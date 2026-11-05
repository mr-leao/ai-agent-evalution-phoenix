# Manual test runbook

Run these commands from the repository root to exercise `action_autonomy` and `planning_autonomy` by hand, including Phoenix. The V1 sequence is first. The V2 sequence starts at "Planning autonomy" and uses the same virtual environment, Ollama model, and Phoenix container. A command succeeded when it exits without an error and prints the result described under that step. The department the model chooses can differ from the label in `data/v1_test_cases.csv`. That difference is a `FAIL` on the experiment. The command can still succeed.

A full pass calls the model many times. The demo is 6 calls. Each scored prompt is 30 calls. `--compare` scores both prompts, so it is 60 calls. Score commands need Phoenix. Do the short checks first.

## 1. Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Leave the virtual environment active for the rest of this runbook.

## 2. Start Ollama

```bash
ollama pull llama3.1
curl -s http://localhost:11434/api/tags
```

The tags response should include `llama3.1`.

The shell must not override the project defaults with the old Bionic model name. That name returns HTTP 404 from Ollama.

```bash
unset LLM_MODEL LLM_BASE_URL LLM_API_KEY
```

Later commands print the model they used. It should be:

```text
Model: llama3.1 at http://localhost:11434/v1
```

## 3. List prompts

This command does not call the model.

```bash
python -m action_autonomy --list-prompts
```

You should see `prompt_1` and `prompt_2` with a one-line description each.

```bash
python -m action_autonomy --help
```

## 4. Route one message

```bash
python -m action_autonomy --prompt-name prompt_1 --message "I was charged twice for my order"
python -m action_autonomy --prompt-name prompt_2 --message "I was charged twice for my order"
```

Each run prints the prompt name, the model, `Customer`, `Department`, and `Reasoning`. The labeled department for this message is `BILLING` (`TC001` in `data/v1_test_cases.csv`).

## 5. Route the six demo messages

```bash
python -m action_autonomy --prompt-name prompt_1 --demo
python -m action_autonomy --prompt-name prompt_2 --demo
```

Each run prints `ROUTER AGENT DEMO` and six decisions. The messages are a double charge, a late package, a return, a stock question, a password failure, and an upset caller.

## 6. Start Phoenix

Open a second terminal and leave this process running. The score commands in the next steps need it:

```bash
docker run --rm -p 6006:6006 -p 4317:4317 -e PHOENIX_ENABLE_AUTH=false arizephoenix/phoenix
```

The current Phoenix image listens on every network address, so authentication turns on unless `PHOENIX_ENABLE_AUTH` is `false`. This project sends no API key. With authentication on, Phoenix rejects the experiment client and the traces, and the UI asks for a login (`admin@localhost` / `admin` on a fresh container).

Open http://127.0.0.1:6006. The page should load with no username or password.

On Python 3.12 or 3.13, `pip install arize-phoenix` and `python -m action_autonomy --phoenix` can start the UI instead of Docker. On Python 3.15 that command cannot start Phoenix. Do not install `arize-phoenix` or `arize-phoenix-otel` into this environment. Use the Docker command above. If something is already listening on port 6006, `--phoenix` prints `Phoenix is already running` and exits.

## 7. Score each prompt

```bash
python -m action_autonomy --prompt-name prompt_1
python -m action_autonomy --prompt-name prompt_2
```

Each run is 30 model calls. The first run creates the dataset `action-routing-v1`. The second run reuses it. The terminal ends with the experiment name and a compare URL:

```text
Experiment: action-prompt_1
http://127.0.0.1:6006/datasets/<dataset id>/compare?experimentId=<experiment id>
```

The second command names `action-prompt_2`. Open each URL. A row shows the department, the reason, and `department_matches` as `PASS` or `FAIL`. These two commands do not fill the tracing projects. If port 6006 is closed, the command exits with the Docker command from step 6 and does not print a local report.

## 8. Score again and send traces

Back in the first terminal, with Phoenix still running:

```bash
python -m action_autonomy --prompt-name prompt_1 --trace
python -m action_autonomy --prompt-name prompt_2 --trace
```

Each run prints that Phoenix is already running, then:

```text
Tracing enabled for project: V1_action_autonomy_prompt_1
```

The second command names `V1_action_autonomy_prompt_2`. Each run also creates another experiment, again named `action-prompt_1` or `action-prompt_2`, and prints a new compare URL. The score is that experiment. The model calls are in the tracing project.

In the UI:

1. Open the compare URL and read `PASS` or `FAIL`.
2. Choose Traces.
3. Select `V1_action_autonomy_prompt_1`, then `V1_action_autonomy_prompt_2`.
4. Open a model call. It shows the system prompt, the customer message, the department, and the reason. The span status says the call succeeded.

`--message` and `--demo` accept `--trace` too. Those runs record the model call only. They do not create an experiment. If Phoenix is down for one of those commands, the run prints the Docker hint, then `Continuing without traces.`, and still prints the decision.

## 9. Compare the two prompts

```bash
python -m action_autonomy --compare --trace
```

This runs `action-prompt_1` and then `action-prompt_2` on the same 30 cases, about 60 model calls. It prints both experiment URLs and a dataset experiments page:

```text
http://127.0.0.1:6006/datasets/<dataset id>/experiments
```

Open that page and compare the two experiments. With `--trace`, the two tracing projects each receive the model calls. The command does not print a local list of fixed or new failures.

The same comparison without naming the default pair:

```bash
python -m action_autonomy --compare prompt_1 prompt_2
```

## 10. Optional one-off overrides

Score an explicit copy of the same file. After step 7 this reuses the dataset `action-routing-v1` and adds another `action-prompt_1` experiment:

