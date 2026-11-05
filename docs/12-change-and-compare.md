# Change one thing and score again

The point of the scores and the traces is to make the next edit specific. Change one thing. Run the same cases. Read `--compare`.

## What to read first

Start with the terminal summary.

For action autonomy, open the miss list. Note the test id, the expected department, the department you got, and the category. A cluster of the same category means the prompt is missing one boundary, not thirty unrelated mistakes.

For planning, separate the two scores. Low recall means the needed procedure was not in the top 2 or top 4. A `bad` or `partial` alignment with high recall means retrieval found the procedure and the plan still skipped a step.

Then open the matching Phoenix project and filter for the error status.

| Agent | Error status means | What to open under the span |
| --- | --- | --- |
| Action | The department does not match the label | The system prompt and the `reasoning` field |
| Planning | An expected procedure is missing | The retrieved ids, then the plan call's excerpts |

The action error filter matches `FAIL`. The planning error filter matches incomplete recall. It does not match a bad plan. Use the terminal line for alignment.

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

`--compare` runs the previous variant and the new one on the same file.

Action compare lists cases the new prompt fixed, cases that still fail, and new failures. A rise in accuracy with a list of new failures means the edit helped some rows and hurt others. Read those rows before you keep the prompt.

Planning compare lists recall that went up, recall that is still incomplete, and recall that went down, plus the change in the share of `good` plans. A higher `TOP_K` can raise recall and leave alignment flat. That is a retrieval change, not a better plan.

Then use [runbook.md](../runbook.md). It runs action autonomy first and planning autonomy second, on the same Ollama model and the same Phoenix server.

[Index](index.md)
