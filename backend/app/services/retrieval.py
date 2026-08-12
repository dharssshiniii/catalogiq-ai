import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.services.source_policy import PolicyDecision, SourcePolicy


@dataclass
class RetrievalResult:
    ok: bool
    url: str
    text: str = ""
    content_type: str | None = None
    status: int | None = None
    content_hash: str | None = None
    retrieved_at: str | None = None
    policy: PolicyDecision | None = None
    error_code: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


def extract_html_text(content: bytes) -> str:
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "noscript", "svg"]):
        tag.decompose()
    parts: list[str] = []
    for node in soup.find_all(["h1", "h2", "h3", "p", "li", "th", "td"]):
        value = re.sub(r"\s+", " ", node.get_text(" ", strip=True))
        if value and (not parts or parts[-1] != value):
            parts.append(value)
    return "\n".join(parts)


class SafeWebRetriever:
    def __init__(self, policy: SourcePolicy | None = None, timeout: float = 10, max_bytes: int = 5_242_880, max_redirects: int = 3, transport: httpx.BaseTransport | None = None):
        self.policy, self.timeout, self.max_bytes, self.max_redirects, self.transport = policy or SourcePolicy(), timeout, max_bytes, max_redirects, transport

    def retrieve(self, url: str, manufacturer_domains: list[str] | None = None) -> RetrievalResult:
        decision = self.policy.evaluate(url, manufacturer_domains, resolve_dns=self.transport is None)
        if not decision.allowed:
            return RetrievalResult(False, url, policy=decision, error_code=decision.reason_code)
        headers = {"User-Agent": "CatalogIQ-AI/0.2 evidence-retriever (+local prototype)", "Accept": "text/html,application/xhtml+xml,application/pdf,text/plain"}
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=False, transport=self.transport, headers=headers) as client:
                current = url
                for _ in range(self.max_redirects + 1):
                    response = client.get(current)
                    if response.status_code in {429, 502, 503, 504}:
                        response = client.get(current)  # one bounded retry; GET is idempotent
                    if response.is_redirect:
                        target = str(response.next_request.url)
                        redirected = self.policy.validate_redirect(target, manufacturer_domains)
                        if not redirected.allowed:
                            return RetrievalResult(False, target, status=response.status_code, policy=redirected, error_code="UNSAFE_REDIRECT")
                        current, decision = target, redirected
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").split(";")[0].lower()
                    if content_type not in {"text/html", "application/xhtml+xml", "text/plain", "application/pdf"}:
                        return RetrievalResult(False, current, content_type=content_type, status=response.status_code, policy=decision, error_code="CONTENT_TYPE_BLOCKED")
                    content = response.content
                    if len(content) > self.max_bytes:
                        return RetrievalResult(False, current, content_type=content_type, status=response.status_code, policy=decision, error_code="RESPONSE_TOO_LARGE")
                    digest = hashlib.sha256(content).hexdigest()
                    text = extract_html_text(content) if content_type != "application/pdf" else ""
                    return RetrievalResult(True, current, text, content_type, response.status_code, digest, datetime.now(timezone.utc).isoformat(), decision, metadata={"raw_content": content if content_type == "application/pdf" else b""})
                return RetrievalResult(False, current, policy=decision, error_code="TOO_MANY_REDIRECTS")
        except httpx.TimeoutException:
            return RetrievalResult(False, url, policy=decision, error_code="TIMEOUT")
        except httpx.HTTPError:
            return RetrievalResult(False, url, policy=decision, error_code="RETRIEVAL_FAILED")
