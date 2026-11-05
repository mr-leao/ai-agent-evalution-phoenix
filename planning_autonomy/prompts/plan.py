"""Instruction text for the plan. Both prompt variants use this text."""

PLAN_PROMPT = """You are a customer support agent planning assistant. Create a detailed, step-by-step action plan.

**Customer Message:**
"{message}"

**Department:** {department}

**Relevant Procedures (SOPs):**
{sops_context}

**Instructions:**
Create a detailed action plan that:
1. Lists specific steps the agent should take (in order)
2. References relevant SOP procedures
3. Includes verification or security steps
4. Mentions escalation criteria if applicable
5. Provides timeline expectations
6. Notes any edge cases or system limitations

Format as a numbered action plan. Be specific and actionable.

**Action Plan:**"""


def render_plan_prompt(message: str, department: str, sops_context: str) -> str:
    return PLAN_PROMPT.format(
        message=message,
        department=department,
        sops_context=sops_context or "(none retrieved)",
    )
