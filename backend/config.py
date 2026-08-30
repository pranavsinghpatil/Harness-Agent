"""Configuration and environment management for TrueForge Agent Harness."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def load_env_file(dotenv_path: Optional[str | Path] = None) -> dict[str, str]:
    """Parse and load key-value pairs from a .env file into os.environ.
    
    Preserves existing environment variables unless overridden.
    Supports comments (#), quotes, and whitespace trimming.
    """
    if dotenv_path is None:
        # Search current working directory and parent directories for .env
        candidates = [
            Path.cwd() / ".env",
            Path(__file__).resolve().parent.parent / ".env",
            Path.cwd() / "backend" / ".env",
        ]
        for candidate in candidates:
            if candidate.is_file():
                dotenv_path = candidate
                break

    loaded: dict[str, str] = {}
    if dotenv_path is None or not Path(dotenv_path).is_file():
        return loaded

    try:
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip()
                    # Strip surrounding quotes if present
                    if (val.startswith('"') and val.endswith('"')) or (
                        val.startswith("'") and val.endswith("'")
                    ):
                        val = val[1:-1]
                    if key and key not in os.environ:
                        os.environ[key] = val
                    loaded[key] = val
    except Exception:
        pass

    return loaded


# Load environment variables on module import
load_env_file()


@dataclass
class HarnessSettings:
    """Central configuration settings for Harness server and integrations."""

    # Server settings
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("NODE_ENV", "development"))

    # Security & Auth
    harness_approval_token: str = field(
        default_factory=lambda: os.getenv("HARNESS_APPROVAL_TOKEN", "change-me-for-local-approval")
    )
    harness_reviewer_id: str = field(
        default_factory=lambda: os.getenv("HARNESS_REVIEWER_ID", "local-reviewer")
    )

    # Groq & LLM Settings
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", "").strip())
    groq_model: str = field(
        default_factory=lambda: os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
    )
    groq_base_url: str = field(
        default_factory=lambda: os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    )

    @property
    def has_groq(self) -> bool:
        """Return True if Groq API key is present."""
        return bool(self.groq_api_key and not self.groq_api_key.startswith("your_"))


def get_settings() -> HarnessSettings:
    """Retrieve freshly evaluated application settings."""
    return HarnessSettings()


settings = get_settings()
