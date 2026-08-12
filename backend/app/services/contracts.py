from typing import Protocol

from app.models.schemas import EnrichedFieldResult, ProductInput, ValidationIssueResult


class SourceRetriever(Protocol):
    def retrieve(self, product: ProductInput) -> list[str]: ...


class DocumentExtractor(Protocol):
    def extract(self, source: str) -> str: ...


class AIExtractor(Protocol):
    @property
    def available(self) -> bool: ...
    def enrich(self, product: ProductInput, documents: list[str]) -> list[EnrichedFieldResult]: ...


class ProductValidator(Protocol):
    def validate(self, fields: list[EnrichedFieldResult]) -> list[ValidationIssueResult]: ...


class DescriptionBuilder(Protocol):
    def build(self, product_name: str, attributes: dict[str, str]) -> str: ...

