"""Runtime settings for the local OpenAI-compatible model server."""

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEST_CASES = REPO_ROOT / "data" / "v1_test_cases.csv"

# Defaults match a local Ollama server. The OpenAI client calls
# http://localhost:11434/v1/chat/completions. Ollama ignores the API key,
# but the client requires one. Override these with environment variables
# or a .env file in the repository root.
DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_API_KEY = "ollama"
DEFAULT_MODEL = "llama3.1"
DEFAULT_TEMPERATURE = 0.1


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Connection settings for the chat model."""

    base_url: str
    api_key: str
    model: str
    temperature: float = DEFAULT_TEMPERATURE

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv()
        temperature = os.getenv("LLM_TEMPERATURE", str(DEFAULT_TEMPERATURE))
        try:
            temperature_value = float(temperature)
        except ValueError as exc:
            raise SystemExit(
                f"LLM_TEMPERATURE must be a number, got {temperature!r}."
            ) from exc
        return cls(
            base_url=os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL),
            api_key=os.getenv("LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or DEFAULT_API_KEY,
            model=os.getenv("LLM_MODEL", DEFAULT_MODEL),
            temperature=temperature_value,
        )
