# LLM Applications Workspace

A monorepo workspace showcasing state-of-the-art LLM-powered applications, custom Model Context Protocol (MCP) servers, stateful graph orchestrations, and high-aesthetic web client dashboards.

---

## 📂 Workspace Projects

This workspace is divided into several modular components:

| Project | Type | Description | README |
| :--- | :--- | :--- | :--- |
| **`hn_mcp`** | MCP Server | A FastMCP server served over SSE that connects to the Hacker News API to fetch top stories, story details, comment threads, and scrape website main bodies. | 📄 [Hacker News MCP README](file:///Users/subhendu/dev/llm-apps/hn_mcp/README.md) |
| **`hn_agent`** | AI Agent | A stateful agent built using **LangGraph** and FastAPI that connects to the `hn_mcp` server, runs tool loops, and streams execution steps using the **AG-UI** SSE protocol. | 📄 [Summarizer Agent README](file:///Users/subhendu/dev/llm-apps/hn_agent/README.md) |
| **`hn-web-app`** | Web Client | A premium-aesthetic React + TypeScript dashboard client that communicates with the `hn_agent` API utilizing the official `@ag-ui/client` package. | 📄 [React Web App README](file:///Users/subhendu/dev/llm-apps/hn-web-app/README.md) |
| **`tool_use_demo`** | Streamlit UI | A classic hand-rolled ReAct (Reason + Act) loop agent demonstrating custom tools (Calculator, Unit Converter, Word Counter) in a Streamlit chat console. | *Details Below* |

---

## ⚡ Quick Start: Hacker News Ecosystem

To run the full Hacker News AI Summarization ecosystem locally, you will launch three micro-services:

### 1. Run the Hacker News MCP Server
From the project root:
```bash
uv run python -m hn_mcp --host 127.0.0.1 --port 8000
```
*Acts as the backend tools engine at `http://127.0.0.1:8000/sse`.*

### 2. Run the Summarization Agent Server
In a separate terminal, from the project root:
```bash
uv run python -m hn_agent --host 127.0.0.1 --port 8001
```
*Exposes the stateful LangGraph execution stream at `http://127.0.0.1:8001/chat`.*

### 3. Run the React Web Dashboard
In a third terminal, change to the web-app directory:
```bash
cd hn-web-app
npm install
npm run dev -- --host 127.0.0.1
```
*Serves the live interactive dashboard client at **[http://127.0.0.1:5173/](http://127.0.0.1:5173/)**.*

---

## 📐 `tool_use_demo` — Streamlit ReAct Agent

A custom hand-rolled **ReAct (Reason + Act)** agent loop using LangChain + OpenAI, featuring a custom Streamlit chat UI. Watch the model reason step-by-step, invoke tools, and construct the final answer.

### Tools Available

* 🧮 `calculator`: Evaluate math expressions (`sqrt`, `log`, trig, etc.)
* 📐 `unit_converter`: Convert temperature, length, and weight units
* 📝 `word_counter`: Count words, characters, sentences, and paragraphs
* 🔢 `prime_checker`: Check if a number is prime; find the next prime

### Running the Demo

From the project root:
```bash
# Install dependencies
uv sync

# Configure secrets in your .env file (copied from .env.example)
uv run streamlit run tool_use_demo/st_app.py
```
Or execute directly from the terminal CLI:
```bash
uv run python -m tool_use_demo
```