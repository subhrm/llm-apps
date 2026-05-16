"""
LangChain ReAct Agent Demo — Streamlit UI
Thin UI layer; all agent logic lives in agent.py, tools in tools.py.

Run with:
    streamlit run demo_app/agent_demo.py
"""

import streamlit as st

from tool_use_demo.agent import run_agent_loop
from tool_use_demo.config import (
    get_openai_api_key,
    get_openai_base_url,
    get_openai_model,
    get_openai_temperature,
)
from tool_use_demo.tools import EXAMPLE_QUERIES, TOOL_INFO

# ──────────────────────────────────────────────────────────────
# Defaults from .env / environment
# ──────────────────────────────────────────────────────────────

_DEFAULT_API_KEY     = get_openai_api_key()
_DEFAULT_BASE_URL    = get_openai_base_url()
_DEFAULT_MODEL       = get_openai_model()
_DEFAULT_TEMPERATURE = get_openai_temperature()

# ──────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="LangChain ReAct Agent Demo",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────
# Session state
# ──────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    # Each entry: {role, content, steps (optional list[Step])}
    st.session_state.messages = []

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def render_steps_expander(steps: list[dict]) -> None:
    """Render ReAct steps as a collapsible expander inside a chat message."""
    with st.expander("🧠 Agent reasoning", expanded=False):
        for step in steps:
            st.markdown(f"**{step['label']}**")
            st.code(step["content"], language=None)


# ──────────────────────────────────────────────────────────────
# Sidebar — configuration
# ──────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    st.divider()

    api_key = st.text_input(
        "OpenAI API Key",
        value=_DEFAULT_API_KEY,
        type="password",
        placeholder="sk-…",
        help="Your OpenAI API key. Pre-filled from OPENAI_API_KEY in .env if set.",
    )
    base_url = st.text_input(
        "Endpoint URL",
        value=_DEFAULT_BASE_URL,
        placeholder="https://api.openai.com/v1",
        help="Custom OpenAI-compatible endpoint. Pre-filled from OPENAI_BASE_URL in .env if set.",
    )
    model = st.text_input(
        "Model",
        value=_DEFAULT_MODEL,
        placeholder="gpt-4o-mini",
        help="Pre-filled from OPENAI_MODEL in .env if set.",
    )
    temperature = st.slider("Temperature", 0.0, 1.0, _DEFAULT_TEMPERATURE, 0.1)

    if st.button("🔌 Check Connection", use_container_width=True):
        if not api_key:
            st.error("Enter an API key first.", icon="🔑")
        else:
            with st.spinner("Connecting…"):
                try:
                    from openai import OpenAI
                    client_kwargs: dict = {"api_key": api_key}
                    if base_url.strip():
                        client_kwargs["base_url"] = base_url.strip()
                    _client = OpenAI(**client_kwargs)
                    _models = [m.id for m in _client.models.list().data[:5]]
                    st.success(f"✅ Connected! Sample models: {', '.join(_models)}")
                except Exception as exc:
                    st.error(f"❌ Connection failed: {exc}")

    st.divider()
    st.markdown("### 🧰 Available Tools")
    for name, desc in TOOL_INFO.items():
        st.markdown(f"**{name}** — {desc}")

    st.divider()
    st.markdown("### 💡 Try asking…")
    for ex in EXAMPLE_QUERIES:
        if st.button(ex, key=f"ex_{ex[:20]}", use_container_width=True):
            st.session_state["prefill"] = ex

    st.divider()
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ──────────────────────────────────────────────────────────────
# Main — chat interface
# ──────────────────────────────────────────────────────────────

st.title("🤖 LangChain ReAct Agent")
st.caption("Watch the model think, plan, use tools, and reason — step by step.")

# Render persisted chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("steps"):
            render_steps_expander(msg["steps"])

# Handle example prefill
prefill = st.session_state.pop("prefill", "")
user_input = st.chat_input("Ask anything — I'll use tools when needed…")

if prefill and not user_input:
    st.info(f"💡 Example selected — paste it above:\n\n**{prefill}**")

# ── Run agent on new input ───────────────────────────────────
if user_input:
    if not api_key:
        st.error("⚠️ Please enter your OpenAI API key in the sidebar.", icon="🔑")
    else:
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("_Thinking…_")

            try:
                answer, run_steps = run_agent_loop(
                    question=user_input,
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
                    base_url=base_url,
                )
            except Exception as exc:
                answer = f"❌ Error: {exc}"
                run_steps = [{"kind": "error", "label": "❌ Error", "content": str(exc)}]

            placeholder.markdown(answer)
            render_steps_expander(run_steps)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "steps": run_steps,
        })

