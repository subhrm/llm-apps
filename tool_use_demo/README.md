# tool_use_demo — Streamlit ReAct Agent

A classic hand-rolled **ReAct (Reason + Act)** loop implemented as a Streamlit chat app. This demo shows a custom agent invoking tools such as calculators, unit converters, and word counters while reasoning through a natural language prompt.

## Tools Included

* 🧮 `calculator` — evaluate math expressions with `sqrt`, `log`, trigonometry, and basic arithmetic.
* 📐 `unit_converter` — convert temperature, length, and weight units.
* 📝 `word_counter` — count words, characters, sentences, and paragraphs.
* 🔢 `prime_checker` — check if a number is prime and find the next prime.

## Run the Demo

From the repository root:

```bash
uv sync
uv run streamlit run tool_use_demo/st_app.py
```

Alternatively, run the package entry point directly:

```bash
uv run python -m tool_use_demo
```

## Configuration

Create a `.env` file in the repo root with any required secrets, based on the `.env.example` pattern. The Streamlit app and tool logic will read those values at runtime.
