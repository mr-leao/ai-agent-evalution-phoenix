"""Phoenix datasets and experiments for the score commands.

The Docker server on port 6006 stores the dataset and the experiment.
These commands do not score locally when that server is down.
"""

from typing import Any, Callable

import httpx
import pandas as pd
from phoenix.client import Client

from action_autonomy.tracing import PHOENIX_URL, collector_reachable

TASK_TIMEOUT_SECONDS = 120


def score_requires_phoenix_message() -> str:
    """Tell the user how to start the server the score commands require."""
    return (
        "Scoring needs the Phoenix server on port 6006. "
        "This command does not print a local score report.\n"
        "Start Phoenix with Docker, then rerun the score command:\n"
        "  docker run --rm -p 6006:6006 -p 4317:4317 "
        "-e PHOENIX_ENABLE_AUTH=false arizephoenix/phoenix\n"
        f"Open {PHOENIX_URL}. The experiment is where the score is stored."
    )


def require_client() -> Client:
    """Return a client for the runbook server, or exit when it is not usable.

    The client sends no API key. The server must be started with
    PHOENIX_ENABLE_AUTH=false.
    """
    if not collector_reachable():
        raise SystemExit(score_requires_phoenix_message())
    client = Client(base_url=PHOENIX_URL)
    try:
        client.datasets.list(limit=1)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            raise SystemExit(score_requires_phoenix_message()) from exc
        raise SystemExit(_http_error(exc)) from exc
    return client


def get_or_create_dataset(
    client: Client,
    *,
    name: str,
    dataframe: pd.DataFrame,
    input_keys: list[str],
    output_keys: list[str],
    metadata_keys: list[str],
    description: str,
) -> Any:
    """Reuse a dataset with this name. Upload the CSV only when it is missing."""
    try:
        dataset = client.datasets.get_dataset(dataset=name)
    except ValueError as exc:
        if "Dataset not found" not in str(exc):
            raise
        dataset = None
    except httpx.HTTPStatusError as exc:
        raise SystemExit(_http_error(exc)) from exc
    if dataset is not None:
        print(
            f"Using dataset {name} ({len(dataset)} examples).",
            flush=True,
        )
        if len(dataset) != len(dataframe):
            print(
                f"The CSV has {len(dataframe)} rows and was not uploaded again.",
                flush=True,
            )
        return dataset
    print(f"Creating dataset {name} ({len(dataframe)} examples).", flush=True)
    try:
        return client.datasets.create_dataset(
            name=name,
            dataframe=dataframe,
            input_keys=input_keys,
            output_keys=output_keys,
            metadata_keys=metadata_keys,
            dataset_description=description,
        )
    except httpx.HTTPStatusError as exc:
        raise SystemExit(_http_error(exc)) from exc


def run_experiment(
    client: Client,
    *,
    dataset: Any,
    task: Callable[..., Any],
    evaluators: list[Any],
    experiment_name: str,
    experiment_description: str,
    experiment_metadata: dict[str, Any] | None = None,
) -> Any:
    """Run one experiment and print its name and compare URL."""
    try:
        result = client.experiments.run_experiment(
            dataset=dataset,
            task=task,
            evaluators=evaluators,
            experiment_name=experiment_name,
            experiment_description=experiment_description,
            experiment_metadata=experiment_metadata,
            print_summary=True,
            timeout=TASK_TIMEOUT_SECONDS,
        )
    except httpx.HTTPStatusError as exc:
        raise SystemExit(_http_error(exc)) from exc
    url = client.experiments.get_experiment_url(dataset.id, result["experiment_id"])
    print(f"Experiment: {experiment_name}", flush=True)
    print(url, flush=True)
    return result


def _http_error(exc: httpx.HTTPStatusError) -> str:
    return (
        f"Phoenix returned HTTP {exc.response.status_code} "
        f"for {exc.request.url}."
    )
