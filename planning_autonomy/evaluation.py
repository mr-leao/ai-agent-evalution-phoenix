"""Score SOP recall and plan alignment on the V2 cases."""

from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

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
DEMO_MESSAGE = "I bought a jacket last month, but it's too big. Can I return it?"


@dataclass
class EvalResult:
    """Recall and alignment for one labeled case."""

    case_id: str
    message: str
    complexity: str
    expected_sops: tuple[str, ...]
    retrieved_sops: tuple[str, ...]
    recall: float
    alignment: str
    department: str
    plan: str


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
            print(
                f"  {normalize_sop_name(sop.sop_id)}  score {sop.score:.2f}"
            )
    else:
        print("SOPs: none")
    print("Plan:")
    print(plan.plan)


def run_evaluation(
    agent: PlanningAgent,
    test_cases: pd.DataFrame,
    tracer=None,
    prompt_name: str = "prompt",
) -> list[EvalResult]:
    """Plan every case, score recall, and judge alignment."""
    results: list[EvalResult] = []
    total = len(test_cases)
    print(
        f"Running {prompt_name} on {total} cases "
        f"(route, plan, then judge: about {total * 3} model calls)...",
        flush=True,
    )
    if tracer is not None:
        print("Each case is being traced in Phoenix.", flush=True)
    print(flush=True)

    for position, (_, row) in enumerate(test_cases.iterrows()):
        message = str(row["message"])
        expected = parse_expected_sops(row["expected_sops"])
        context = (
            tracer.start_as_current_span(f"test_case_{position}")
            if tracer is not None
            else nullcontext()
        )
        with context as span:
            if span is not None:
                span.set_attribute("test.id", str(position))
                span.set_attribute("test.message", message)
                span.set_attribute("test.complexity", str(row["complexity"]))
                span.set_attribute("test.expected_sops", ", ".join(expected))
            plan = agent.plan(message)
            retrieved = tuple(
                normalize_sop_name(sop.sop_id) for sop in plan.retrieved_sops
            )
            case_recall = recall(expected, retrieved)
            if span is not None:
                _record_span(span, plan.department, retrieved, expected)
            alignment = classify_plan(
                agent,
                message=message,
                expected_steps=str(row["expected_steps"]),
                policy_details=str(row["policy_details"]),
                generated_plan=plan.plan,
            )
        result = EvalResult(
            case_id=str(position),
            message=message,
            complexity=str(row["complexity"]),
            expected_sops=expected,
            retrieved_sops=retrieved,
            recall=case_recall,
            alignment=alignment,
            department=plan.department,
            plan=plan.plan,
        )
        results.append(result)
        print(
            f"[{position + 1}/{total}] case {position}: "
            f"recall {case_recall:.0%} alignment {alignment} "
            f"(department {plan.department}, SOPs {', '.join(retrieved) or 'none'})",
            flush=True,
        )
    print("\nEvaluation complete!", flush=True)
    return results


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


def render_metrics(results: list[EvalResult], prompt_name: str, top_k: int) -> str:
    """Format mean SOP recall and the alignment counts."""
    total = len(results)
    mean_recall = sum(result.recall for result in results) / total if total else 0.0
    counts = _alignment_counts(results)
    lines = [
        "=" * 70,
        f"{prompt_name.upper()} EVALUATION RESULTS (top {top_k} SOPs)",
        "=" * 70,
        "",
        f"SOP Retrieval Recall: {mean_recall:.1%}",
        (
            "Plan Alignment: "
            f"good {counts['good']}, partial {counts['partial']}, "
            f"bad {counts['bad']} ({total} cases)"
        ),
    ]
    return "\n".join(lines)


def render_comparison(
    name_a: str,
    top_k_a: int,
    results_a: list[EvalResult],
    name_b: str,
    top_k_b: int,
    results_b: list[EvalResult],
) -> str:
    """Compare recall and the share of good plans."""
    recall_a = _mean_recall(results_a)
    recall_b = _mean_recall(results_b)
    good_a = _alignment_counts(results_a)["good"]
    good_b = _alignment_counts(results_b)["good"]
    total_a = len(results_a)
    total_b = len(results_b)
    share_a = good_a / total_a if total_a else 0.0
    share_b = good_b / total_b if total_b else 0.0
    by_id_b = {result.case_id: result for result in results_b}
    improved = []
    worse = []
    incomplete = []
    for result in results_a:
        other = by_id_b.get(result.case_id)
        if other is None:
            continue
        if other.recall > result.recall:
            improved.append(other)
        if other.recall < result.recall:
            worse.append(other)
        if other.recall < 1.0:
            incomplete.append(other)
    lines = [
        "=" * 70,
        f"{name_a.upper()} VS {name_b.upper()}",
        "=" * 70,
        "",
        "SOP Retrieval Recall:",
        f"  {name_a} (top {top_k_a}): {recall_a:.1%}",
        f"  {name_b} (top {top_k_b}): {recall_b:.1%}",
        f"  Change: {recall_b - recall_a:+.1%}",
        "",
        "Plan Alignment (good):",
        f"  {name_a}: {good_a}/{total_a} ({share_a:.1%})",
        f"  {name_b}: {good_b}/{total_b} ({share_b:.1%})",
        f"  Change: {share_b - share_a:+.1%}",
    ]
    lines.extend(_case_block("Recall improved", improved))
    lines.extend(_case_block("Still incomplete", incomplete))
    lines.extend(_case_block("Recall got worse", worse))
    return "\n".join(lines)


def _record_span(span, department: str, retrieved: tuple[str, ...], expected: tuple[str, ...]) -> None:
    from opentelemetry.trace import Status, StatusCode

    span.set_attribute("result.department", department)
    span.set_attribute("result.retrieved_sops", ", ".join(retrieved))
    missing = set(expected) - set(retrieved)
    if missing:
        span.set_status(Status(StatusCode.ERROR, "Missing expected SOPs"))
        span.set_attribute("error.missing_sops", ", ".join(sorted(missing)))
        return
    span.set_status(Status(StatusCode.OK))


def _alignment_counts(results: list[EvalResult]) -> dict[str, int]:
    counts = {"good": 0, "partial": 0, "bad": 0}
    for result in results:
        counts[result.alignment] = counts.get(result.alignment, 0) + 1
    return counts


def _mean_recall(results: list[EvalResult]) -> float:
    if not results:
        return 0.0
    return sum(result.recall for result in results) / len(results)


def _case_block(title: str, results: list[EvalResult]) -> list[str]:
    if not results:
        return []
    lines = ["", f"{title} ({len(results)}):"]
    for result in results:
        preview = result.message[:60]
        lines.append(
            f"  [case {result.case_id}] {preview} "
            f"(recall {result.recall:.0%})"
        )
    return lines
