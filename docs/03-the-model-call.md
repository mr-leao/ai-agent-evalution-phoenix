# The model call

Both agents talk to a chat model through an OpenAI-compatible client. The defaults live in `action_autonomy/config.py`. Planning reads those same settings. It does not define a second server.

| Setting | Default | Environment variable |
| --- | --- | --- |
| Server | `http://localhost:11434/v1` | `LLM_BASE_URL` |
| Model | `llama3.1` | `LLM_MODEL` |
| API key | `ollama` | `LLM_API_KEY`, or `OPENAI_API_KEY` if the first is unset |
| Temperature | `0.1` | `LLM_TEMPERATURE` |

The server is local Ollama. Ollama ignores the API key. The client still sends one, because the OpenAI library requires a value. A `.env` file in the repository root can set the same variables. Leave `LLM_MODEL` unset when you want the default model, `llama3.1`. A leftover value such as `mistral-7b-instruct-v0.3` overrides that default, and Ollama returns HTTP 404 when that name is not pulled.

## Temperature

Each time the model writes the next word, it has a ranked list of likely words. Temperature is how willing it is to skip the top of that list.

Think of a multiple-choice answer. The model believes `BILLING` is the best choice for "I was charged twice," and `RETURNS` is the next one down, because the message sounds a bit like a refund.

| Temperature | What the model does with that list |
| --- | --- |
| `0` | Always takes the top choice. A second run of the same message stays on `BILLING`. |
| `0.1` | Almost always takes the top choice. A rare word can still differ, so two runs are close, not guaranteed identical. |
| `0.8` or `1` | Often takes the second or third choice. One run can say `BILLING`. The next run of the same message can say `RETURNS`. |

The router uses `0.1`, from `LLM_TEMPERATURE`. You score the same 30 messages twice and compare the totals. If the department jumps around on its own, a higher score might be luck rather than a better prompt.

The plan and the judge use `0`, set as `PLAN_TEMPERATURE` in `planning_autonomy/config.py`. You want the same plan to stay put while you read it.

Temperature does not change the boundary rules in the prompt, and it does not change which model is running. It only changes how often the model leaves its top choice.

## JSON schema on the router

`RouterAgent` asks for `json_schema` with `strict` set. The schema requires two fields:

- `department`, one of the seven enum names such as `BILLING`
- `reasoning`, a string

That is the block in `action_autonomy/agent.py` whose type is `json_schema`. The schema keeps the reply in a shape the code can parse. After the call, `department_from_name` still maps a missing or unknown name to `ESCALATION`.

> **The schema decides the shape. The prompt decides the boundary rules. The model decides which rule it follows.**
>
> A reply of `{"department": "RETURNS", "reasoning": "..."}` satisfies the schema even when the label is `BILLING`. The correct department is a model choice, which is what the evaluation measures.

The plan call does not use this schema. A plan is numbered prose, not a department.

## Who uses which model

The routing call uses `Settings.model`. The plan call uses `LLM_PLAN_MODEL` when that variable is set, and otherwise the same routing model. The judge uses `LLM_JUDGE_MODEL` the same way. The router never reads those two variables. Setting them does not change an action-autonomy run.

Next: [The action agent](04-the-action-agent.md)
