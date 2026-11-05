"""Arize Phoenix tracing for router evaluations.

Phoenix records every model call: the customer message, the system prompt,
the department, the reasoning, token use, and latency. Failed test cases
are marked with an error status so they can be filtered in the UI.
"""

import os
import socket
import threading
from dataclasses import dataclass

PHOENIX_HOST = "127.0.0.1"
PHOENIX_PORT = 6006
PHOENIX_URL = f"http://{PHOENIX_HOST}:{PHOENIX_PORT}"

_instrumentor = None


@dataclass
class TracingSession:
    """OpenTelemetry provider for one Phoenix project."""

    project_name: str
    provider: object
    tracer: object

    def flush(self) -> None:
        flush = getattr(self.provider, "force_flush", None)
        if flush is None:
            return
        try:
            flush(timeout_millis=10000)
        except TypeError:
            flush()


def project_name_for(prompt_name: str) -> str:
    """Phoenix project name used by the lesson for this prompt."""
    return f"V1_action_autonomy_{prompt_name}"


def collector_reachable() -> bool:
    """Return true when something is accepting connections on the Phoenix port."""
    try:
        with socket.create_connection((PHOENIX_HOST, PHOENIX_PORT), timeout=0.5):
            return True
    except OSError:
        return False


def can_launch_phoenix() -> bool:
    """Return true when this environment can start the Phoenix UI in-process."""
    try:
        import phoenix as px
    except ImportError:
        return False
    return hasattr(px, "launch_app")


def start_phoenix(block: bool = False) -> str:
    """Start the local Phoenix UI. Returns the URL.

    When block is true, this process stays running until interrupted.
    Traces are stored by Phoenix and can be opened again later.
    """
    if not can_launch_phoenix():
        raise SystemExit(ui_hint())

    import phoenix as px

    os.environ.setdefault("PHOENIX_HOST", PHOENIX_HOST)
    os.environ.setdefault("PHOENIX_PORT", str(PHOENIX_PORT))
    try:
        session = px.launch_app(port=PHOENIX_PORT)
        url = getattr(session, "url", PHOENIX_URL)
        print(f"Phoenix running at {url}")
    except Exception as exc:
        url = PHOENIX_URL
        print(f"Using the Phoenix server at {url} ({exc}).")

    if block:
        print("Keep this process running while you evaluate with --trace.")
        print("Open the URL above, then choose Traces in the sidebar.")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            print("\nPhoenix stopped.")
    return url


def enable_tracing(project_name: str) -> TracingSession:
    """Send model calls and evaluation spans to a Phoenix project."""
    try:
        from phoenix.otel import register
    except ImportError:
        return _enable_otlp_tracing(project_name)

    from openinference.instrumentation.openai import OpenAIInstrumentor

    instrumentor = _openai_instrumentor(OpenAIInstrumentor)
    if instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.uninstrument()
    provider = register(project_name=project_name, batch=False)
    instrumentor.instrument(tracer_provider=provider)
    print(f"Tracing enabled for project: {project_name}", flush=True)
    return TracingSession(
        project_name=project_name,
        provider=provider,
        tracer=provider.get_tracer("action_autonomy"),
    )


def _enable_otlp_tracing(project_name: str) -> TracingSession:
    """Export traces with the OpenTelemetry SDK when phoenix.otel is absent.

    Python 3.15 cannot install arize-phoenix-otel yet. The same spans still
    go to a Phoenix server that is already running on port 6006.
    """
    from openinference.instrumentation.openai import OpenAIInstrumentor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    provider = TracerProvider(
        resource=Resource.create({"openinference.project.name": project_name})
    )
    provider.add_span_processor(
        SimpleSpanProcessor(OTLPSpanExporter(endpoint=f"{PHOENIX_URL}/v1/traces"))
    )
    instrumentor = _openai_instrumentor(OpenAIInstrumentor)
    if instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.uninstrument()
    instrumentor.instrument(tracer_provider=provider)
    print(f"Tracing enabled for project: {project_name}", flush=True)
    return TracingSession(
        project_name=project_name,
        provider=provider,
        tracer=provider.get_tracer("action_autonomy"),
    )


def _openai_instrumentor(instrumentor_cls):
    """Reuse one instrumentor so a later prompt can switch projects."""
    global _instrumentor
    if _instrumentor is None:
        _instrumentor = instrumentor_cls()
    return _instrumentor


def ui_hint() -> str:
    return (
        "This Python cannot start the Phoenix UI. "
        "arize-phoenix needs arize-phoenix-otel, which has no Python 3.15 build.\n"
        "Start Phoenix with Docker, then rerun with --trace:\n"
        "  docker run --rm -p 6006:6006 -p 4317:4317 arizephoenix/phoenix\n"
        f"Open {PHOENIX_URL} and choose Traces in the sidebar."
    )