```bash
python -m action_autonomy --prompt-name prompt_1 --test-cases data/v1_test_cases.csv
```

Point one command at another Ollama model without changing the defaults:

```bash
python -m action_autonomy --prompt-name prompt_1 --message "Where is my package?" --model mistral:latest
```

`--base-url` and `--api-key` override the server and key for that one command. Do not pass `data/v2_test_cases.csv` to the router. The planning sequence scores that file. The router scores `test_id`, `customer_message`, `expected_department`, and `category`.

## 11. Planning autonomy

Use the same virtual environment and the same Ollama model. Do not export `LLM_MODEL`. `LLM_PLAN_MODEL` and `LLM_JUDGE_MODEL` are optional and apply only to this package. The router ignores them.

Leave the Phoenix container from the V1 sequence running. If you stopped it, start it again with the same command. Do not start a second container, and do not turn authentication on:

```bash
docker run --rm -p 6006:6006 -p 4317:4317 -e PHOENIX_ENABLE_AUTH=false arizephoenix/phoenix
```

Confirm the setup without a model call:

```bash
unset LLM_MODEL LLM_BASE_URL LLM_API_KEY
python -m planning_autonomy --list-prompts
python -m planning_autonomy --help
```

You should see `prompt_1` (top 2 SOPs) and `prompt_2` (top 4 SOPs).

Route one message, then the demo. Each is one routing call plus one plan call. The demo message is the jacket return, the first row of `data/v2_test_cases.csv`.

```bash
python -m planning_autonomy --prompt-name prompt_1 --message "I bought a jacket last month, but it's too big. Can I return it?"
python -m planning_autonomy --prompt-name prompt_2 --message "I bought a jacket last month, but it's too big. Can I return it?"
python -m planning_autonomy --prompt-name prompt_1 --demo
```

Each run prints the routing model `llama3.1` at `http://localhost:11434/v1`, a department, a reason, SOP ids with scores, and a numbered plan. A department other than `RETURNS` is the model's choice, not a broken command.

The scored runs are long. One prompt is 22 cases and about 66 model calls: route, plan, and judge. `--compare` scores both prompts, about 132 calls. Run them only when you want the full experiment. Phoenix has to be the server from step 6. If it is down, the command exits and does not print a local report.

```bash
python -m planning_autonomy --prompt-name prompt_1
python -m planning_autonomy --prompt-name prompt_2
```

The first run creates the dataset `planning-v2`. The second run reuses it. Each command prints an experiment name, `planning-prompt_1` or `planning-prompt_2`, and a compare URL. Open it. `sop_recall` is a score from 0 to 1. `plan_alignment` is `good`, `partial`, or `bad`. These commands do not fill the tracing projects.

With Phoenix still running:

```bash
python -m planning_autonomy --prompt-name prompt_1 --trace
python -m planning_autonomy --prompt-name prompt_2 --trace
```

The tracing projects are `V2_planning_autonomy_prompt_1` and `V2_planning_autonomy_prompt_2`. In the UI, open Traces and select one of those projects. A model call shows the message, the plan, or the judge reply. Recall and alignment stay on the experiment. V1 traces stay in `V1_action_autonomy_prompt_1` and `V1_action_autonomy_prompt_2`.

```bash
python -m planning_autonomy --compare --trace
python -m planning_autonomy --compare prompt_1 prompt_2
```

The comparison runs both experiments on `planning-v2` and prints both URLs. Read the recall change and the share of `good` plans on the dataset experiments page.

Do not pass `data/v1_test_cases.csv` to this package. That file is the routing set.

```bash
python -m planning_autonomy --prompt-name prompt_1 --test-cases data/v2_test_cases.csv
```

## 12. Stop

In the Phoenix terminal, press Ctrl-C. The `--rm` flag removes that container when it exits. Ollama can keep running.

## Command list

After the virtual environment is active, Ollama is serving the model, and Phoenix is running in another terminal:

```bash
unset LLM_MODEL LLM_BASE_URL LLM_API_KEY
python -m action_autonomy --list-prompts
python -m action_autonomy --help
python -m action_autonomy --prompt-name prompt_1 --message "I was charged twice for my order"
python -m action_autonomy --prompt-name prompt_2 --message "I was charged twice for my order"
python -m action_autonomy --prompt-name prompt_1 --demo
python -m action_autonomy --prompt-name prompt_2 --demo
python -m action_autonomy --prompt-name prompt_1
python -m action_autonomy --prompt-name prompt_2
python -m action_autonomy --prompt-name prompt_1 --trace
python -m action_autonomy --prompt-name prompt_2 --trace
python -m action_autonomy --compare --trace
python -m action_autonomy --compare prompt_1 prompt_2
```

The planning commands below assume that same setup. One scored prompt is about 66 model calls. `--compare` is about 132.

```bash
python -m planning_autonomy --list-prompts
python -m planning_autonomy --help
python -m planning_autonomy --prompt-name prompt_1 --message "I bought a jacket last month, but it's too big. Can I return it?"
python -m planning_autonomy --prompt-name prompt_2 --message "I bought a jacket last month, but it's too big. Can I return it?"
python -m planning_autonomy --prompt-name prompt_1 --demo
python -m planning_autonomy --prompt-name prompt_1
python -m planning_autonomy --prompt-name prompt_2
python -m planning_autonomy --prompt-name prompt_1 --trace
python -m planning_autonomy --prompt-name prompt_2 --trace
python -m planning_autonomy --compare --trace
python -m planning_autonomy --compare prompt_1 prompt_2
```
