"""Command line for running a named planning prompt."""

import argparse
from dataclasses import replace
from pathlib import Path

from action_autonomy.tracing import (
    PHOENIX_URL,
    can_launch_phoenix,
    collector_reachable,
    enable_tracing,
    start_phoenix,
    ui_hint,
)

from planning_autonomy.agent import PlanningAgent
from planning_autonomy.config import DEFAULT_TEST_CASES, PlanningSettings
from planning_autonomy.evaluation import (
    load_test_cases,
    print_plan,
    render_comparison,
    render_metrics,
    run_demo,
    run_evaluation,
)
from planning_autonomy.prompts import available_prompts, get_prompt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="planning_autonomy",
        description=(
            "Run the V2 planning agent. "
            "A prompt name selects how many SOPs are retrieved."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  python -m planning_autonomy --list-prompts
  python -m planning_autonomy --prompt-name prompt_1 --demo
  python -m planning_autonomy --prompt-name prompt_1 --message "I bought a jacket last month, but it's too big. Can I return it?"
  python -m planning_autonomy --prompt-name prompt_1
  python -m planning_autonomy --prompt-name prompt_2
  python -m planning_autonomy --compare
  python -m planning_autonomy --phoenix
  python -m planning_autonomy --prompt-name prompt_1 --trace
""",
    )
    parser.add_argument(
        "--prompt-name",
        help="Prompt to execute. Use --list-prompts to see the names.",
    )
    parser.add_argument(
        "--list-prompts",
        action="store_true",
        help="Print the available prompt names and exit.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Plan the built-in jacket return message.",
    )
    parser.add_argument(
        "--message",
        help="Plan this one customer message and print the result.",
    )
    parser.add_argument(
        "--compare",
        nargs="*",
        default=None,
        metavar="PROMPT",
        help=(
            "Evaluate two prompts and compare recall and alignment. "
            "With no names, compares prompt_1 and prompt_2."
        ),
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Record model calls and test results in Arize Phoenix.",
    )
    parser.add_argument(
        "--phoenix",
        action="store_true",
        help="Start the Phoenix UI. Alone, this keeps the process running.",
    )
    parser.add_argument(
        "--test-cases",
        type=Path,
        default=DEFAULT_TEST_CASES,
        help=f"CSV of labeled planning cases. Default: {DEFAULT_TEST_CASES}",
    )
    parser.add_argument("--base-url", help="OpenAI-compatible server URL.")
    parser.add_argument("--model", help="Model name served at --base-url.")
    parser.add_argument("--api-key", help="API key sent to the model server.")
    parser.add_argument(
        "--plan-model",
        help="Model for the plan. Defaults to the routing model.",
    )
    parser.add_argument(
        "--judge-model",
        help="Model for plan alignment. Defaults to the routing model.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate(parser, args)

    if args.list_prompts:
        _print_prompts()
        return 0

    wants_run = bool(args.prompt_name or args.compare is not None)
    if args.phoenix and not wants_run:
        if collector_reachable():
            print(f"Phoenix is already running at {PHOENIX_URL}.", flush=True)
            return 0
        start_phoenix(block=True)
        return 0

    settings = _settings_from_args(args)
    if args.trace or (args.phoenix and wants_run):
        _prepare_tracing(args)

    try:
        if args.compare is not None:
            names = args.compare or ["prompt_1", "prompt_2"]
            _compare(names, settings, args.test_cases, trace=args.trace)
            return 0
        _run_named_prompt(args, settings)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    return 0


def _validate(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.list_prompts and any(
        (
            args.prompt_name,
            args.demo,
            args.message,
            args.compare is not None,
            args.trace,
            args.phoenix,
        )
    ):
        parser.error("--list-prompts does not take other options.")
    if args.compare is not None and args.prompt_name:
        parser.error(
            "Pass the two prompt names to --compare. "
            "Omit --prompt-name to compare prompt_1 and prompt_2."
        )
    if args.compare is not None and (args.demo or args.message):
        parser.error("--compare evaluates the test set. Omit --demo and --message.")
    if args.compare is not None and len(args.compare) not in (0, 2):
        parser.error(
            "--compare expects two prompt names, or none to compare prompt_1 and prompt_2."
        )
    if args.demo and args.message:
        parser.error("Use either --demo or --message.")
    if (args.demo or args.message) and not args.prompt_name:
        parser.error("Pass --prompt-name with --demo or --message.")
    if not args.list_prompts and args.compare is None and not args.phoenix and not args.prompt_name:
        parser.error("Pass --prompt-name, or use --compare, --list-prompts, or --phoenix.")


def _prepare_tracing(args: argparse.Namespace) -> None:
    """Start Phoenix when this process can, or skip traces when it is down."""
    if collector_reachable():
        print(f"Phoenix is already running at {PHOENIX_URL}.", flush=True)
        return
    if can_launch_phoenix():
        start_phoenix(block=False)
        return
    print(ui_hint(), flush=True)
    if args.trace:
        print("Continuing without traces.", flush=True)
        args.trace = False


def _print_prompts() -> None:
    prompts = available_prompts()
    if not prompts:
        print("No prompts found.")
        return
    width = max(len(prompt.name) for prompt in prompts.values())
    for prompt in prompts.values():
        print(f"{prompt.name:<{width}}  {prompt.description}")


def _settings_from_args(args: argparse.Namespace) -> PlanningSettings:
    settings = PlanningSettings.from_env()
    connection = settings.connection
    updates = {}
    if args.base_url:
        updates["base_url"] = args.base_url
    if args.model:
        updates["model"] = args.model
    if args.api_key:
        updates["api_key"] = args.api_key
    if updates:
        connection = replace(connection, **updates)
    plan_model = settings.plan_model
    judge_model = settings.judge_model
    if args.model:
        if not settings.plan_model_pinned:
            plan_model = args.model
        if not settings.judge_model_pinned:
            judge_model = args.model
    if args.plan_model:
        plan_model = args.plan_model
    if args.judge_model:
        judge_model = args.judge_model
    return replace(
        settings,
        connection=connection,
        plan_model=plan_model,
        judge_model=judge_model,
    )


def _compare(names: list[str], settings: PlanningSettings, test_cases: Path, trace: bool) -> None:
    prompts = [get_prompt(name) for name in names]
    frame = load_test_cases(test_cases)
    calls = len(frame) * 3 * len(prompts)
    print(
        f"Comparison scores {len(prompts)} prompts on {len(frame)} cases, "
        f"about {calls} model calls.",
        flush=True,
    )
    print(flush=True)
    scored = []
    for prompt in prompts:
        session = _trace_session(prompt.name) if trace else None
        agent = PlanningAgent(prompt.top_k, settings)
        try:
            results = run_evaluation(
                agent,
                frame,
                tracer=None if session is None else session.tracer,
                prompt_name=prompt.name,
            )
        finally:
            if session is not None:
                session.flush()
        print()
        print(render_metrics(results, prompt.name, prompt.top_k))
        print()
        scored.append((prompt, results))
    left, right = scored
    print(
        render_comparison(
            left[0].name,
            left[0].top_k,
            left[1],
            right[0].name,
            right[0].top_k,
            right[1],
        )
    )


def _run_named_prompt(args: argparse.Namespace, settings: PlanningSettings) -> None:
    prompt = get_prompt(args.prompt_name)
    if not args.message and not args.demo:
        frame = load_test_cases(args.test_cases)
    _announce(prompt, settings)
    session = _trace_session(prompt.name) if args.trace else None
    agent = PlanningAgent(prompt.top_k, settings)
    try:
        if args.message:
            print_plan(agent.plan(args.message))
            return
        if args.demo:
            run_demo(agent)
            return
        results = run_evaluation(
            agent,
            frame,
            tracer=None if session is None else session.tracer,
            prompt_name=prompt.name,
        )
    finally:
        if session is not None:
            session.flush()
    print()
    print(render_metrics(results, prompt.name, prompt.top_k))


def _announce(prompt, settings: PlanningSettings) -> None:
    connection = settings.connection
    print(f"Prompt: {prompt.name} (top {prompt.top_k} SOPs)")
    print(f"Routing model: {connection.model} at {connection.base_url}")
    print(f"Plan model: {settings.plan_model}")
    print(f"Judge model: {settings.judge_model}")


def _trace_session(prompt_name: str):
    return enable_tracing(f"V2_planning_autonomy_{prompt_name}")
