"""Evaluate routing accuracy on the labeled test set."""

from collections import defaultdict
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from action_autonomy.agent import RouterAgent
from action_autonomy.models import RoutingDecision

REQUIRED_COLUMNS = (
    "test_id",
    "customer_message",
    "expected_department",
    "category",
)

DEMO_MESSAGES = (
    "I was charged twice for my order!",
    "Where is my package? It's been 2 weeks!",
    "I want to return these shoes, they don't fit",
    "Is the blue wireless headphone in stock?",
    "I can't log into my account, it says password invalid",
    "This is ridiculous! I've called 3 times and nobody helps me!",
)


@dataclass
class EvalResult:
    """Result of one labeled test case."""

    test_id: str
    message: str
    expected: str
    predicted: str
    correct: bool
    reasoning: str
    category: str


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


def run_evaluation(
    agent: RouterAgent,
    test_cases: pd.DataFrame,
    tracer=None,
    prompt_name: str = "prompt",
) -> list[EvalResult]:
    """Route every test case and print pass/fail as it goes."""
    results: list[EvalResult] = []
    total = len(test_cases)
    print(f"Running {prompt_name} evaluation on {total} test cases...", flush=True)
    if tracer is not None:
        print("Each routing decision is being traced in Phoenix.", flush=True)
    print(flush=True)

    for position, (_, row) in enumerate(test_cases.iterrows(), start=1):
        test_id = str(row["test_id"])
        expected = str(row["expected_department"]).strip().upper()
        message = str(row["customer_message"])
        category = str(row["category"])
        span_name = f"test_case_{test_id}"
        context = (
            tracer.start_as_current_span(span_name)
            if tracer is not None
            else nullcontext()
        )
        with context as span:
            if span is not None:
                span.set_attribute("test.id", test_id)
                span.set_attribute("test.category", category)
                span.set_attribute("test.expected_department", expected)
            decision = agent.route(message)
            result = _result_from_decision(
                test_id=test_id,
                message=message,
                expected=expected,
                category=category,
                decision=decision,
            )
            if span is not None:
                _record_span(span, result)
        results.append(result)
        status = "PASS" if result.correct else "FAIL"
        print(
            f"[{position}/{total}] {test_id}: {status} "
            f"(Expected: {result.expected}, Got: {result.predicted})",
            flush=True,
        )
    print("\nEvaluation complete!", flush=True)
    return results


def run_demo(agent: RouterAgent, prompt_name: str, messages: tuple[str, ...] = DEMO_MESSAGES) -> list[RoutingDecision]:
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


def render_metrics(results: list[EvalResult], prompt_name: str) -> str:
    """Format overall accuracy, per-department accuracy, and errors."""
    total = len(results)
    correct = sum(1 for result in results if result.correct)
    accuracy = correct / total if total else 0.0
    department_correct: dict[str, int] = defaultdict(int)
    department_total: dict[str, int] = defaultdict(int)
    for result in results:
        department_total[result.expected] += 1
        if result.correct:
            department_correct[result.expected] += 1

    lines = [
        "=" * 70,
        f"{prompt_name.upper()} EVALUATION RESULTS",
        "=" * 70,
        "",
        f"Overall Accuracy: {accuracy:.1%} ({correct}/{total} correct)",
        "",
        "Per-Department Accuracy:",
    ]
    for department in sorted(department_total):
        department_accuracy = department_correct[department] / department_total[department]
        filled = int(department_accuracy * 20)
        bar = "█" * filled + "░" * (20 - filled)
        lines.append(f"  {department:20} {bar} {department_accuracy:.0%}")

    errors = [result for result in results if not result.correct]
    if errors:
        lines.append("")
        lines.append(f"Errors ({len(errors)} cases):")
        for result in errors:
            lines.append("")
            lines.append(f"  [{result.test_id}] {result.message[:60]}...")
            lines.append(f"  Expected: {result.expected} -> Got: {result.predicted}")
            lines.append(f"  Category: {result.category}")
    return "\n".join(lines)


def render_comparison(
    name_a: str,
    results_a: list[EvalResult],
    name_b: str,
    results_b: list[EvalResult],
) -> str:
    """Format the before/after accuracy comparison from the lesson."""
    correct_a = sum(1 for result in results_a if result.correct)
    correct_b = sum(1 for result in results_b if result.correct)
    total_a = len(results_a)
    total_b = len(results_b)
    accuracy_a = correct_a / total_a if total_a else 0.0
    accuracy_b = correct_b / total_b if total_b else 0.0
    errors_a = {result.test_id for result in results_a if not result.correct}
    errors_b = {result.test_id for result in results_b if not result.correct}
    fixed = errors_a - errors_b
    still_failing = errors_a & errors_b
    new_failures = errors_b - errors_a
    by_id_a = {result.test_id: result for result in results_a}
    by_id_b = {result.test_id: result for result in results_b}

    lines = [
        "=" * 70,
        f"{name_a.upper()} vs {name_b.upper()} COMPARISON",
        "=" * 70,
        "",
        "Overall Accuracy:",
        f"  {name_a}: {accuracy_a:.1%} ({correct_a}/{total_a})",
        f"  {name_b}: {accuracy_b:.1%} ({correct_b}/{total_b})",
        f"  Improvement: {accuracy_b - accuracy_a:+.1%}",
    ]
    lines.extend(_case_block(f"Fixed in {name_b}", fixed, by_id_a))
    lines.extend(_case_block("Still failing", still_failing, by_id_b))
    lines.extend(_case_block(f"New failures in {name_b}", new_failures, by_id_b))
    return "\n".join(lines)


def _result_from_decision(
    test_id: str,
    message: str,
    expected: str,
    category: str,
    decision: RoutingDecision,
) -> EvalResult:
    predicted = decision.department.name
    return EvalResult(
        test_id=test_id,
        message=message,
        expected=expected,
        predicted=predicted,
        correct=predicted == expected,
        reasoning=decision.reasoning,
        category=category,
    )


def _record_span(span, result: EvalResult) -> None:
    from opentelemetry.trace import Status, StatusCode

    span.set_attribute("result.predicted_department", result.predicted)
    span.set_attribute("result.correct", result.correct)
    if result.correct:
        span.set_status(Status(StatusCode.OK))
        return
    span.set_status(Status(StatusCode.ERROR, "Incorrect routing"))
    span.set_attribute("error.expected", result.expected)
    span.set_attribute("error.got", result.predicted)


def _case_block(title: str, test_ids: set[str], by_id: dict[str, EvalResult]) -> list[str]:
    if not test_ids:
        return []
    lines = ["", f"{title} ({len(test_ids)} cases):"]
    for test_id in sorted(test_ids):
        result = by_id[test_id]
        lines.append(f"  [{test_id}] {result.message[:50]}...")
    return lines
