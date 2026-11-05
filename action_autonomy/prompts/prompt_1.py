"""Prompt 1, the baseline router prompt.

The prompt lists department names and asks for JSON. It has no descriptions
and no boundary rules. Evaluation is how we find what is missing.
"""

PROMPT_NAME = "prompt_1"
DESCRIPTION = (
    "Baseline. Department names only, with no descriptions or boundary rules."
)

SYSTEM_PROMPT = """Route customer messages to departments.

Available departments: BILLING, RETURNS, TECHNICAL_SUPPORT, ORDER_STATUS, PRODUCT_INQUIRY, ACCOUNT_MANAGEMENT, ESCALATION

Respond with JSON:
{
    "department": "DEPARTMENT_NAME",
    "reasoning": "Your reasoning"
}
"""
