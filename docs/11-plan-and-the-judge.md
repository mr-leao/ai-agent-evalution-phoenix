# The plan and the judge

Planning evaluation scores two different things. SOP recall scores retrieval. Plan alignment scores the written plan. They can disagree. The code is `sop_recall`, `plan_alignment`, and `recall` in `planning_autonomy/evaluation.py`. The labels are the 22 rows in `data/v2_test_cases.csv`.

One row costs three model calls: route, plan, and judge. Retrieval sits between the route and the plan and does not call the model. A full prompt is about 66 calls. `--compare` runs both prompts, about 132 calls. Phoenix does not remove those calls.

The score command stores both checks as an experiment named `planning-prompt_1` or `planning-prompt_2` on the dataset `planning-v2`. The same Phoenix server as the action scores has to be up. If port 6006 is closed, the command exits and does not print a local score report.

## The dataset

The first planning score creates `planning-v2`. A later run reuses that name.

| Role | Columns |
| --- | --- |
| Input | `message` |
| Expected output | `expected_sops`, `expected_steps`, `policy_details` |
| Metadata | `complexity`, and the row number `0` through `21` |

The task returns the department, the reason, the normalized SOP ids, and the plan text. It does not see the expected procedures or the expected steps.

## SOP recall

`sop_recall` uses `recall`. Recall is the share of expected procedure ids that appear in the retrieved ids.

| Expected | Retrieved | Recall |
| --- | --- | --- |
| `SOP_001` | `SOP_001` | 1 |
| `SOP_006` and `SOP_003` | `SOP_006` only | 0.5 |
| none | anything | 1 |

An empty expected set scores 1 because there is nothing missing. Extra retrieved procedures do not reduce the score. Duplicate labels in the CSV count once.

The department is in the task output so you can see the route. This dataset does not grade that department.

## Plan alignment

`plan_alignment` calls the judge in `planning_autonomy/prompts/judge.py` through `classify_plan`. Temperature is `0`. The judge reads the customer message, `expected_steps`, `policy_details`, and the plan.

The judge must answer with a line `CLASS: good`, `CLASS: partial`, or `CLASS: bad`.

| Label | Meaning in the prompt |
| --- | --- |
| `good` | The critical steps are covered and the plan can be followed |
| `partial` | The main steps are there and some detail is missing |
| `bad` | Critical steps are missing, or the gaps are large |

Any other reply, a missing `CLASS:` line, or a failed judge call counts as `partial`. The rest of the evaluation continues.

The judge does not see the BM25 scores or the expected SOP ids. A fluent plan that ignored the retrieved procedure can still be labeled `good` if the steps match the label. A complete retrieval can still produce a `bad` plan.

On the experiment, `sop_recall` is a score and `plan_alignment` is the label `good`, `partial`, or `bad`. The command prints the experiment name and the compare URL. It does not print a recall total or the alignment counts. Read those on the experiment. `--compare` runs both experiments on `planning-v2` and leaves the comparison there.

## Phoenix for a planning case

The compare URL is the score. With `--trace`, the model calls are also in `V2_planning_autonomy_prompt_1` or `V2_planning_autonomy_prompt_2`. Open the router call, the plan call, and the judge call. The plan call holds the 2000-character excerpts and the numbered plan.

The trace status says whether those calls succeeded. A missing expected procedure is a `sop_recall` below 1 on the experiment. A `bad` plan is the `plan_alignment` label. Neither one is the trace status.

Next: [Change one thing and score again](12-change-and-compare.md)
