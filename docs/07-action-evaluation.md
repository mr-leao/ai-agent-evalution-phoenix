# Action evaluation

A score command runs the router on every row of `data/v1_test_cases.csv` and stores the department check as a Phoenix experiment. The code is `run_action_experiment` and `department_matches` in `action_autonomy/evaluation.py`.

This is the simple test in the repo. One case is one model call and one label. The department matches, or it does not.

Phoenix has to be running on port 6006, with authentication off. If nothing is listening, the command stops and prints the Docker command from the runbook. It does not print a local score report.

## The dataset

The first score command creates a dataset named `action-routing-v1`. A later score command finds that name and reuses it, so the CSV is not uploaded again.

| Role | Columns |
| --- | --- |
| Input | `customer_message` |
| Expected output | `expected_department` |
| Metadata | `test_id`, `category` |

The task receives the customer message. It does not receive the label. It returns `department` and `reasoning`.

## One case

`department_matches` compares the returned department name with `expected_department`.

| Result | Label | Score |
| --- | --- | --- |
| Same department | `PASS` | 1 |
| Any other department | `FAIL` | 0 |

The reason is not scored. A wrong route to `ESCALATION` is still `FAIL` when the label is another department. `ESCALATION` is a valid department. It is the right answer only when the label says so.

Thirty cases are thirty model calls. The command prints the experiment name and the page where that check is stored:

```text
Experiment: action-prompt_1
http://127.0.0.1:6006/datasets/<dataset id>/compare?experimentId=<experiment id>
```

`prompt_2` is the experiment `action-prompt_2` on the same dataset. Open the URL the command prints. Each row shows the department the model returned, the reason, and the `PASS` or `FAIL` label. `test_id` and `category` are on the row as metadata, so misses of the same kind sit together.

The terminal does not print a line per case, an accuracy total, or a miss list. Those facts are the experiment.

## Compare

`--compare` runs `action-prompt_1` and then `action-prompt_2`. That is about 60 model calls. It prints both experiment names and both URLs. The fixed cases, the cases that still fail, and the new failures are the two experiments side by side. The client also prints a dataset experiments page:

```text
http://127.0.0.1:6006/datasets/<dataset id>/experiments
```

The CSV is not modified. A second run calls the model again and adds another experiment with the same name. Temperature `0.1` makes repeats close. It does not make them identical.

Next: [Terminal and Phoenix](08-terminal-and-phoenix.md)
