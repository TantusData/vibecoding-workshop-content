"""opscopilot/config.py — environment-driven settings for the whole app.

Purpose:      One place that reads the env (or `.env`) so no module calls os.environ ad hoc.
              Exports `.env` into os.environ on import (no override) so a key set in `.env`
              reaches every entry point (CLI, uvicorn, scripts); the machine's own environment
              always wins. Seeds
              `random`/`numpy` from RANDOM_SEED on import for reproducibility.
Entry points: settings (module-level Settings instance), seed_everything()
Depends on:   pydantic-settings, python-dotenv
Used by:      opscopilot.llm.client, opscopilot.cli, opscopilot.rag.*, opscopilot.webapp.app
Invariants:   LITELLM_VIRTUAL_KEY is the only secret; it is read from the environment and must
              never be logged or written to disk.
"""

from __future__ import annotations

import random
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent

# Export `.env` into the process environment (never overriding what is already set), so a value
# written there is visible to every entry point. On our code-server machines LITELLM_BASE_URL and
# LITELLM_VIRTUAL_KEY are already in the environment and `.env` is not needed at all.
load_dotenv(REPO_ROOT / ".env", override=False)


class Settings(BaseSettings):
    """Runtime configuration. Every field maps 1:1 to an env var of the same (upper-case) name."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: str = Field(default="litellm", description="litellm | fake")
    # the model gateway: OpenAI-compatible, one virtual key per user (spend is metered)
    litellm_base_url: str = "https://ide.tantusdata.com/v1"
    litellm_virtual_key: str = Field(default="", repr=False)
    llm_model: str = "bedrock-claude"  # an alias on the key's allow-list, not a provider id
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.1
    random_seed: int = 42

    # retrieval (plan item 7)
    embeddings_backend: str = Field(default="litellm", description="litellm | fake")
    embeddings_model: str = "titan-embed"  # Titan Text Embeddings V2, 1024 dimensions
    rag_chunk_words: int = 120
    rag_chunk_overlap: int = 30
    rag_title_prefix: bool = True  # prefix every chunk with its page title (the KX-90 fix)
    rag_top_k: int = 4

    # where the fake client's canned responses live (see opscopilot.llm.client.FakeLLMClient)
    fake_llm_responses: str = "tests/fixtures/llm_responses.json"
    record: bool = Field(default=False, description="RECORD=1 -> real replies are captured")


settings = Settings()


def seed_everything(seed: int | None = None) -> int:
    """Seed `random` (and `numpy` if importable) so anything stochastic is reproducible."""
    seed = settings.random_seed if seed is None else seed
    random.seed(seed)
    try:  # numpy is a dependency but keep this import lazy — nothing in the stub needs it
        import numpy as np

        np.random.seed(seed)
    except ImportError:  # pragma: no cover
        pass
    return seed


seed_everything()
