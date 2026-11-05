# Plan: `planning_autonomy` package

This plan turns `jupyter/planning_autonomy.ipynb` into a package shaped like `action_autonomy`. The goal is that each runbook can be followed on its own, in either order, on one machine. Running the V1 commands must leave Ollama and Phoenix usable for V2, and the V2 commands must leave them usable for V1. The plan does not change the notebooks.

## How the two notebooks connect

`jupyter/action_autonomy.ipynb` is V1. It routes one customer message to one department. `jupyter/planning_autonomy.ipynb` is V2. It keeps that routing step, retrieves standard operating procedures (SOPs), and writes a multi-step plan.

The connection is the lesson and the shared domain.

- V2's opening says it keeps V1 routing and adds retrieval and planning.
- V1's last cell names V2 as the next step.
- Both use the same seven department names.
- V2's routing text is the V1 Prompt 2 text: the department descriptions and the three boundary rules. In the notebook that text is pasted into `PlanningAgent.route_message`. It is not imported from the V1 notebook or from the `action_autonomy` package.
- V1 scores `data/v1_test_cases.csv` (30 cases, expected department). V2 scores `data/v2_test_cases.csv` (22 cases, expected SOPs, expected steps, and policy details).
- V1's SOPs are unused by the router. V2 reads the nine `sop_*.txt` files in `data/sops/`.
- Both follow the same loop: run a baseline, record traces in Phoenix, design a metric from the misses, change one configuration, and compare. Phoenix project names follow the same pattern: `V1_action_autonomy_prompt_1` and `V2_planning_autonomy_prompt_1`.

There is no code path from one notebook to the other. Each notebook defines its own classes, its own OpenAI client, and its own Colab file paths.

`planning_autonomy` imports the V1 package for routing, connection settings, and Phoenix. That import does not affect either runbook. The V2 commands do not require the V1 commands to have been run, and the V1 commands do not import `planning_autonomy`. Both packages are installed by the same `pip install -r requirements.txt`.

## Both runbooks on one machine

`runbook.md` is the V1 sequence. The V2 sequence is added there, or in a second file that assumes the same repository root and the same virtual environment. A learner can finish one, stop, and start the other later.

These are the conditions that keep the two sequences from breaking each other:

- Both default to `http://localhost:11434/v1` and `mistral:7b-instruct-v0.3-q4_K_M`. The V1 step `unset LLM_MODEL LLM_BASE_URL LLM_API_KEY` is the right setup for V2 as well. V2 does not ask the learner to export a different `LLM_MODEL`.
- V2-only variables are `LLM_PLAN_MODEL` and `LLM_JUDGE_MODEL`. The router never reads them. Leaving them set does not change a later V1 run.
- One Phoenix process owns ports 6006 and 4317. The Docker command is the same for both lessons, including `-e PHOENIX_ENABLE_AUTH=false`. If that port is already open, the runbook says to reuse it. It does not start a second container and it does not turn authentication on.
- Traces go to different Phoenix projects: `V1_action_autonomy_prompt_1`, `V1_action_autonomy_prompt_2`, `V2_planning_autonomy_prompt_1`, and `V2_planning_autonomy_prompt_2`. A V2 run does not write into a V1 project.
- The commands are `python -m action_autonomy` and `python -m planning_autonomy`. Each runbook names its own CSV: `data/v1_test_cases.csv` or `data/v2_test_cases.csv`.
- Neither runbook stops Ollama, changes the pulled model, or edits the other package.

V1 is 6 demo calls, 30 calls per scored prompt, and 60 for `--compare`. V2 adds retrieval and a judge, so one scored prompt is about 66 calls and `--compare` is about 132. The V2 runbook says that before the long commands. Those calls only take time. They do not change the settings the other runbook uses.

## What V2 actually changes

In the notebook, Prompt 1 and Prompt 2 use the same routing text and the same plan text. The variants are configuration.

| | Prompt 1 | Prompt 2 |
| --- | --- | --- |
| SOPs retrieved | 2 | 4 |
| Plan model in code | `gpt-4o-mini` | `gpt-4o` |
| Routing model in code | `gpt-4o`, always | `gpt-4o`, always |
| Judge model in code | `gpt-4o` | `gpt-4o` |

