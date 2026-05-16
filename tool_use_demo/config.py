"""
tool_use_demo.config
~~~~~~~~~~~~~~~~~~~~
Loads environment variables from a .env file (project root) and exposes
them as typed, validated settings.

Priority (highest → lowest):
    1. Real environment variables already set in the shell
    2. Variables in the .env file
    3. Hardcoded defaults below
"""

import os
from pathlib import Path

# ── Load .env from the project root (two levels up from this file) ──────────
_PROJECT_ROOT = Path(__file__).parent.parent

try:
    from dotenv import load_dotenv

    _env_path = _PROJECT_ROOT / ".env"
    load_dotenv(dotenv_path=_env_path, override=False)  # don't override real env vars
except ImportError:
    pass  # python-dotenv not installed; rely on real env vars


# ── Typed accessors ───────────────────────────────────────────────────────────

def get_openai_api_key() -> str:
    """Return the OpenAI API key, or an empty string if not set."""
    return os.environ.get("OPENAI_API_KEY", "")


def get_openai_base_url() -> str:
    """Return the custom endpoint URL, or an empty string for the default."""
    return os.environ.get("OPENAI_BASE_URL", "")


def get_openai_model() -> str:
    """Return the default model name."""
    return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def get_openai_temperature() -> float:
    """Return the default sampling temperature."""
    raw = os.environ.get("OPENAI_TEMPERATURE", "0.0")
    try:
        return float(raw)
    except ValueError:
        return 0.0
