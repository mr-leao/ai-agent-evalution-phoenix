"""Load SOP files and retrieve them with BM25."""

import re
from functools import lru_cache
from pathlib import Path

from rank_bm25 import BM25Okapi

from planning_autonomy.config import DEFAULT_SOPS_DIR
from planning_autonomy.models import RetrievedSOP

EXCERPT_CHARS = 2000
_SOP_NUMBER = re.compile(r"(SOP_\d+)")


def normalize_sop_name(name: str) -> str:
    """Reduce a filename or CSV label to SOP_ plus its number.

    `SOP-001_standard_returns` and `sop_001_standard_returns.txt` both
    become `SOP_001`.
    """
    text = str(name).strip().upper().replace("SOP-", "SOP_").replace(" ", "_")
    if text.endswith(".TXT"):
        text = text[:-4]
    match = _SOP_NUMBER.match(text)
    return match.group(1) if match else text


def parse_expected_sops(value: object) -> tuple[str, ...]:
    """Split a CSV cell of comma-separated SOP labels and normalize each one."""
    if value is None or (isinstance(value, float) and value != value):
        return ()
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ()
    return tuple(normalize_sop_name(part.strip()) for part in text.split(",") if part.strip())


def load_sop_documents(directory: Path | None = None) -> list[tuple[str, str]]:
    """Return `(sop_id, text)` for every `sop_*.txt` file, sorted by name."""
    folder = (directory or DEFAULT_SOPS_DIR).expanduser().resolve()
    if not folder.is_dir():
        raise FileNotFoundError(f"SOP directory not found: {folder}")
    files = sorted(folder.glob("sop_*.txt"))
    if not files:
        raise FileNotFoundError(f"No sop_*.txt files in {folder}")
    documents: list[tuple[str, str]] = []
    for path in files:
        sop_id = path.stem.upper()
        documents.append((sop_id, path.read_text(encoding="utf-8")))
    return documents


class SOPIndex:
    """BM25 index over the SOP corpus."""

    def __init__(self, documents: list[tuple[str, str]]):
        if not documents:
            raise ValueError("SOP index requires at least one document.")
        self.documents = documents
        tokenized = [_tokens(text) for _, text in documents]
        self._bm25 = BM25Okapi(tokenized)

    def retrieve(self, message: str, department: str, top_k: int) -> tuple[RetrievedSOP, ...]:
        """Return the highest-scoring SOPs for a message and department."""
        if top_k < 1:
            raise ValueError(f"top_k must be at least 1, got {top_k}.")
        query = _tokens(f"{message} {department}")
        scores = self._bm25.get_scores(query)
        order = sorted(range(len(scores)), key=lambda index: float(scores[index]), reverse=True)
        hits: list[RetrievedSOP] = []
        for index in order[:top_k]:
            sop_id, text = self.documents[index]
            hits.append(
                RetrievedSOP(
                    sop_id=sop_id,
                    score=float(scores[index]),
                    excerpt=text[:EXCERPT_CHARS],
                )
            )
        return tuple(hits)


@lru_cache(maxsize=4)
def get_index(directory: str) -> SOPIndex:
    """Build and cache an index for one SOP directory."""
    return SOPIndex(load_sop_documents(Path(directory)))


def _tokens(text: str) -> list[str]:
    tokens = text.lower().split()
    return tokens or ["empty"]