The markdown around those cells disagrees with the code. One cell says the plan model upgrade is `gpt-4o` to `gpt-5`. Another says `gpt-4o-mini` to `gpt-4o`. The comparison print says Prompt 2 uses `gpt-5`. The code is the source of truth for behavior: routing is fixed, and the plan model changes from `gpt-4o-mini` to `gpt-4o`. The package should not hardcode those OpenAI model names. Routing, the plan, and the judge use `action_autonomy.config.Settings`, so the defaults stay `http://localhost:11434/v1` and `mistral:7b-instruct-v0.3-q4_K_M`. The notebook's reported scores (routing about 93%, SOP recall about 54% to 76%, plan alignment about 72% to 100%) were measured on those OpenAI models. A local Mistral run will not reproduce those numbers. The package should print the model it actually called.

V2's notebook asks the model for a department name only, at temperature 0. The package uses V1 instead. `RouterAgent` with `prompt_2` returns JSON with `department` and `reasoning` at temperature `0.1`. An unknown department becomes `ESCALATION`. The department name is what retrieval and the plan prompt receive. The reasoning is kept on the result and printed.

## Package layout

```
planning_autonomy/
  __init__.py
  __main__.py          python -m planning_autonomy
  cli.py
  config.py            plan and judge model overrides on top of V1 Settings
  models.py            RetrievedSOP and Plan
  sops.py              load files, normalize ids, BM25 retrieve
  agent.py             PlanningAgent
  evaluation.py        recall, judge, comparison
  prompts/
    __init__.py        prompt_1 and prompt_2 registries
    prompt_1.py        top_k = 2
    prompt_2.py        top_k = 4
    plan.py            the plan instruction text
    judge.py           the good / partial / bad instruction text
```

`prompts/prompt_1.py` and `prompts/prompt_2.py` export `PROMPT_NAME`, `DESCRIPTION`, and `TOP_K`. The command shape matches `action_autonomy`. The plan instruction lives in one place because the notebook uses one plan text for both variants. Routing comes from `action_autonomy.prompts.get_prompt("prompt_2")`. Departments come from `action_autonomy.models.Department`.

## Runtime settings

`config.py` calls `action_autonomy.config.Settings.from_env()` for the server, API key, routing model, and temperature.

- Those defaults stay `http://localhost:11434/v1`, `mistral:7b-instruct-v0.3-q4_K_M`, API key `ollama`, and temperature `0.1`.
- The plan call and the judge call use that same server and model unless `LLM_PLAN_MODEL` or `LLM_JUDGE_MODEL` is set. Their temperature is 0.
- SOP files default to `data/sops`. Test cases default to `data/v2_test_cases.csv`.
- `--base-url`, `--model`, and `--api-key` override the shared settings for one command. `--plan-model` and `--judge-model` override the two extra calls.

Add `rank-bm25` to `requirements.txt`. Leave Phoenix on the existing Docker path. Python 3.15 still cannot install `arize-phoenix`.

## SOP retrieval

`sops.py` loads every `sop_*.txt` file. There are nine. The notebook's Colab path goes away. The repository path is `data/sops`.

BM25 is keyword search from `rank-bm25`. The corpus is the lowercased, whitespace-split SOP text. The query is the customer message plus the routed department name.

Each hit keeps the SOP id, the BM25 score, and an excerpt. The notebook first keeps 1500 words and then cuts the plan prompt to 2000 characters of that excerpt. The model only sees the second cut. The package should keep that effective limit, 2000 characters, and record the score beside the id.

Ids have to be normalized before recall is computed. Files are named like `sop_001_standard_returns.txt`. The CSV writes `SOP-001_standard_returns`. Both become `SOP_001` by taking the `SOP_` prefix and the digits. Recall is `len(expected ∩ retrieved) / len(expected)`. An empty expected set scores 1.0, matching the notebook.

## Agent

`PlanningAgent.plan(message)` does three steps.

1. `RouterAgent` with V1 `prompt_2` returns a `RoutingDecision`. The department name is passed to retrieval and to the plan prompt.
2. BM25 retrieves `top_k` SOPs for that message and department.
3. The plan model receives the message, the department name, and the excerpts. Temperature is 0. The reply is the plan text. This call does not use JSON schema. The plan is prose.

The result is a `Plan`:

- `customer_message`
- `department`
- `reasoning` from the V1 router
- `retrieved_sops`: id and score, in rank order
- `plan`

