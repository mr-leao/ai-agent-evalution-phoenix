# Terminal and Phoenix

For one traced case, Phoenix shows the input, the output, and the pass or fail status. The terminal shows the same pass or fail as a line, then adds the totals across every case. Those totals exist only in the terminal.

A run without tracing prints the same scores and writes nothing to Phoenix. Tracing does not change the score. It sends a trace when something is listening on port 6006. If Phoenix is down and this Python cannot start it, the run says it is continuing without traces and still prints the scores.

Start Phoenix from [runbook.md](../runbook.md). Leave authentication off (`PHOENIX_ENABLE_AUTH=false`). These agents do not send an API key. With authentication on, Phoenix rejects the traces.

## What each place shows

| | Terminal | Phoenix |
| --- | --- | --- |
| One message or the demo | The decision for that message | Input and output of the model call. No pass or fail, because there is no label |
| One evaluation case | `PASS` or `FAIL`, the expected department, and the department returned | Input, output, and a status: ok for a pass, error for a fail |
| After every case | Accuracy, the department bars, and the miss list | No total. Filter for the error status to see the failed cases, one trace at a time |

## The action span

For a traced action run, each case is a span named `test_case_TC001` and so on. Open that span and you see three things.

| What you see | Where it comes from |
| --- | --- |
| Input | The system prompt and the customer message sent to the model |
| Output | The JSON the model returned: `department` and `reasoning` |
| Status | Ok when `department` matches the label. Error, "Incorrect routing," when it does not |

The status is the same fact as `PASS` or `FAIL` on the terminal line. The span also stores `test.expected_department`, `result.predicted_department`, `result.correct`, and, on a failure, `error.expected` and `error.got`.

The model call sits under the case span. That is where the input and output are recorded, including the reason. Token use and latency are on that call too. The terminal line does not print the reason. The miss list does not either.

## Projects

Each prompt has its own Phoenix project, so two runs do not mix.

| Run | Project |
| --- | --- |
| Action `prompt_1` | `V1_action_autonomy_prompt_1` |
| Action `prompt_2` | `V1_action_autonomy_prompt_2` |
| Planning `prompt_1` | `V2_planning_autonomy_prompt_1` |
| Planning `prompt_2` | `V2_planning_autonomy_prompt_2` |

Open http://127.0.0.1:6006, choose Traces, select the project, and filter for the error status.

Planning spans are covered with the planning scores. A planning trace also has input, output, and a status. That status is an error when an expected procedure is missing. It is not the judge's `good`, `partial`, or `bad` label. The totals, mean recall and the alignment counts, stay in the terminal.

Next: [The planning agent](09-the-planning-agent.md)
