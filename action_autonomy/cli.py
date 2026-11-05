"""Command line for running a named router prompt."""

import argparse
from dataclasses import replace
from pathlib import Path

from action_autonomy.agent import RouterAgent
from action_autonomy.config import DEFAULT_TEST_CASES, Settings
from action_autonomy.evaluation import (
    load_test_cases,
    run_action_experiment,
    run_demo,
)
from action_autonomy.prompts import available_prompts, get_prompt
from action_autonomy.tracing import (
    PHOENIX_URL,
    can_launch_phoenix,
    collector_reachable,
    enable_tracing,
    project_name_for,
    start_phoenix,
    ui_hint,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="action_autonomy",
        description=(
            "Run the V1 action-autonomy router. "
            "A prompt name selects which system prompt the agent uses."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  python -m action_autonomy --list-prompts
  python -m action_autonomy --prompt-name prompt_1 --demo
  python -m action_autonomy --prompt-name prompt_1 --message "I was charged twice"
  python -m action_autonomy --prompt-name prompt_1
  python -m action_autonomy --prompt-name prompt_2
  python -m action_autonomy --compare
  python -m action_autonomy --phoenix
  python -m action_autonomy --prompt-name prompt_1 --trace
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
        help="Route the built-in sample messages instead of the test set.",
    )
    parser.add_argument(
        "--message",
        help="Route this one customer message and print the decision.",
    )
    parser.add_argument(
        "--compare",
        nargs="*",
        default=None,
        metavar="PROMPT",
        help=(
            "Score two prompts as Phoenix experiments on the same dataset. "
            "With no names, scores prompt_1 and prompt_2."
        ),
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help=(
            "Record model calls in Arize Phoenix. "
            "A score command stores pass or fail on the experiment either way."
        ),
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
        help=f"CSV of labeled messages. Default: {DEFAULT_TEST_CASES}",
    )
    parser.add_argument("--base-url", help="OpenAI-compatible server URL.")
    parser.add_argument("--model", help="Model name served at --base-url.")
    parser.add_argument("--api-key", help="API key sent to the model server.")
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


def _settings_from_args(args: argparse.Namespace) -> Settings:
    settings = Settings.from_env()
    updates = {}
    if args.base_url:
        updates["base_url"] = args.base_url
    if args.model:
        updates["model"] = args.model
    if args.api_key:
        updates["api_key"] = args.api_key
    if not updates:
        return settings
    return replace(settings, **updates)


def _compare(names: list[str], settings: Settings, test_cases: Path, trace: bool) -> None:
    prompts = [get_prompt(name) for name in names]
    frame = load_test_cases(test_cases)
    calls = len(frame) * len(prompts)
    print(
        f"Comparison runs {len(prompts)} experiments on {len(frame)} cases, "
        f"about {calls} model calls.",
        flush=True,
    )
    print(
        "Phoenix stores each experiment. This command does not print a local comparison.",
        flush=True,
    )
    print(flush=True)
    for prompt in prompts:
        session = _trace_session(prompt.name) if trace else None
        agent = RouterAgent(prompt.system_prompt, settings)
        try:
            run_action_experiment(agent, frame, prompt.name)
        finally:
            if session is not None:
                session.flush()
        print(flush=True)


def _run_named_prompt(args: argparse.Namespace, settings: Settings) -> None:
    prompt = get_prompt(args.prompt_name)
    scoring = not args.message and not args.demo
    if scoring:
        # Fail on a missing file before any model call or trace setup.
        frame = load_test_cases(args.test_cases)
    _announce(prompt, settings)
    session = _trace_session(prompt.name) if args.trace else None
    agent = RouterAgent(prompt.system_prompt, settings)
    try:
        if args.message:
            _print_decision(args.message, agent.route(args.message))
            return
        if args.demo:
            run_demo(agent, prompt.name)
            return
        run_action_experiment(agent, frame, prompt.name)
    finally:
        if session is not None:
            session.flush()


def _announce(prompt, settings: Settings) -> None:
    print(f"Prompt: {prompt.name} ({len(prompt.system_prompt)} characters)")
    print(f"Model: {settings.model} at {settings.base_url}")


def _trace_session(prompt_name: str):
    return enable_tracing(project_name_for(prompt_name))


def _print_decision(message: str, decision) -> None:
    print(f"Customer: {message}")
    print(f"Department: {decision.department.name}")
    print(f"Reasoning: {decision.reasoning}")
