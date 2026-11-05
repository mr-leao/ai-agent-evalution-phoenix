# Learn this repo in order

Read the pages from top to bottom. Each one adds one idea. Action autonomy comes first because its test is one label and one model call. Planning autonomy reuses that step and adds retrieval, a written plan, and a second score.

Commands for both agents stay in [runbook.md](../runbook.md). Run a page's commands only after that page, so the output matches what you just read.

| Step | Page | Question it answers | Where to look |
| --- | --- | --- | --- |
| 1 | [What an agent is here](01-what-an-agent-is.md) | What counts as an agent in this repo, and what does a person still do? | The two packages |
| 2 | [Two kinds of autonomy](02-two-kinds-of-autonomy.md) | Why start with one action, then add a plan? | `action_autonomy`, `planning_autonomy` |
| 3 | [The model call](03-the-model-call.md) | Which model runs, what temperature does, and why the router asks for `json_schema`? | `action_autonomy/config.py`, `action_autonomy/agent.py` |
| 4 | [The action agent](04-the-action-agent.md) | How does one message become one department? | `RouterAgent`, `Department`, `RoutingDecision` |
| 5 | [Prompts](05-prompts.md) | What is `prompt_1`, what did `prompt_2` add, and what are you allowed to change? | `action_autonomy/prompts/` |
| 6 | [Test cases](06-test-cases.md) | What is a labeled row, and why is a demo message not a test? | `data/v1_test_cases.csv` |
| 7 | [Action evaluation](07-action-evaluation.md) | How does a case become `PASS` or `FAIL`, and what does the summary add up? | `action_autonomy/evaluation.py` |
| 8 | [Terminal and Phoenix](08-terminal-and-phoenix.md) | What does the command print, and what does a trace show that the score does not? | `action_autonomy/tracing.py` |
| 9 | [The planning agent](09-the-planning-agent.md) | How does planning reuse the router, then retrieve procedures and write a plan? | `planning_autonomy/agent.py` |
| 10 | [Retrieval](10-retrieval.md) | What is an SOP, how does BM25 rank them, and what changes between top 2 and top 4? | `data/sops/`, `planning_autonomy/sops.py` |
| 11 | [The plan and the judge](11-plan-and-the-judge.md) | What is SOP recall, what is plan alignment, and why can those two scores disagree? | `data/v2_test_cases.csv`, `planning_autonomy/evaluation.py` |
| 12 | [Change one thing and score again](12-change-and-compare.md) | How do you use a miss, a trace, and `--compare` to tell whether a change helped? | Both evaluation modules |

After step 12, use [runbook.md](../runbook.md) as the practice sequence. It runs the same agents in the same order: action first, then planning, on one Ollama model and one Phoenix server.
