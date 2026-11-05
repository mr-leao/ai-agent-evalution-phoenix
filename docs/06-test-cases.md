# Test cases

A test case is one labeled row in a CSV file. The agent sees the customer message. It does not see the label. The evaluation compares the agent's result with that label afterward.

A demo message is not a test case. Nothing is labeled, so nothing can pass or fail. A demo shows the shape of one decision. A test case checks that decision against an answer you wrote down in advance.

## The routing file

`data/v1_test_cases.csv` has 30 rows, `TC001` through `TC030`.

| Column | Role |
| --- | --- |
| `test_id` | The name printed with the result, such as `TC001` |
| `customer_message` | The text sent to the router |
| `expected_department` | The correct department name |
| `category` | A short tag for the kind of wording, such as `duplicate_charge` |

The first row is a double charge. The label is `BILLING`. The category says why that row exists: it is a duplicate-charge wording. Other rows cover the rest of the departments, including ambiguous wording and messages with more than one issue.

The category is not sent to the model. It is there so a miss is easier to group when you read the report.

## The planning file

`data/v2_test_cases.csv` has 22 rows. It does not grade the department.

| Column | Role |
| --- | --- |
| `message` | The text sent to the planning agent |
| `complexity` | `simple`, `complex`, or `very_complex` |
| `expected_sops` | Procedure ids the retrieval should find |
| `expected_steps` | Steps a good plan should cover |
| `policy_details` | Policy facts the plan should respect |

A cell can list more than one procedure, separated by commas. There is no `test_id`. The evaluation numbers rows from `0`.

## The files are not interchangeable

The router requires `test_id`, `customer_message`, `expected_department`, and `category`. The planner requires `message`, `complexity`, `expected_sops`, `expected_steps`, and `policy_details`. Passing the wrong file stops the run and names the missing columns.

## A code check is not an evaluation

`tests/test_planning_sops.py` checks the planning code: procedure ids, recall math, and that the routing CSV is rejected. It does not call the model and it does not score the 30 or the 22 messages. The scores in the next pages are the evaluation.

Next: [Action evaluation](07-action-evaluation.md)
