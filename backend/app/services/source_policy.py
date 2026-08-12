import ipaddress
import socket
from dataclasses import asdict, dataclass
from enum import Enum
from urllib.parse import urlparse


class SourceType(str, Enum):
    MANUFACTURER_PAGE = "MANUFACTURER_PAGE"
    MANUFACTURER_DOCUMENT = "MANUFACTURER_DOCUMENT"
    APPROVED_THIRD_PARTY = "APPROVED_THIRD_PARTY"
    PROHIBITED_MARKETPLACE = "PROHIBITED_MARKETPLACE"
    UNTRUSTED = "UNTRUSTED"


MARKETPLACES = {"amazon.com", "amazon.in", "ebay.com", "walmart.com", "aliexpress.com", "etsy.com"}
TRUST = {SourceType.MANUFACTURER_PAGE: 1.0, SourceType.MANUFACTURER_DOCUMENT: 1.0, SourceType.APPROVED_THIRD_PARTY: 0.65, SourceType.PROHIBITED_MARKETPLACE: 0.0, SourceType.UNTRUSTED: 0.0}


@dataclass
class PolicyDecision:
    url: str
    domain: str
    source_type: SourceType
    allowed: bool
    reason_code: str
    trust_weight: float

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


def _is_unsafe_ip(host: str) -> bool:
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            addresses = [ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, None)]
        except socket.gaierror:
            return True
    return any(ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified for ip in addresses)


class SourcePolicy:
    def evaluate(self, url: str, manufacturer_domains: list[str] | None = None, resolve_dns: bool = True) -> PolicyDecision:
        parsed = urlparse(url)
        domain = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme not in {"http", "https"} or not domain or parsed.username or parsed.password:
            return PolicyDecision(url, domain, SourceType.UNTRUSTED, False, "INVALID_URL", 0)
        if any(domain == market or domain.endswith("." + market) for market in MARKETPLACES):
            return PolicyDecision(url, domain, SourceType.PROHIBITED_MARKETPLACE, False, "MARKETPLACE_PROHIBITED", 0)
        if domain == "localhost" or (resolve_dns and _is_unsafe_ip(domain)):
            return PolicyDecision(url, domain, SourceType.UNTRUSTED, False, "SSRF_BLOCKED", 0)
        owned = any(domain == item.lower() or domain.endswith("." + item.lower()) for item in (manufacturer_domains or []))
        document = parsed.path.lower().endswith(".pdf")
        source_type = SourceType.MANUFACTURER_DOCUMENT if owned and document else SourceType.MANUFACTURER_PAGE if owned else SourceType.APPROVED_THIRD_PARTY
        return PolicyDecision(url, domain, source_type, True, "ALLOWED", TRUST[source_type])

    def validate_redirect(self, target: str, manufacturer_domains: list[str] | None = None) -> PolicyDecision:
        return self.evaluate(target, manufacturer_domains)
