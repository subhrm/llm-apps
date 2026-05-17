# llm-apps

A collection of LLM-powered apps built with LangChain and Streamlit.

---

## `tool_use_demo` — ReAct Agent

A Streamlit chat UI that runs a hand-rolled **ReAct (Reason + Act)** agent loop using LangChain + OpenAI. Watch the model think step-by-step, pick tools, and reason toward a final answer.

### Tools available

| Tool | Description |
|------|-------------|
| 🧮 `calculator` | Evaluate math expressions (`sqrt`, `log`, trig, etc.) |
| 📐 `unit_converter` | Convert temperature, length, and weight units |
| 📝 `word_counter` | Count words, characters, sentences, and paragraphs |
| 🔢 `prime_checker` | Check if a number is prime; find the next prime |

### Project structure

```
llm-apps/
├── tool_use_demo/
│   ├── agent.py      # ReAct loop (pure Python, no Streamlit dependency)
│   ├── tools.py      # LangChain tool definitions
│   ├── config.py     # Loads secrets from .env
│   └── st_app.py     # Streamlit UI
├── .env.example      # Copy to .env and fill in your key
└── pyproject.toml
```

### Setup

#### 1. Install dependencies
```bash
uv sync
```

#### 2. Configure secrets
```
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...
```

#### 3. Run the app
```
uv run streamlit run tool_use_demo/st_app.py
```
or
```
uv run python -m tool_use_demo
```

### Environment variables (`.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | — | Your OpenAI API key |
| `OPENAI_BASE_URL` | ❌ | OpenAI default | Custom OpenAI-compatible endpoint |
| `OPENAI_MODEL` | ❌ | `gpt-4o-mini` | Model to use |
| `OPENAI_TEMPERATURE` | ❌ | `0.0` | Sampling temperature (0.0–1.0) |

> Sidebar fields are pre-filled from `.env` on startup and can be overridden in the UI.
---