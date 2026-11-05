# Prompts

The action agent does not contain the department rules. Those rules are the system prompt you pass in. Changing the prompt is the change this lesson measures.

Prompts live in `action_autonomy/prompts/`. A module becomes a runnable prompt when it defines `PROMPT_NAME` and `SYSTEM_PROMPT`. `DESCRIPTION` is the line shown when the prompts are listed. The CLI name is `PROMPT_NAME`, not the filename.

## `prompt_1`

`prompt_1` is the baseline. It lists the seven department names and asks for JSON. It does not say what each department handles. It does not say what to do when a word could fit two teams.

Use it first. The misses show what the model does with names alone.

## `prompt_2`

`prompt_2` is the same task with two additions:

- A one-line description of each department.
- Three boundary rules:
  - Login and password problems go to `TECHNICAL_SUPPORT`.
  - Changing a saved payment method goes to `ACCOUNT_MANAGEMENT`.
  - A question about refund status goes to `BILLING`.

Those rules target failures that show up when the prompt is only a list of names: an ambiguous word such as "refund", two issues in one message, and a frustrated customer sent to `ESCALATION` without asking for a manager.

> **The prompt decides the boundary rules. The model decides which rule it follows.**
>
> `prompt_2` can say that refund status belongs to `BILLING`. The schema can force the reply to be one of the seven department names. Neither one picks the department. The model reads the message, reads those rules, and chooses. A `FAIL` is that choice disagreeing with the label. It is still valid JSON.

`prompt_2` is also the routing prompt that planning uses. Planning does not carry its own copy of the department list. The same split applies there: the routing prompt holds the rules, and the routing model chooses the department that retrieval and the plan then use.

## What you change

Add a module beside the others. Define the three names:

```python
PROMPT_NAME = "prompt_3"
DESCRIPTION = "What changed in this prompt."
SYSTEM_PROMPT = """..."""
```

The package loads it on the next run. Keep the JSON shape. The router still expects `department` and `reasoning`.

Change one thing at a time. If you rewrite the prompt and also switch models, the next score cannot tell you which change moved the result.

Next: [Test cases](06-test-cases.md)
