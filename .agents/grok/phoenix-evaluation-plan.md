# Plan: Phoenix evaluation

Replace the local score loop with a Phoenix experiment. `main` keeps the current evaluation. This work stays on `phoenix-evals`.

The agents stay. The CSV rows stay. The score moves into Phoenix: a dataset holds the labels, a task calls the agent, and an evaluator writes the label Phoenix stores. The Docker server on port 6006 remains the server. This branch does not run Phoenix inside Python and does not downgrade Python.

## Client-side SDK

Use the client-side SDK. Do not attach evaluators in the Phoenix UI.

The task is the Python agent: `RouterAgent.route`, BM25 over `data/sops/`, and `PlanningAgent.plan`. A server-side evaluator runs in the Playground or in Phoenix's code sandbox. The Playground can repeat a prompt. It cannot run this package. A sandbox script cannot import `normalize_sop_name` or read the SOP files, so the recall rule and the "missing `CLASS:` counts as `partial`" rule would be a second copy.

`arize-phoenix-client` uploads the dataset, runs the experiment, and stores each evaluator result. `arize-phoenix-evals` is available for the judge call. The department check and SOP recall stay ordinary Python functions passed in `evaluators=[...]`. The Docker UI is where you read the experiment. It is not where the score is computed.

`arize-phoenix-otel` stays out. Tracing already exports spans with the OpenTelemetry SDK. That package only wraps the same export. Evaluation does not need it.

## What is replaced

`action_autonomy/evaluation.py` and `planning_autonomy/evaluation.py` currently walk the CSV, call the agent, compare the output with the label, and print the score. That comparison becomes a Phoenix evaluator.

| Today | After |
| --- | --- |
| `PASS` or `FAIL` printed for each routing row | A code evaluator: returned department equals `expected_department` |
| Accuracy, department bars, and the miss list | The experiment summary in Phoenix. The command prints the experiment name and the URL |
| SOP recall | A code evaluator using the same id rules as `recall` in `planning_autonomy/evaluation.py` |
| `good`, `partial`, or `bad` | The existing judge prompt, called from an evaluator. A missing `CLASS:` line or a failed judge call is still `partial` |
| `--compare` printing fixed and new failures | Two experiments on the same dataset. Phoenix shows the comparison |

`--message` and `--demo` stay local. They have no label, so they are not experiments.

`--trace` stays. It still sends the model call to Phoenix through the OpenTelemetry exporter this repo already uses. It does not start using `arize-phoenix-otel`. When a score command also traces, the experiment result is the score and the trace is the input and output. The span status `ok` or `error` from the old loop goes away, because that loop is the thing being removed. The pass or fail for a row is the evaluator result.

## Packages

Add these to `requirements.txt` and pin the versions that install on Python 3.15:

- `arize-phoenix-client` (3.7.0 allows `>=3.11,<3.16`)
- `arize-phoenix-evals` (3.9.5 allows `>=3.11,<3.16`)

Do not add `arize-phoenix` or `arize-phoenix-otel`. The server package depends on `arize-phoenix-otel` 0.17.2, which requires Python `<3.15`. This environment is 3.15.2. Docker already provides the server.

Confirm the evaluator function signature against the installed client before writing the CLI. The call shape to target is:

```python
from phoenix.client import Client

client = Client(base_url="http://127.0.0.1:6006")
client.experiments.run_experiment(
    dataset=dataset,
    task=task,
    evaluators=[department_matches],
    experiment_name="action-prompt_1",
)
```

The server must be the same one the runbook starts, with `PHOENIX_ENABLE_AUTH=false`. The client sends no API key. If port 6006 is closed, the score command exits with the Docker hint. It does not fall back to the old local report.

## Datasets

Build two datasets from the CSVs. Look up each dataset by name and create it only when it is missing, so a second run does not upload a duplicate.

**Action** from `data/v1_test_cases.csv`, named `action-routing-v1`:

