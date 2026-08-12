import math
import re
from dataclasses import dataclass


@dataclass
class Chunk:
    source_identifier: str
    url: str
    text: str
    source_trust: float
    content_hash: str
    page_number: int | None = None
    heading: str | None = None


class EvidenceIndex:
    """Small deterministic BM25-compatible index; persisted chunks use EvidenceChunk."""
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []

    def add(self, chunk: Chunk) -> None:
        self.chunks.append(chunk)

    def search(self, query: str, limit: int = 5) -> list[Chunk]:
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        if not terms:
            return []
        scored = []
        for chunk in self.chunks:
            words = re.findall(r"[a-z0-9]+", chunk.text.lower())
            score = sum((1 + math.log(1 + words.count(term))) for term in terms if term in words) * chunk.source_trust
            if score:
                scored.append((score, chunk))
        return [chunk for _, chunk in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


def chunk_text(text: str, source_identifier: str, url: str, content_hash: str, trust: float, page_number: int | None = None, size: int = 800) -> list[Chunk]:
    paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
    result: list[Chunk] = []
    current = ""
    heading = None
    for part in paragraphs:
        if len(part) < 100 and part.isupper():
            heading = part
        if current and len(current) + len(part) > size:
            result.append(Chunk(source_identifier, url, current, trust, content_hash, page_number, heading))
            current = ""
        current = f"{current}\n{part}".strip()
    if current:
        result.append(Chunk(source_identifier, url, current, trust, content_hash, page_number, heading))
    return result
