"""V1 action-autonomy agent.

The agent performs one action: classify a customer message and route it
to a department. A person in that department takes over from there.
"""

import json
import re

from openai import OpenAI

from action_autonomy.config import Settings
from action_autonomy.models import Department, RoutingDecision, department_from_name

_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class RouterAgent:
    """Routes one customer message to one department."""

    def __init__(
        self,
        system_prompt: str,
        settings: Settings | None = None,
        client: OpenAI | None = None,
    ):
        self.settings = settings or Settings.from_env()
        self.client = client or OpenAI(
            base_url=self.settings.base_url,
            api_key=self.settings.api_key,
        )
        self.model = self.settings.model
        self.system_prompt = system_prompt

    def route(self, customer_message: str) -> RoutingDecision:
        """Route a customer message to a department.

        Steps:
        1. Call the chat model with the system prompt and the message.
        2. Parse the JSON response.
        3. Validate the department. An unknown department becomes ESCALATION.
        4. Return a RoutingDecision.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": customer_message},
                ],
                temperature=self.settings.temperature,
                # JSON Schema keeps department to the known enum values.
                response_format=_response_format(),
            )
        except Exception as exc:
            raise RuntimeError(
                "Model request failed for "
                f"{self.model} at {self.settings.base_url}: {exc}"
            ) from exc

        content = _message_text(response.choices[0].message.content)
        try:
            result = _parse_json_object(content)
        except (json.JSONDecodeError, ValueError) as exc:
            preview = content[:200].replace("\n", " ")
            raise RuntimeError(
                f"Model response was not valid JSON ({exc}). Response: {preview}"
            ) from exc

        return RoutingDecision(
            department=department_from_name(result.get("department")),
            reasoning=str(result.get("reasoning") or "No reasoning provided"),
            customer_message=customer_message,
        )


def _response_format() -> dict:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "routing_decision",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "enum": [department.name for department in Department],
                    },
                    "reasoning": {"type": "string"},
                },
                "required": ["department", "reasoning"],
                "additionalProperties": False,
            },
        },
    }


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


def _parse_json_object(content: str) -> dict:
    text = content.strip()
    if not text:
        raise ValueError("empty response")
    text = _JSON_FENCE.sub("", text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match is None:
            raise
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("JSON response was not an object")
    return parsed
