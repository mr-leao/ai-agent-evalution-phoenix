"""V2 planning agent.

Routing is the V1 router with prompt_2. This agent then retrieves SOPs
and asks the plan model for a numbered action plan.
"""

from openai import OpenAI

from action_autonomy.agent import RouterAgent
from action_autonomy.prompts import get_prompt as get_route_prompt

from planning_autonomy.config import PLAN_TEMPERATURE, PlanningSettings, sops_dir
from planning_autonomy.models import Plan, RetrievedSOP
from planning_autonomy.prompts.plan import render_plan_prompt
from planning_autonomy.sops import SOPIndex, get_index

ROUTE_PROMPT_NAME = "prompt_2"


class PlanningAgent:
    """Route a message, retrieve SOPs, and write a plan."""

    def __init__(
        self,
        top_k: int,
        settings: PlanningSettings | None = None,
        client: OpenAI | None = None,
        index: SOPIndex | None = None,
    ):
        self.settings = settings or PlanningSettings.from_env()
        route_prompt = get_route_prompt(ROUTE_PROMPT_NAME)
        self.router = RouterAgent(
            route_prompt.system_prompt,
            self.settings.connection,
            client,
        )
        self.client = self.router.client
        self.top_k = top_k
        self.plan_model = self.settings.plan_model
        self.judge_model = self.settings.judge_model
        self.index = index or get_index(str(sops_dir().resolve()))

    def plan(self, customer_message: str) -> Plan:
        """Route, retrieve, and write a plan for one customer message."""
        decision = self.router.route(customer_message)
        department = decision.department.name
        retrieved = self.index.retrieve(customer_message, department, self.top_k)
        plan_text = self._write_plan(customer_message, department, retrieved)
        return Plan(
            customer_message=customer_message,
            department=department,
            reasoning=decision.reasoning,
            retrieved_sops=retrieved,
            plan=plan_text,
        )

    def _write_plan(
        self,
        message: str,
        department: str,
        retrieved: tuple[RetrievedSOP, ...],
    ) -> str:
        prompt = render_plan_prompt(message, department, _sop_context(retrieved))
        try:
            response = self.client.chat.completions.create(
                model=self.plan_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=PLAN_TEMPERATURE,
            )
        except Exception as exc:
            raise RuntimeError(
                "Plan request failed for "
                f"{self.plan_model} at {self.settings.connection.base_url}: {exc}"
            ) from exc
        text = _message_text(response.choices[0].message.content).strip()
        if not text:
            raise RuntimeError(
                f"Plan model {self.plan_model} returned an empty plan."
            )
        return text


def _sop_context(retrieved: tuple[RetrievedSOP, ...]) -> str:
    blocks = [
        f"--- {sop.sop_id} (Relevance: {sop.score:.2f}) ---\n{sop.excerpt}"
        for sop in retrieved
    ]
    return "\n\n".join(blocks)


def _message_text(content: object) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(str(part.get("text", "")))
            else:
                text = getattr(part, "text", None)
                parts.append(str(text if text is not None else part))
        return "".join(parts)
    return str(content)
