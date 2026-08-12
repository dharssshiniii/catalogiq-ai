import json
import uuid
from dataclasses import dataclass
from typing import Protocol

import httpx
from pydantic import BaseModel, ValidationError


class ExtractedFacts(BaseModel):
    values: dict[str, str | list[str] | None]


@dataclass
class ProviderResult:
    provider: str
    model: str | None
    request_id: str | None
    available: bool
    valid: bool
    values: dict[str, object]
    error_code: str | None = None


class ExtractionProvider(Protocol):
    def extract(self, evidence: list[str], fields: list[str]) -> ProviderResult: ...


class DeterministicProvider:
    def extract(self, evidence: list[str], fields: list[str]) -> ProviderResult:
        return ProviderResult("demo", "deterministic-v1", "demo-" + uuid.uuid4().hex[:8], True, True, {field: None for field in fields})


class UnavailableProvider:
    def __init__(self, reason: str = "PROVIDER_UNAVAILABLE") -> None:
        self.reason = reason
    def extract(self, evidence: list[str], fields: list[str]) -> ProviderResult:
        return ProviderResult("unavailable", None, None, False, False, {}, self.reason)


class GeminiProvider:
    def __init__(self, mode: str, api_key: str | None, model: str, timeout: float = 20, transport: httpx.BaseTransport | None = None) -> None:
        self.mode, self.api_key, self.model, self.timeout, self.transport = mode, api_key, model, timeout, transport
    @property
    def available(self) -> bool:
        return self.mode == "LIVE" and bool(self.api_key and self.model)
    def extract(self, evidence: list[str], fields: list[str]) -> ProviderResult:
        if not self.available:
            return UnavailableProvider("LIVE_NOT_CONFIGURED").extract(evidence, fields)
        prompt = "Extract only supported facts. Return null when unsupported. Fields: " + ", ".join(fields) + "\nEvidence:\n" + "\n".join(evidence)
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.post(endpoint, params={"key": self.api_key}, json=payload)
                if response.status_code in {429, 502, 503, 504}:
                    response = client.post(endpoint, params={"key": self.api_key}, json=payload)
            response.raise_for_status()
            body = response.json()
            text = body["candidates"][0]["content"]["parts"][0]["text"]
            values = ExtractedFacts.model_validate(json.loads(text)).values
            return ProviderResult("gemini", self.model, response.headers.get("x-request-id"), True, True, values)
        except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValidationError):
            return ProviderResult("gemini", self.model, None, True, False, {}, "PROVIDER_RESPONSE_INVALID")


def select_provider(mode: str, key: str | None, model: str) -> ExtractionProvider:
    return GeminiProvider(mode, key, model) if mode == "LIVE" else DeterministicProvider()
