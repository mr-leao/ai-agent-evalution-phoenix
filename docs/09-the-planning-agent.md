# The planning agent

`PlanningAgent` in `planning_autonomy/agent.py` takes one customer message and returns a `Plan`. It does three steps. Two of them call the model. Retrieval does not.

## The three steps

1. **Route.** `PlanningAgent` builds a `RouterAgent` with action autonomy's `prompt_2` and the shared connection settings. `route` returns a `RoutingDecision`. The department name and the reason are kept.

> **The prompt decides the boundary rules. The model decides which rule it follows.**
>
> This step is that choice. `prompt_2` states the rules, including "refund status goes to `BILLING`." The routing model chooses one department. Retrieval and the plan use the department it chose, including when that choice is wrong.
2. **Retrieve.** BM25 searches `data/sops/` with the customer message plus the department name. Prompt 1 keeps the top 2 procedures. Prompt 2 keeps the top 4. This step is local. It does not call the model.
3. **Write.** The plan model receives the message, the department, and an excerpt of each retrieved procedure. Temperature is `0`. The reply is the plan text. This call does not use JSON schema.

The result is a `Plan`:

| Field | Meaning |
| --- | --- |
| `customer_message` | The message that was sent |
| `department` | The routed department name |
| `reasoning` | The router's reason |
| `retrieved_sops` | Id, BM25 score, and excerpt for each hit |
| `plan` | The numbered plan |

An empty plan stops the run. A failed model call stops the run. Retrieval always returns the requested number of procedures as long as the SOP files are present. A weak match still comes back with a low score. The agent does not drop it.

## What planning reuses

Planning imports the router, the routing prompt, and the connection settings. It does not reimplement departments. `LLM_PLAN_MODEL` and `LLM_JUDGE_MODEL` override the plan and the judge only. The router keeps using `LLM_MODEL` or the default.

The two planning prompts are configurations, not two plan texts. Both use `planning_autonomy/prompts/plan.py`. They differ by `TOP_K`: 2 for `prompt_1`, 4 for `prompt_2`.

The printed decision for one message shows the customer, the department, the reason, each SOP id with its score, and the plan. That print is not a score. Scoring starts when the rows in `data/v2_test_cases.csv` are labeled.

Next: [Retrieval](10-retrieval.md)
