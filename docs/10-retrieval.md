# Retrieval

Retrieval picks written procedures for the plan. The procedures are the `sop_*.txt` files in `data/sops/`. There are nine. Each file is a standard operating procedure: returns, damaged items, billing disputes, account access, and the others named in that folder.

The planner does not send every file to the model. It ranks them and keeps the top few. The code is `planning_autonomy/sops.py`.

## How a file becomes an id

The evaluation compares ids, not filenames. `normalize_sop_name` reduces both forms to the number:

| Written as | Counted as |
| --- | --- |
| `sop_001_standard_returns.txt` | `SOP_001` |
| `SOP-001_standard_returns` | `SOP_001` |

A CSV cell can list several ids separated by commas. `SOP-002_damaged_items,SOP-002_damaged_items` counts once, as `SOP_002`.

## BM25

BM25 is a keyword ranker from the `rank-bm25` package. The corpus is the lowercased words of each SOP file. The query is the customer message plus the routed department name, also split into words.

Every file gets a score. The highest scores are kept. `top_k` is 2 or 4, depending on the prompt. The score is printed next to the id. A higher score means more word overlap with the query. It does not mean the procedure is the labeled one.

The plan sees the first 2000 characters of each chosen file (`EXCERPT_CHARS`). The rest of a long procedure is not in the prompt.

## What changes between the two prompts

The plan instructions stay the same. Prompt 2 puts two more excerpts into the prompt than prompt 1. That can raise recall, because a needed procedure has more room to appear in the top results. It can also add a procedure the case did not ask for. Extra procedures do not lower recall. Recall only asks whether the expected ids were present.

Retrieval can rank a loosely related file above the labeled one. The jacket-return message is labeled `SOP_001`. A run can still place another SOP first and `SOP_001` second. With top 2, that case can still score full recall. With a tighter top 1, it would not. Read the ids and the scores, not only the plan text.

Next: [The plan and the judge](11-plan-and-the-judge.md)
