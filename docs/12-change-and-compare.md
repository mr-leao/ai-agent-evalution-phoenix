# Change one thing and score again

The point of the scores and the traces is to make the next edit specific. Change one thing. Run the same cases. Compare the two experiments.

## What to read first

Open the compare URL the score command prints.

For action autonomy, read `department_matches`. Note the test id, the expected department, the department you got, and the category. A cluster of the same category means the prompt is missing one boundary, not thirty unrelated mistakes.

For planning, separate the two scores. Low `sop_recall` means the needed procedure was not in the top 2 or top 4. A `bad` or `partial` alignment with recall 1 means retrieval found the procedure and the plan still skipped a step.

Then open the tracing project from a run that used `--trace`. The model call has the system prompt, the message, and the reply. Its status says the call succeeded. The score stays on the experiment.

| Agent | Where the miss is | What to open in the trace |
| --- | --- | --- |
| Action | `department_matches` is `FAIL` | The system prompt and the `reasoning` field |
| Planning | `sop_recall` is below 1 | The retrieved ids, then the plan call's excerpts |
| Planning | `plan_alignment` is `partial` or `bad` | The plan text and the judge reply |

## What to change

| You saw | Change |
| --- | --- |
| The same kind of message routed to the wrong department | A department description or a boundary rule in a new action prompt |
| The right SOP ranked just below the cutoff | `TOP_K` on the planning prompt, from 2 to 4 |
| The right SOP present and the plan missing a step | The plan instructions in `planning_autonomy/prompts/plan.py` |
| The judge label looks unrelated to the steps | The judge instructions, knowing a broken judge reply becomes `partial` |

Leave the model, the temperature, and the CSV fixed while you do this. Otherwise the comparison mixes two changes.

Add an action prompt as a new module with `PROMPT_NAME`, `DESCRIPTION`, and `SYSTEM_PROMPT`. Keep the JSON shape. Planning prompt modules only need `PROMPT_NAME`, `DESCRIPTION`, and `TOP_K`. They share the plan text.

## How you know it helped

`--compare` runs the previous variant and the new one on the same dataset. It prints two experiment URLs. Open the dataset experiments page the command prints and put the two experiments side by side.

For action, `action-prompt_1` and `action-prompt_2` share `action-routing-v1`. Read the rows the new prompt turned from `FAIL` to `PASS`, the rows that still fail, and the rows that newly fail. A higher pass count with new failures means the edit helped some rows and hurt others. Read those rows before you keep the prompt.

For planning, `planning-prompt_1` and `planning-prompt_2` share `planning-v2`. Read recall that went up, recall that is still below 1, and recall that went down, plus the share of `good` plans. A higher `TOP_K` can raise recall and leave alignment flat. That is a retrieval change, not a better plan.

Then use [runbook.md](../runbook.md). It runs action autonomy first and planning autonomy second, on the same Ollama model and the same Phoenix server.

[Index](index.md)
