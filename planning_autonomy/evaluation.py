"""Score SOP recall and plan alignment as a Phoenix experiment."""

from pathlib import Path
from typing import Any

import pandas as pd
from phoenix.client.experiments import create_evaluator

from action_autonomy.phoenix_eval import (
    get_or_create_dataset,
    require_client,
    run_experiment,
)
from planning_autonomy.agent import PlanningAgent
from planning_autonomy.config import PLAN_TEMPERATURE
from planning_autonomy.prompts.judge import parse_alignment, render_judge_prompt
from planning_autonomy.sops import normalize_sop_name, parse_expected_sops

REQUIRED_COLUMNS = (
    "message",
    "complexity",
    "expected_sops",
    "expected_steps",
    "policy_details",
)

DATASET_NAME = "planning-v2"
DEMO_MESSAGE = "I bought a jacket last month, but it's too big. Can I return it?"


def load_test_cases(path: Path) -> pd.DataFrame:
    """Load the V2 cases. The V1 routing CSV does not have these columns."""
    csv_path = path.expanduser().resolve()
    if not csv_path.is_file():
        raise FileNotFoundError(f"Test cases file not found: {csv_path}")
    frame = pd.read_csv(csv_path)
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(
            f"{csv_path.name} is missing {', '.join(missing)}. "
            "Planning scores data/v2_test_cases.csv "
            "(message, complexity, expected_sops, expected_steps, policy_details)."
        )
    if frame.empty:
        raise ValueError(f"{csv_path} has no test cases.")
    return frame


def recall(expected: tuple[str, ...], retrieved: tuple[str, ...]) -> float:
    """Fraction of expected SOP ids present in the retrieved ids.

    An empty expected set scores 1.0. Duplicate labels count once.
    """
    expected_ids = {normalize_sop_name(sop) for sop in expected}
    if not expected_ids:
        return 1.0
    retrieved_ids = {normalize_sop_name(sop) for sop in retrieved}
    return len(expected_ids & retrieved_ids) / len(expected_ids)


def sop_recall(output: Any, expected: Any) -> float:
    """Code evaluator: share of expected SOP ids present in the task output."""
    expected_sops = parse_expected_sops(_field(expected, "expected_sops"))
    retrieved = _retrieved(output)
    return recall(expected_sops, retrieved)


def run_demo(agent: PlanningAgent) -> None:
    """Plan the notebook's first sample message."""
    print("=" * 70)
    print(f"PLANNING AGENT DEMO (top {agent.top_k} SOPs)")
    print("=" * 70)
    print()
    print_plan(agent.plan(DEMO_MESSAGE))


def print_plan(plan) -> None:
    """Print the department, retrieved SOP ids, and the plan."""
    print(f"Customer: {plan.customer_message}")
    print(f"Department: {plan.department}")
    print(f"Reasoning: {plan.reasoning}")
    if plan.retrieved_sops:
        print("SOPs:")
        for sop in plan.retrieved_sops:
            print(f"  {normalize_sop_name(sop.sop_id)}  score {sop.score:.2f}")
    else:
        print("SOPs: none")
    print("Plan:")
    print(plan.plan)


def classify_plan(
    agent: PlanningAgent,
    message: str,
    expected_steps: str,
    policy_details: str,
    generated_plan: str,
) -> str:
    """Ask the judge model for good, partial, or bad. Failures count as partial."""
    prompt = render_judge_prompt(
        message, expected_steps, policy_details, generated_plan
    )
    try:
        response = agent.client.chat.completions.create(
            model=agent.judge_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=PLAN_TEMPERATURE,
        )
    except Exception:
        return "partial"
    content = response.choices[0].message.content
    return parse_alignment(content if isinstance(content, str) else "")


def run_planning_experiment(
    agent: PlanningAgent,
    test_cases: pd.DataFrame,
    prompt_name: str,
) -> Any:
    """Upload or reuse the planning dataset and score one prompt in Phoenix."""
    frame = _dataset_frame(test_cases)
    experiment_name = f"planning-{prompt_name}"
    client = require_client()
    print(
        f"Running {prompt_name} on {len(frame)} cases as experiment {experiment_name}.",
        flush=True,
    )
    print(
        "Each case is a route, a plan, and a judge: "
        f"about {len(frame) * 3} model calls. Phoenix stores both scores.",
        flush=True,
    )
    dataset = get_or_create_dataset(
        client,
        name=DATASET_NAME,
        dataframe=frame,
        input_keys=["message"],
        output_keys=["expected_sops", "expected_steps", "policy_details"],
        metadata_keys=["complexity", "row"],
        description="Labeled planning cases from data/v2_test_cases.csv.",
    )
    return run_experiment(
        client,
        dataset=dataset,
        task=_plan_task(agent),
        evaluators=[sop_recall, _plan_alignment(agent)],
        experiment_name=experiment_name,
        experiment_description=(
            f"Route, retrieve top {agent.top_k} SOPs, and plan with {prompt_name}."
        ),
        experiment_metadata={
            "prompt_name": prompt_name,
            "top_k": agent.top_k,
            "plan_model": agent.plan_model,
            "judge_model": agent.judge_model,
        },
    )


def _plan_task(agent: PlanningAgent):
    def write_plan(input: dict[str, Any]) -> dict[str, Any]:
        plan = agent.plan(str(input["message"]))
        return {
            "department": plan.department,
            "reasoning": plan.reasoning,
            "retrieved_sops": [
                normalize_sop_name(sop.sop_id) for sop in plan.retrieved_sops
            ],
            "plan": plan.plan,
        }

    return write_plan


def _plan_alignment(agent: PlanningAgent):
    def plan_alignment(output: Any, expected: Any, input: Any) -> str:
        return classify_plan(
            agent,
            message=_field(input, "message"),
            expected_steps=_field(expected, "expected_steps"),
            policy_details=_field(expected, "policy_details"),
            generated_plan=_field(output, "plan"),
        )

    return create_evaluator(kind="LLM", name="plan_alignment")(plan_alignment)


def _dataset_frame(test_cases: pd.DataFrame) -> pd.DataFrame:
    frame = test_cases.loc[:, list(REQUIRED_COLUMNS)].copy()
    for column in REQUIRED_COLUMNS:
        frame[column] = frame[column].fillna("").astype(str)
    frame["row"] = list(range(len(frame)))
    return frame


def _retrieved(output: Any) -> tuple[str, ...]:
    if not isinstance(output, dict):
        return ()
    retrieved = output.get("retrieved_sops") or ()
    if isinstance(retrieved, str):
        return (retrieved,)
    return tuple(str(item) for item in retrieved)


def _field(value: Any, key: str) -> str:
    if not isinstance(value, dict):
        return ""
    field = value.get(key)
    if field is None:
        return ""
    return str(field)
