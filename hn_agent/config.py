"""
Configuration module for the Hacker News Agent.
Loads environment variables from `.env` file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Find the project root directory containing the .env file
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# LLM Configurations
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "not_required")
OPENAI_BASE_URL: str = os.environ.get("OPENAI_BASE_URL", "").strip()
OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_TEMPERATURE: float = float(os.environ.get("OPENAI_TEMPERATURE", "0.0"))

# MCP Server URL
HN_MCP_URL: str = os.environ.get("HN_MCP_URL", "http://127.0.0.1:8000/sse").strip()