The notebook demo message is the first V2 case: "I bought a jacket last month, but it's too big. Can I return it?" The demo command prints the department, the retrieved SOP ids and scores, and the plan.

## Evaluation

`evaluation.py` reads `data/v2_test_cases.csv`. Required columns are `message`, `complexity`, `expected_sops`, `expected_steps`, and `policy_details`. Do not accept `data/v1_test_cases.csv` for this scorer. Its columns are the routing labels.

For each of the 22 cases the evaluation:

- calls `plan`
- normalizes expected and retrieved SOP ids
- computes SOP recall
- asks the judge model to classify the plan as `good`, `partial`, or `bad`

The judge prompt is the notebook's prompt: message, expected steps, policy details, and generated plan. Temperature is 0. The parser reads a line that starts with `CLASS:`. Anything else, including a failed judge call, counts as `partial`, matching the notebook.

The report prints mean SOP recall and the counts of good, partial, and bad. The comparison prints both variants, the recall change, and the change in the share of good plans. It also lists cases whose recall improved, cases that stayed incomplete, and cases that got worse.

A traced run opens one span per case, named `test_case_0` through `test_case_21`, as the notebook does. Attributes include the message, expected SOP ids, routed department, and retrieved SOP ids. A missing expected SOP sets the span status to error. A complete retrieval sets it to ok. Plan alignment is a second model call and stays in the terminal report. It does not need its own span beyond the judge call Phoenix already records from the OpenAI client.

## Commands

`python -m planning_autonomy` follows the router CLI.

```bash
python -m planning_autonomy --list-prompts
python -m planning_autonomy --prompt-name prompt_1 --message "I bought a jacket last month, but it's too big. Can I return it?"
python -m planning_autonomy --prompt-name prompt_1 --demo
python -m planning_autonomy --prompt-name prompt_1
python -m planning_autonomy --prompt-name prompt_2
python -m planning_autonomy --compare
python -m planning_autonomy --prompt-name prompt_1 --trace
python -m planning_autonomy --compare --trace
```

`--compare` with no names scores `prompt_1` then `prompt_2`. `--demo` runs the jacket message. The default action with only `--prompt-name` scores all 22 cases.

Phoenix starts the same way as the router. On Python 3.15 the UI is Docker with authentication off:

```bash
docker run --rm -p 6006:6006 -p 4317:4317 -e PHOENIX_ENABLE_AUTH=false arizephoenix/phoenix
```

`planning_autonomy` calls `action_autonomy.tracing.enable_tracing` with `V2_planning_autonomy_prompt_1` or `V2_planning_autonomy_prompt_2`. It uses the same `collector_reachable`, `start_phoenix`, and `ui_hint` helpers. If port 6006 is closed and this Python cannot launch Phoenix, `--trace` prints the Docker hint and continues without traces.

One evaluation case is two model calls before the judge, and a third call while computing alignment. A traced Prompt 1 run is about 66 calls. `--compare` is about 132. The runbook should say that before the long commands.

## Docs to update when the package exists

- `README.md`: a short V2 section that points at the package, the two metrics, and the Phoenix project names.
- `runbook.md`: a second sequence for `planning_autonomy`. It starts from the same virtual environment, the same Ollama model, and a Phoenix container that is already running or is started with the same Docker command. It does not repeat a setup step that would change V1.
- `requirements.txt`: add `rank-bm25` next to the packages V1 already installs, so one `pip install -r requirements.txt` covers both runbooks.

The notebooks stay as the lesson. The package is the runnable form, which is the same split V1 already has.

## Implementation order

1. SOP loading, id normalization, and BM25 retrieval, with a small check that `SOP-001_standard_returns` and `sop_001_standard_returns.txt` both become `SOP_001`. This check does not call a model.
2. `Plan` and `PlanningAgent`, routing through V1 `RouterAgent` and `prompt_2`.
3. One-message and demo commands against the local Ollama model.
4. Recall, judge, and the terminal report.
5. `--compare`.
6. Phoenix project names and `--trace`.
7. README and runbook sections.

## Out of scope

- Editing either notebook.
- Re-scoring V1's 30 routing cases inside this package.
- Embedding search, a vector store, or a new SOP corpus.
- A runbook step that changes `LLM_MODEL`, the Ollama model, or Phoenix authentication in order to run the other lesson.
- Treating the notebook's published percentages as pass bars for the local model.
