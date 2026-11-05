"""Score routing decisions as a Phoenix experiment."""

from pathlib import Path
from typing import Any

import pandas as pd

from action_autonomy.agent import RouterAgent
from action_autonomy.models import RoutingDecision
from action_autonomy.phoenix_eval import (
    get_or_create_dataset,
    require_client,
    run_experiment,
)

REQUIRED_COLUMNS = (
    "test_id",
    "customer_message",
    "expected_department",
    "category",
)

DATASET_NAME = "action-routing-v1"

DEMO_MESSAGES = (
    "I was charged twice for my order!",
    "Where is my package? It's been 2 weeks!",
    "I want to return these shoes, they don't fit",
    "Is the blue wireless headphone in stock?",
    "I can't log into my account, it says password invalid",
    "This is ridiculous! I've called 3 times and nobody helps me!",
)


def load_test_cases(path: Path) -> pd.DataFrame:
    """Load the labeled routing cases used to score a prompt."""
    csv_path = path.expanduser().resolve()
    if not csv_path.is_file():
        raise FileNotFoundError(f"Test cases file not found: {csv_path}")
    frame = pd.read_csv(csv_path)
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(
            f"{csv_path} is missing columns: {', '.join(missing)}. "
            f"Found: {', '.join(map(str, frame.columns))}."
        )
    if frame.empty:
        raise ValueError(f"{csv_path} has no test cases.")
    return frame


def department_matches(output: Any, expected: Any) -> dict[str, Any]:
    """Code evaluator: the returned department equals the label.

    The label is PASS or FAIL. The score is 1.0 or 0.0. The reason is not scored.
    """
    predicted = _department(output)
    wanted = _department_label(expected)
    matched = predicted == wanted
    return {"score": 1.0 if matched else 0.0, "label": "PASS" if matched else "FAIL"}


def run_demo(
    agent: RouterAgent,
    prompt_name: str,
    messages: tuple[str, ...] = DEMO_MESSAGES,
) -> list[RoutingDecision]:
    """Route the sample messages used before the formal evaluation."""
    print("=" * 70)
    print(f"ROUTER AGENT DEMO ({prompt_name})")
    print("=" * 70)
    print()
    decisions: list[RoutingDecision] = []
    for index, message in enumerate(messages, start=1):
        decision = agent.route(message)
        decisions.append(decision)
        print(f"[{index}] Customer: {message}")
        print(f"    -> Department: {decision.department.name}")
        print(f"    -> Reasoning: {decision.reasoning}")
        print()
    print("Demo looks good! But let's evaluate systematically...")
    return decisions


def run_action_experiment(
    agent: RouterAgent,
    test_cases: pd.DataFrame,
    prompt_name: str,
) -> Any:
    """Upload or reuse the routing dataset and score one prompt in Phoenix."""
    frame = _dataset_frame(test_cases)
    experiment_name = f"action-{prompt_name}"
    client = require_client()
    print(
        f"Running {prompt_name} on {len(frame)} cases as experiment {experiment_name}.",
        flush=True,
    )
    print(
        "Each case is one model call. Phoenix stores the department check.",
        flush=True,
    )
    dataset = get_or_create_dataset(
        client,
        name=DATASET_NAME,
        dataframe=frame,
        input_keys=["customer_message"],
        output_keys=["expected_department"],
        metadata_keys=["test_id", "category"],
        description="Labeled routing cases from data/v1_test_cases.csv.",
    )
    return run_experiment(
        client,
        dataset=dataset,
        task=_route_task(agent),
        evaluators=[department_matches],
        experiment_name=experiment_name,
        experiment_description=f"Route each message with {prompt_name}.",
        experiment_metadata={
            "prompt_name": prompt_name,
            "model": agent.model,
        },
    )


def _route_task(agent: RouterAgent):
    def route_message(input: dict[str, Any]) -> dict[str, str]:
        decision = agent.route(str(input["customer_message"]))
        return {
            "department": decision.department.name,
            "reasoning": decision.reasoning,
        }

    return route_message


def _dataset_frame(test_cases: pd.DataFrame) -> pd.DataFrame:
    frame = test_cases.loc[:, list(REQUIRED_COLUMNS)].copy()
    for column in REQUIRED_COLUMNS:
        frame[column] = frame[column].fillna("").astype(str)
    frame["expected_department"] = frame["expected_department"].str.strip().str.upper()
    return frame


def _department(output: Any) -> str:
    if not isinstance(output, dict):
        return ""
    return str(output.get("department") or "").strip().upper()


def _department_label(expected: Any) -> str:
    if not isinstance(expected, dict):
        return ""
    return str(expected.get("expected_department") or "").strip().upper()
