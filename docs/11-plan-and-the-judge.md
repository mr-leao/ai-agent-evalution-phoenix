# The plan and the judge

Planning evaluation scores two different things. SOP recall scores retrieval. Plan alignment scores the written plan. They can disagree. The code is `planning_autonomy/evaluation.py`. The labels are the 22 rows in `data/v2_test_cases.csv`.

One row costs three model calls: route, plan, and judge. Retrieval sits between the route and the plan and does not call the model. A full prompt is about 66 calls. `--compare` runs both prompts, about 132 calls.

## SOP recall

Recall is the share of expected procedure ids that appear in the retrieved ids.

| Expected | Retrieved | Recall |
| --- | --- | --- |
| `SOP_001` | `SOP_001` | 100% |
| `SOP_006` and `SOP_003` | `SOP_006` only | 50% |
| none | anything | 100% |

An empty expected set scores 100% because there is nothing missing. Extra retrieved procedures do not reduce the score. Duplicate labels in the CSV count once.

The terminal line for a row looks like this:

```text
[1/22] case 0: recall 100% alignment good (department RETURNS, SOPs SOP_001, SOP_007)
```

`case 0` is the first row. The department is printed so you can see the route. This file does not grade that department.

## Plan alignment

After the plan is written, the judge model reads four things: the customer message, `expected_steps`, `policy_details`, and the plan. The instruction is `planning_autonomy/prompts/judge.py`. Temperature is `0`.

The judge must answer with a line `CLASS: good`, `CLASS: partial`, or `CLASS: bad`.

| Label | Meaning in the prompt |
| --- | --- |
| `good` | The critical steps are covered and the plan can be followed |
| `partial` | The main steps are there and some detail is missing |
| `bad` | Critical steps are missing, or the gaps are large |

Any other reply, a missing `CLASS:` line, or a failed judge call counts as `partial`. The rest of the evaluation continues.

The judge does not see the BM25 scores or the expected SOP ids. A fluent plan that ignored the retrieved procedure can still be labeled `good` if the steps match the label. A complete retrieval can still produce a `bad` plan.

## The summary

After the 22 rows, the report prints mean recall and the counts of `good`, `partial`, and `bad`. `--compare` prints the recall change, the change in the share of good plans, cases whose recall went up, cases that are still incomplete, and cases whose recall went down. A case can be both improved and still incomplete.

## Phoenix for a planning case

A traced row is a span named `test_case_0` through `test_case_21`. The span stores the message, the expected procedure ids, the department, and the retrieved ids. The status is an error when an expected procedure is missing. A `bad` plan does not set that error. Alignment stays on the terminal line.

Under the span you can open the router call, the plan call, and the judge call. The plan call holds the 2000-character excerpts and the numbered plan. Projects are `V2_planning_autonomy_prompt_1` and `V2_planning_autonomy_prompt_2`.

Next: [Change one thing and score again](12-change-and-compare.md)
