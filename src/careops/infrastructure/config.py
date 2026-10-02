from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT_DIR / "data"

# Provider name (as used by LangChain) -> the environment variable holding its API key.
# Add a line here (and the matching langchain-* package) to support another provider.
PROVIDER_KEYS: dict[str, str] = {
    "google_genai": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}

_PLACEHOLDERS = {"", "replace_me", "your_key_here"}


@dataclass(frozen=True)
class RuntimeConfig:
    provider: str
    model: str
    api_key: str | None

    @property
    def key_env_var(self) -> str | None:
        return PROVIDER_KEYS.get(self.provider)


def runtime_config() -> RuntimeConfig:
    load_dotenv(ROOT_DIR / ".env")
    provider = os.getenv("LLM_PROVIDER", "google_genai").strip().lower()
    key_var = PROVIDER_KEYS.get(provider)
    raw_key = (os.getenv(key_var) or "").strip() if key_var else ""
    return RuntimeConfig(
        provider=provider,
        model=os.getenv("LLM_MODEL", "gemini-2.5-flash").strip(),
        api_key=None if raw_key.lower() in _PLACEHOLDERS else raw_key,
    )
