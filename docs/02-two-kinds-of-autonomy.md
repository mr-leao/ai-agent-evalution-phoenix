# Two kinds of autonomy

Autonomy here means how much of the support task the agent does before a person takes over. This repo has two levels. Build and measure the first one before you add the second.

## Action autonomy

The agent performs one action. It classifies the message and names a department.

| | |
| --- | --- |
| Input | A customer message |
| Action | Choose one department |
| Output | A department and a short reason |
| Handoff | A person in that department takes the case |

That is a closed task. There are seven departments. The answer is either the right one or the wrong one. You can score it with a label.

## Planning autonomy

The agent keeps the routing action, then does more. It retrieves written procedures and drafts a multi-step plan. A person follows the plan.

| | |
| --- | --- |
| Input | A customer message |
| Actions | Route, retrieve procedures, write a plan |
| Output | A department, the retrieved procedures, and the plan |
| Handoff | A person carries out the plan |

The plan is prose. "Right" is no longer a single department name. You need a different score, which is why planning comes second.

`planning_autonomy` imports `RouterAgent` from `action_autonomy`. The route is the same code you already measured. Planning adds the steps after it.

Next: [The model call](03-the-model-call.md)
