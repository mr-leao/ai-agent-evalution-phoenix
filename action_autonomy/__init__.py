"""V1 action-autonomy router.

The agent classifies a customer message and routes it to one department.
"""

from action_autonomy.agent import RouterAgent
from action_autonomy.models import Department, RoutingDecision
from action_autonomy.prompts import get_prompt

__all__ = [
    "Department",
    "RouterAgent",
    "RoutingDecision",
    "get_prompt",
]
