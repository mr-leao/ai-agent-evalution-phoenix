# Manual test runbook

Run these commands from the repository root to exercise `action_autonomy` and `planning_autonomy` by hand, including Phoenix. The V1 sequence is first. The V2 sequence starts at "Planning autonomy" and uses the same virtual environment, Ollama model, and Phoenix container. A command succeeded when it exits without an error and prints the result described under that step. The department the model chooses can differ from the label in `data/v1_test_cases.csv`. That is a routing miss to read in the report, not a broken command.

A full pass calls the model many times. The demo is 6 calls. Each scored prompt is 30 calls. `--compare` scores both prompts, so it is 60 calls. Do the short checks first.

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

## 6. Score each prompt

```bash
python -m action_autonomy --prompt-name prompt_1
python -m action_autonomy --prompt-name prompt_2
```

Each run prints 30 lines, `TC001` through `TC030`, marked `PASS` or `FAIL`, then an accuracy report: overall accuracy, a bar per department, and the missed cases. These two commands do not send traces.

## 7. Start Phoenix

Open a second terminal, activate the same virtual environment only if you need it there, and leave this process running:

```bash
docker run --rm -p 6006:6006 -p 4317:4317 -e PHOENIX_ENABLE_AUTH=false arizephoenix/phoenix
```

The current Phoenix image listens on every network address, so authentication turns on unless `PHOENIX_ENABLE_AUTH` is `false`. This project sends traces without an API key. With authentication on, Phoenix rejects those traces, and the UI asks for a login (`admin@localhost` / `admin` on a fresh container).

Open http://127.0.0.1:6006. The page should load with no username or password.

On Python 3.12 or 3.13, `pip install arize-phoenix` and `python -m action_autonomy --phoenix` can start the UI instead of Docker. On Python 3.15 that command cannot start Phoenix. Use the Docker command above. If something is already listening on port 6006, `--phoenix` prints `Phoenix is already running` and exits.

## 8. Score again and send traces

Back in the first terminal:

```bash
python -m action_autonomy --prompt-name prompt_1 --trace
python -m action_autonomy --prompt-name prompt_2 --trace
```

When Phoenix is up, each run prints:

```text
Phoenix is already running at http://127.0.0.1:6006.
Tracing enabled for project: V1_action_autonomy_prompt_1
Each routing decision is being traced in Phoenix.
```

The second command names `V1_action_autonomy_prompt_2`. The terminal report matches step 6. If nothing is listening on port 6006 and this Python cannot start Phoenix, the run prints the Docker hint, then `Continuing without traces.`, and still scores the 30 cases.

In the UI:

1. Choose Traces.
2. Select `V1_action_autonomy_prompt_1`, then `V1_action_autonomy_prompt_2`.
3. Filter for the error status.
4. Open a failed trace. It should show the customer message, the system prompt, the department, and the reason. The span for a case is named `test_case_TC001` and the rest follow that pattern. A miss records `test.expected_department`, `result.predicted_department`, `error.expected`, and `error.got`.

`--message` and `--demo` accept `--trace` too. Those runs record the model call only. The `test_case_*` spans are created by the labeled evaluation.

## 9. Compare the two prompts

```bash
python -m action_autonomy --compare --trace
```

This scores `prompt_1` and then `prompt_2` on the same 30 cases and prints both reports plus a comparison: overall accuracy for each prompt, the change, cases fixed by `prompt_2`, cases still failing, and new failures. With Phoenix still running, the two projects each receive a trace for every case.

The same comparison without naming the default pair:

```bash
python -m action_autonomy --compare prompt_1 prompt_2
```

## 10. Optional one-off overrides

Score an explicit copy of the same file:

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

The scored runs are long. One prompt is 22 cases and about 66 model calls: route, plan, and judge. `--compare` scores both prompts, about 132 calls. Run them only when you want the full report.

```bash
python -m planning_autonomy --prompt-name prompt_1
python -m planning_autonomy --prompt-name prompt_2
```

Each case line shows recall and alignment (`good`, `partial`, or `bad`). The report ends with mean SOP recall and the alignment counts. These commands do not send traces.

With Phoenix still running:

```bash
python -m planning_autonomy --prompt-name prompt_1 --trace
python -m planning_autonomy --prompt-name prompt_2 --trace
```

The projects are `V2_planning_autonomy_prompt_1` and `V2_planning_autonomy_prompt_2`. In the UI, open Traces, select one of those projects, and filter for the error status. A miss is a case whose expected SOP was not retrieved. The span is `test_case_0` through `test_case_21`. It records the message, the expected SOP ids, the department, and the retrieved SOP ids. V1 traces stay in `V1_action_autonomy_prompt_1` and `V1_action_autonomy_prompt_2`.

```bash
python -m planning_autonomy --compare --trace
python -m planning_autonomy --compare prompt_1 prompt_2
```

The comparison prints the recall change, the change in the share of good plans, cases whose recall improved, cases that are still incomplete, and cases whose recall got worse.

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
