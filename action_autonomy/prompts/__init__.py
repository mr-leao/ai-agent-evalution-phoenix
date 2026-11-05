"""Named system prompts.

Each module in this package that defines PROMPT_NAME and SYSTEM_PROMPT
becomes a prompt you can run with --prompt-name.
"""

import importlib
import pkgutil
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Prompt:
    """A named system prompt."""

    name: str
    description: str
    system_prompt: str


@lru_cache(maxsize=1)
def available_prompts() -> dict[str, Prompt]:
    """Load prompts from sibling modules, keyed by PROMPT_NAME."""
    prompts: dict[str, Prompt] = {}
    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        name = getattr(module, "PROMPT_NAME", None)
        system_prompt = getattr(module, "SYSTEM_PROMPT", None)
        if not isinstance(name, str) or not isinstance(system_prompt, str):
            continue
        description = getattr(module, "DESCRIPTION", "")
        prompts[name] = Prompt(
            name=name,
            description=str(description),
            system_prompt=system_prompt,
        )
    return dict(sorted(prompts.items()))


def get_prompt(name: str) -> Prompt:
    """Return one prompt by its CLI name."""
    prompts = available_prompts()
    try:
        return prompts[name]
    except KeyError as exc:
        known = ", ".join(prompts) or "(none)"
        raise ValueError(
            f"Unknown prompt {name!r}. Available prompts: {known}."
        ) from exc
