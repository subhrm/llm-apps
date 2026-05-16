"""
ReAct agent loop — pure Python, no Streamlit dependency.
Can be imported by the Streamlit UI or run directly from the command line.

Usage (CLI):
    python agent.py --question "Is 997 prime?" --api-key sk-...
    python agent.py --question "sqrt(2)*100" --model gpt-4o --temperature 0.2
"""

import argparse
import re
from typing import Any

from langchain_openai import ChatOpenAI

from tool_use_demo.tools import TOOLS

# ──────────────────────────────────────────────────────────────
# Derived registries — built once at import time
# ──────────────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, Any] = {t.name: t for t in TOOLS}
TOOL_NAMES: list[str] = [t.name for t in TOOLS]
TOOL_DESCRIPTIONS: str = "\n".join(f"{t.name}: {t.description}" for t in TOOLS)

# ──────────────────────────────────────────────────────────────
# Prompt template
# ──────────────────────────────────────────────────────────────

REACT_PROMPT_TEMPLATE = """\
You are a helpful AI assistant with access to several tools.
Use the tools when appropriate to give accurate, well-reasoned answers.

Available tools:
{tool_descriptions}

Use the following format EXACTLY:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {question}
Thought:{scratchpad}"""

# ──────────────────────────────────────────────────────────────
# Step type
# ──────────────────────────────────────────────────────────────

Step = dict[str, str]  # keys: kind, label, content


# ──────────────────────────────────────────────────────────────
# Core ReAct loop
# ──────────────────────────────────────────────────────────────

def run_agent_loop(
    question: str,
    api_key: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
    base_url: str = "",
    max_iterations: int = 12,
) -> tuple[str, list[Step]]:
    """
    Run the ReAct loop for *question* and return (final_answer, steps).

    Each step is a dict with keys:
        kind    — one of: thought | action | observation | final | error
        label   — human-readable label with emoji
        content — the text content of the step
    """
    llm_kwargs: dict = {"model": model, "temperature": temperature, "api_key": api_key}
    if base_url.strip():
        llm_kwargs["base_url"] = base_url.strip()
    llm = ChatOpenAI(**llm_kwargs)

    steps: list[Step] = []
    scratchpad = ""

    for _ in range(max_iterations):
        prompt_text = REACT_PROMPT_TEMPLATE.format(
            tool_descriptions=TOOL_DESCRIPTIONS,
            tool_names=", ".join(TOOL_NAMES),
            question=question,
            scratchpad=scratchpad,
        )
        response = llm.invoke(prompt_text)
        llm_text: str = response.content.strip()

        # ── Final Answer? ──────────────────────────────────────
        final_match = re.search(r"Final Answer:\s*(.*)", llm_text, re.DOTALL)
        if final_match:
            answer = final_match.group(1).strip()
            thought_match = re.search(r"^(.+?)(?:Action:|Final Answer:)", llm_text, re.DOTALL)
            if thought_match and (t := thought_match.group(1).strip()):
                steps.append({"kind": "thought", "label": "💭 Thought", "content": t})
            steps.append({"kind": "final", "label": "✅ Final Answer", "content": answer})
            return answer, steps

        # ── Parse Action / Action Input ────────────────────────
        action_match = re.search(r"Action:\s*(\w+)", llm_text)
        input_match  = re.search(r"Action Input:\s*(.*)", llm_text, re.DOTALL)

        if not action_match or not input_match:
            error_msg = f"Could not parse LLM output:\n{llm_text}"
            steps.append({"kind": "error", "label": "❌ Parse Error", "content": error_msg})
            return error_msg, steps

        tool_name  = action_match.group(1).strip()
        tool_input = input_match.group(1).strip()

        thought_match = re.search(r"^(.+?)(?=Action:)", llm_text, re.DOTALL)
        if thought_match and (t := thought_match.group(1).strip()):
            steps.append({"kind": "thought", "label": "💭 Thought", "content": t})

        steps.append({
            "kind": "action",
            "label": f"🔧 Tool Call → {tool_name}",
            "content": f"Input: {tool_input}",
        })

        # ── Dispatch tool ──────────────────────────────────────
        tool_fn = TOOL_REGISTRY.get(tool_name)
        if tool_fn is None:
            observation = f"Unknown tool '{tool_name}'. Available: {', '.join(TOOL_NAMES)}"
            steps.append({"kind": "error", "label": "❌ Tool Error", "content": observation})
        else:
            try:
                observation = str(tool_fn.invoke(tool_input))
            except Exception as exc:
                observation = f"Tool error: {exc}"
                steps.append({"kind": "error", "label": "❌ Tool Error", "content": observation})

        if tool_fn is not None:
            steps.append({"kind": "observation", "label": "🔍 Observation", "content": observation})

        scratchpad += f" {llm_text}\nObservation: {observation}\nThought:"

    timeout_msg = f"Agent stopped after {max_iterations} iterations without a final answer."
    steps.append({"kind": "error", "label": "⏱️ Timeout", "content": timeout_msg})
    return timeout_msg, steps


# ──────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────

def _print_steps(steps: list[Step]) -> None:
    """Pretty-print ReAct steps to stdout."""
    sep = "─" * 60
    for step in steps:
        print(f"\n{sep}")
        print(f"  {step['label']}")
        print(sep)
        print(step["content"])
    print()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the LangChain ReAct agent from the command line.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--question",    required=True,           help="Question to ask the agent")
    parser.add_argument("--api-key",     default="",              help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--base-url",    default="",              help="Custom OpenAI-compatible endpoint URL")
    parser.add_argument("--model",       default="gpt-4o-mini",   help="Model name")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    parser.add_argument("--max-iter",    type=int,   default=12,  help="Maximum ReAct iterations")
    parser.add_argument("--no-steps",    action="store_true",     help="Only print the final answer")
    return parser


if __name__ == "__main__":
    import os

    args = _build_parser().parse_args()

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise SystemExit("❌ Provide --api-key or set the OPENAI_API_KEY environment variable.")

    print(f"\n🤖 Question: {args.question}\n")

    answer, steps = run_agent_loop(
        question=args.question,
        api_key=api_key,
        model=args.model,
        temperature=args.temperature,
        base_url=args.base_url,
        max_iterations=args.max_iter,
    )

    if not args.no_steps:
        _print_steps(steps)

    print(f"✅ Answer: {answer}\n")
