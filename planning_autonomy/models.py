"""Domain types for a planned customer-support case."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedSOP:
    """One SOP retrieved for a customer message."""

    sop_id: str
    score: float
    excerpt: str


@dataclass(frozen=True)
class Plan:
    """Routing decision, retrieved procedures, and the written plan."""

    customer_message: str
    department: str
    reasoning: str
    retrieved_sops: tuple[RetrievedSOP, ...]
    plan: str
