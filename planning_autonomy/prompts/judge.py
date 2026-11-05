"""Instruction text for the plan-alignment judge."""

JUDGE_PROMPT = """Evaluate if this action plan covers expected procedure steps.

**Message:** {message}
**Expected Steps:** {expected_steps}
**Expected Policy:** {policy_details}
**Generated Plan:** {generated_plan}

Classify as:
- good: All critical steps covered, complete and actionable
- partial: Main steps covered but missing some details
- bad: Missing critical steps or significant gaps

Respond: CLASS: <good|partial|bad>
REASONING: <brief explanation>"""


def render_judge_prompt(
    message: str,
    expected_steps: str,
    policy_details: str,
    generated_plan: str,
) -> str:
    return JUDGE_PROMPT.format(
        message=message,
        expected_steps=expected_steps,
        policy_details=policy_details,
        generated_plan=generated_plan,
    )


def parse_alignment(content: str) -> str:
    """Read a `CLASS:` line. Anything else counts as partial."""
    for line in content.splitlines():
        if not line.startswith("CLASS:"):
            continue
        label = line.replace("CLASS:", "", 1).strip().lower()
        if label in {"good", "partial", "bad"}:
            return label
        return "partial"
    return "partial"
