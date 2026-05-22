# Hacker News MCP Server (SSE)

An async, modular **Model Context Protocol (MCP)** server built in Python that exposes Hacker News data, story interactions, and text scraping utilities to Large Language Models (LLMs) and MCP clients.

The server operates over **Server-Sent Events (SSE)**, enabling bidirectional RPC interaction over HTTP.

---

## Features

The server exposes three specialized tools to any connected client:

1. **`list_top_stories`**
   - **Arguments**: `limit: int` (default: `30`, max: `50`)
   - **Returns**: A structured JSON array of stories containing details like ID, title, score, comment count, author, submission time, source URL, HN link, and self-post flag. Each article is sent as an independent content block.

2. **`get_story_details`**
   - **Arguments**: `story_id: int` (required), `max_comments: int` (default: `5`, max: `20`)
   - **Returns**: A clean, formatted Markdown report detailing the story metadata and top-level comments. Comment HTML tags are stripped and converted to clean markdown (e.g. converting paragraph breaks, blockquotes, and link lists).

3. **`fetch_article_content`**
   - **Arguments**: `url: str` (required)
   - **Returns**: Pure, readable main-body text scraped from the target website. All boilerplate layout code (scripts, styling, headers, sidebars, nav elements, and footer links) is stripped, providing text optimized for LLM reading.

---

## Codebase Architecture

The project is structured modularly:
```
llm-apps/
├── hn_mcp/
│   ├── __init__.py      # FastMCP instance and Starlette application factory
│   ├── __main__.py      # CLI execution wrapper (parses host/port, starts Uvicorn)
│   ├── hn_client.py     # Core Hacker News API client & BS4-based scraper logic
│   └── server.py        # MCP Tool registrations & Starlette/FastAPI SSE mount
├── tests/
│   └── hn_mcp/          # 19 automated unit and integration tests
└── pyproject.toml       # Python package configuration, dependencies, and pytest settings
```

---

## Developer Setup

### 1. Prerequisites
- **Python**: `>=3.13`
- **uv**: Modern, fast Python package manager and resolver. Ensure `uv` is installed on your path.

### 2. Environment Setup
Clone the repository and run `uv sync` from the project root to install the virtual environment and all package dependencies:
```bash
uv sync
```

This installs core dependencies: `mcp`, `fastapi`, `uvicorn`, `beautifulsoup4`, and `httpx`.

---

## Execution Instructions

### Running the Server
Start the Uvicorn ASGI server hosting the SSE application using the module execution syntax:
```bash
uv run python -m hn_mcp --host 127.0.0.1 --port 8000
```

By default, the server binds to `127.0.0.1:8000` and exposes:
- **SSE Stream**: `GET /sse` (clients connect here to listen to server-sent events)
- **Message Receiver**: `POST /messages` (clients POST JSON-RPC requests here)

---

## Testing & Quality Assurance

We maintain a high-coverage test suite consisting of **19 unit and integration tests** verifying HTML cleaning, API parsing, error fallback, clamping, and ASGI integration.

To execute the test suite:
```bash
uv run pytest tests/hn_mcp
```

Test configurations are controlled directly in `pyproject.toml` using `pythonpath = ["."]` to ensure correct module resolution without namespace pollution.

---

## Integration with Clients

### SSE Client Handshake (Bi-directional SSE)
Connecting to this server requires standard MCP SSE connection protocols:
1. Connect via HTTP `GET` to `/sse`. The server responds with `200 OK` and a persistent stream.
2. The server fires a persistent `endpoint` event containing the POST session URL path (e.g. `/messages/?session_id=...`).
3. Complete the standard MCP initialization handshake:
   - Client sends HTTP `POST` containing `initialize` request.
   - Server returns response containing capabilities and info over the persistent `/sse` stream.
   - Client sends `notifications/initialized` notification via `POST` to `/messages`.
4. The connection is now active. Send `tools/list` or `tools/call` JSON-RPC payloads to the message endpoint.