| Role | Columns |
| --- | --- |
| Input | `customer_message` |
| Expected output | `expected_department` |
| Metadata | `test_id`, `category` |

**Planning** from `data/v2_test_cases.csv`, named `planning-v2`:

| Role | Columns |
| --- | --- |
| Input | `message` |
| Expected output | `expected_sops`, `expected_steps`, `policy_details` |
| Metadata | `complexity`, and the row number `0` through `21` |

The task sees the input. The evaluator sees the input, the task output, and the expected output. The agent still does not see the label.

## Tasks

A task returns a JSON-serializable dict. It does not return `RoutingDecision` or `Plan`.

The action task builds a `RouterAgent` with the selected system prompt and the shared settings. It returns `department` and `reasoning`.

The planning task builds a `PlanningAgent` with that prompt's `TOP_K`. It returns `department`, `reasoning`, the normalized retrieved SOP ids, and the plan text.

One experiment uses one prompt. `action-prompt_1` and `action-prompt_2` are separate experiments on `action-routing-v1`. `planning-prompt_1` and `planning-prompt_2` are separate experiments on `planning-v2`.

## Evaluators

Keep the pure checks. Move them out of the print loop and call them from evaluators.

- `department_matches` is a code evaluator. It compares the task's `department` with `expected_department`. The result is the same fact as today's `PASS` or `FAIL`.
- `sop_recall` is a code evaluator. It uses `normalize_sop_name` and `recall`. An empty expected set still scores `1.0`.
- `plan_alignment` calls the current judge with `PLAN_TEMPERATURE` and the prompt in `planning_autonomy/prompts/judge.py`. Do not switch this to a Phoenix built-in template. Those templates grade hallucination and relevance, which are different questions.

A unit test can call `department_matches` and `sop_recall` with fake dicts. That test does not need Docker or a model. The live experiment stays a manual runbook step.

## Commands

The score commands keep their names.

```bash
python -m action_autonomy --prompt-name prompt_1
python -m action_autonomy --compare
python -m planning_autonomy --prompt-name prompt_1
python -m planning_autonomy --compare
```

Each score command checks that Phoenix is up, reuses or creates the dataset, runs the experiment, and prints the experiment name. The per-row label and the comparison are in the Phoenix experiments view. `--compare` runs the two experiments in order. It does not reimplement the fixed, still-failing, and new-failure lists once those lists are visible on the two experiments.

A planning experiment is still about 66 model calls. A comparison is still about 132. Phoenix does not remove those calls.

## Docs to update after the commands work

- `docs/07-action-evaluation.md` and `docs/11-plan-and-the-judge.md`: the score is an experiment result.
- `docs/08-terminal-and-phoenix.md`: input and output stay on the trace. Pass or fail moves to the experiment. The trace status is no longer the score.
- `docs/12-change-and-compare.md` and `runbook.md`: point the score steps at the experiment names.
- `docs/index.md`: steps 7 and 11 name the experiment instead of only the local evaluation module.

Leave those pages unchanged until one action experiment and one planning experiment have been seen in the UI.

## Order

1. Pin the two client packages and import `Client` against the Docker server.
2. Create or reuse `action-routing-v1`.
3. Run `action-prompt_1` and confirm one row shows the department check in the UI.
4. Connect the action score and compare commands to experiments.
5. Add `planning-v2`, `sop_recall`, and `plan_alignment`.
6. Connect the planning score and compare commands.
7. Delete the print loop that scores rows itself. Keep `recall`, `normalize_sop_name`, and `parse_alignment`.
8. Update the docs and the runbook from a real experiment URL.

## Out of scope

- Server-side evaluators: the dataset Evaluators tab, the Playground, and Phoenix's code sandbox.
- Phoenix templates for hallucination, relevance, or toxicity.
- A new judge rubric.
- Installing the Phoenix server into this virtual environment.
- Changing `RouterAgent`, the prompts, or the CSV columns.
- Treating `--message` or `--demo` as an experiment.
