"""Domain types for the V1 router."""

from dataclasses import dataclass
from enum import Enum


class Department(Enum):
    """Departments a customer message can be routed to."""

    BILLING = "billing"
    RETURNS = "returns"
    TECHNICAL_SUPPORT = "technical_support"
    ORDER_STATUS = "order_status"
    PRODUCT_INQUIRY = "product_inquiry"
    ACCOUNT_MANAGEMENT = "account_management"
    ESCALATION = "escalation"


@dataclass
class RoutingDecision:
    """One routing decision for a customer message."""

    department: Department
    reasoning: str
    customer_message: str


def department_from_name(name: str | None) -> Department:
    """Map a model string to a department. Unknown names become ESCALATION."""
    if not name or not str(name).strip():
        return Department.ESCALATION
    try:
        return Department[str(name).strip().upper()]
    except KeyError:
        return Department.ESCALATION
