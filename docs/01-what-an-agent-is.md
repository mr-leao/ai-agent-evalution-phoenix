# What an agent is here

An agent in this repo is a small program that takes one customer message, calls a chat model, and returns a result a person can act on.

The model does not talk to the customer. It does not look up a live order. It does not send an email. A person still handles the customer. The agent's job is to prepare that person's next step.

Two agents are in this repo. The names say how much of the job each one is allowed to do. Both start from the same customer message.

**Action** means one action and then stop. That action is the routing decision: pick one department and give a short reason. In the code this is `RouterAgent.route` in `action_autonomy`. A person in that department takes the case.

**Planning** means several steps before the handoff: route, retrieve procedures, and write a plan. In the code this is `PlanningAgent.plan` in `planning_autonomy`. A person follows the plan.

| Name | The agent's job | What happens next |
| --- | --- | --- |
| Action | One action: pick a department and give a short reason | A person takes the case |
| Planning | Several steps: route, retrieve procedures, write a plan | A person follows the plan |

Next: [Two kinds of autonomy](02-two-kinds-of-autonomy.md)
