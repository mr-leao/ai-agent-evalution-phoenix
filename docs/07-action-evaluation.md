# Action evaluation

Evaluation runs the router on every row of `data/v1_test_cases.csv` and scores the department. The code is `run_evaluation` and `render_metrics` in `action_autonomy/evaluation.py`.

This is the simple test in the repo. One case is one model call and one label. The department matches, or it does not.

## One case

For each row the evaluation:

1. Reads `test_id`, `customer_message`, `expected_department`, and `category`.
2. Calls `RouterAgent.route` with the customer message only.
3. Compares the returned department name with `expected_department`.
4. Prints one line and keeps the result.

A match is `PASS`. Anything else is `FAIL`.

```text
[1/30] TC001: PASS (Expected: BILLING, Got: BILLING)
[8/30] TC008: FAIL (Expected: BILLING, Got: RETURNS)
```

The line does not include the model's reason. The reason is on the decision, and it shows up in Phoenix when you trace the run. This page is only the score.

Thirty cases are thirty model calls. The run prints `Evaluation complete!` after the last row.

## The summary

`render_metrics` then prints:

- Overall accuracy, as a percentage and a count, such as `80.0% (24/30 correct)`.
- A bar for each expected department. The bar is the share of that department's rows that passed. It is grouped by the label, not by the department the model chose.
- Every miss: the test id, the start of the message, the expected department, the predicted department, and the category.

A wrong route to `ESCALATION` is still a `FAIL` when the label is another department. `ESCALATION` is a valid department. It is the right answer only when the label says so.

## Compare

`--compare` runs two prompts on the same 30 rows. That is about 60 model calls. It prints both summaries, then:

| List | Meaning |
| --- | --- |
| Fixed | Failed for the first prompt and passed for the second |
| Still failing | Failed for both |
| New failures | Passed for the first prompt and failed for the second |

The accuracy change is the second prompt's accuracy minus the first. A higher number means more rows match the label. It does not by itself say which prompt text caused the change. Keep the model the same when you compare prompts.

The CSV is not modified. A second run calls the model again. Temperature `0.1` makes repeats close. It does not make them identical.

Next: [Terminal and Phoenix](08-terminal-and-phoenix.md)
