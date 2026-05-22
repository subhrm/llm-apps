# Hacker News Summarization Agent

A stateful, production-ready AI Agent powered by **LangGraph**, **FastAPI**, and the **AG-UI Protocol**. This agent acts as a stateful orchestrator that connects to a Hacker News SSE MCP server, invokes tools to browse front-page stories, extracts comments, scrapes external linked articles, and streams real-time execution steps back to clients.

---

## 🛠️ Tech Stack & Protocols

* **Orchestration**: `LangGraph` StateGraph defining a stateful ReAct (Reasoning and Acting) loop.
* **Server Framework**: `FastAPI` + `Uvicorn`.
* **Interaction Protocol**: Complies with the **AG-UI (Agent-User Interaction) protocol**, transforming standard LangChain event streams into strongly-typed Server-Sent Events (SSE).
* **Environment & Package Management**: Managed via `uv`.

---

## 📂 Codebase Layout

```
hn_agent/
├── __init__.py      # Package initialization & exports
├── __main__.py      # CLI entrypoint script for running the module
├── agent.py         # LangGraph workflow, system prompt, and StateGraph definition
├── config.py        # Environment variables loader & validator
├── server.py        # FastAPI server, AG-UI protocol streaming, and message converters
└── tools.py         # LangChain tools wrapping MCP client sessions via ContextVar
```

### 1. `config.py`
Dynamically loads env parameters (with strict fallback defaults). Configures local OpenAI-compatible endpoints (like LM Studio or Ollama) and specifies the target Hacker News MCP server SSE URL.

### 2. `tools.py`
Defines 3 specialized agent tools:
* `list_top_stories(limit)`: Retrieves top stories from the homepage and formats them as a clean JSON array.
* `get_story_details(story_id, max_comments)`: Retrieves detailed story metadata and markdown-formatted top discussion threads.
* `fetch_article_content(url)`: Scrapes external linked pages, extracts readable body text, and removes HTML boilerplate.

It utilizes Python's `ContextVar` to share the active MCP `ClientSession` safely across async execution threads.

### 3. `agent.py`
Sets up the stateful LangGraph agent loop. The LLM decides when to call tools and wraps up once it has gathered sufficient context to formulate the final summary.

### 4. `server.py`
The FastAPI application core. It translates `astream_events` (v2) chunks into standard AG-UI events like `TextMessageStartEvent`, `TextMessageContentEvent`, `ToolCallStartEvent`, and `ToolCallResultEvent`. Exposes `GET /capabilities` to publish supported metadata.

---

## ⚙️ Prerequisites & Environment

Make sure you have your environment variables set up in your root `.env` file (copied from `.env.example`). 

Key variables used by the agent:
```ini
# OpenAI-compatible API configurations (LM Studio, Ollama, OpenAI, etc.)
OPENAI_API_KEY="lm-studio"
OPENAI_API_BASE="http://localhost:1234/v1"
OPENAI_MODEL_NAME="qwen2.5-7b-instruct"

# Target Hacker News MCP server connection URL
HN_MCP_URL="http://127.0.0.1:8000/sse"
```

---

## 🚀 Running the Agent

You can start the agent directly using Python's module syntax:

```bash
# Using uv (recommended)
uv run python -m hn_agent --host 127.0.0.1 --port 8001

# Or standard Python
python -m hn_agent --host 127.0.0.1 --port 8001
```

Once started, the agent will expose the following endpoints:
* **Capabilities Endpoint**: `GET http://127.0.0.1:8001/capabilities`
* **SSE Chat Connection**: `POST http://127.0.0.1:8001/chat`

---

## 🧪 Running Automated Tests

A comprehensive suite of unit and integration tests is located in `tests/hn_agent/`. You can execute it with:

```bash
uv run pytest tests/hn_agent
```
