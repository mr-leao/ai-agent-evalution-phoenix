"""Settings for planning on top of the V1 model connection."""

import os
from dataclasses import dataclass
from pathlib import Path

from action_autonomy.config import REPO_ROOT, Settings

DEFAULT_SOPS_DIR = REPO_ROOT / "data" / "sops"
DEFAULT_TEST_CASES = REPO_ROOT / "data" / "v2_test_cases.csv"
PLAN_TEMPERATURE = 0.0


@dataclass(frozen=True)
class PlanningSettings:
    """V1 connection settings plus the plan and judge models."""

    connection: Settings
    plan_model: str
    judge_model: str
    plan_model_pinned: bool = False
    judge_model_pinned: bool = False

    @classmethod
    def from_env(cls) -> "PlanningSettings":
        connection = Settings.from_env()
        plan_model = os.getenv("LLM_PLAN_MODEL")
        judge_model = os.getenv("LLM_JUDGE_MODEL")
        return cls(
            connection=connection,
            plan_model=plan_model or connection.model,
            judge_model=judge_model or connection.model,
            plan_model_pinned=bool(plan_model),
            judge_model_pinned=bool(judge_model),
        )


def sops_dir() -> Path:
    return DEFAULT_SOPS_DIR
