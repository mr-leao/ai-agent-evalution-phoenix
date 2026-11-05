"""Named planning configurations.

Each module that defines PROMPT_NAME and TOP_K is a variant you can run
with --prompt-name. The plan text itself is shared.
"""

import importlib
import pkgutil
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class PlanningPrompt:
    """How many SOPs one variant retrieves."""

    name: str
    description: str
    top_k: int


@lru_cache(maxsize=1)
def available_prompts() -> dict[str, PlanningPrompt]:
    """Load prompt variants from sibling modules, keyed by PROMPT_NAME."""
    prompts: dict[str, PlanningPrompt] = {}
    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        name = getattr(module, "PROMPT_NAME", None)
        top_k = getattr(module, "TOP_K", None)
        if not isinstance(name, str) or not isinstance(top_k, int):
            continue
        description = getattr(module, "DESCRIPTION", "")
        prompts[name] = PlanningPrompt(
            name=name,
            description=str(description),
            top_k=top_k,
        )
    return dict(sorted(prompts.items()))


def get_prompt(name: str) -> PlanningPrompt:
    """Return one variant by its CLI name."""
    prompts = available_prompts()
    try:
        return prompts[name]
    except KeyError as exc:
        known = ", ".join(prompts) or "(none)"
        raise ValueError(
            f"Unknown prompt {name!r}. Available prompts: {known}."
        ) from exc
