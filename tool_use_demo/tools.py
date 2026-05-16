"""
Tool definitions for the LangChain ReAct Agent demo.
Each tool is decorated with @tool so LangChain can describe and invoke it.
"""

import math
import re
from typing import Any

from langchain_classic.tools import tool


# ──────────────────────────────────────────────────────────────
# Individual tools
# ──────────────────────────────────────────────────────────────

@tool
def calculator(expression: str) -> str:
    """
    Evaluates a mathematical expression. Supports +, -, *, /, **, sqrt(), abs(),
    sin(), cos(), tan(), log(), log10(), ceil(), floor(), pi, e.
    Input: a valid math expression as a string, e.g. 'sqrt(144) + 2**8'.
    """
    safe_env = {
        "sqrt": math.sqrt, "abs": abs,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "log": math.log, "log10": math.log10,
        "ceil": math.ceil, "floor": math.floor,
        "pi": math.pi, "e": math.e,
        "__builtins__": {},
    }
    try:
        result = eval(expression.strip(), safe_env)  # noqa: S307
        return f"{result}"
    except Exception as exc:
        return f"Error evaluating expression: {exc}"


@tool
def unit_converter(query: str) -> str:
    """
    Converts between common units. Supported conversions:
    - Temperature: Celsius ↔ Fahrenheit ↔ Kelvin
    - Length: km ↔ miles, meters ↔ feet
    - Weight: kg ↔ pounds
    Input format: '<value> <from_unit> to <to_unit>', e.g. '100 celsius to fahrenheit'.
    """
    query = query.lower().strip()
    pattern = r"([\d.]+)\s*(\w+)\s+to\s+(\w+)"
    m = re.match(pattern, query)
    if not m:
        return "Could not parse query. Use format: '<value> <from_unit> to <to_unit>'"
    value, from_unit, to_unit = float(m.group(1)), m.group(2), m.group(3)

    conversions: dict[tuple[str, str], Any] = {
        ("celsius", "fahrenheit"): lambda v: v * 9 / 5 + 32,
        ("fahrenheit", "celsius"): lambda v: (v - 32) * 5 / 9,
        ("celsius", "kelvin"):     lambda v: v + 273.15,
        ("kelvin", "celsius"):     lambda v: v - 273.15,
        ("fahrenheit", "kelvin"):  lambda v: (v - 32) * 5 / 9 + 273.15,
        ("kelvin", "fahrenheit"):  lambda v: (v - 273.15) * 9 / 5 + 32,
        ("km", "miles"):           lambda v: v * 0.621371,
        ("miles", "km"):           lambda v: v * 1.60934,
        ("meters", "feet"):        lambda v: v * 3.28084,
        ("feet", "meters"):        lambda v: v / 3.28084,
        ("kg", "pounds"):          lambda v: v * 2.20462,
        ("pounds", "kg"):          lambda v: v / 2.20462,
    }

    conv_fn = conversions.get((from_unit, to_unit))
    if conv_fn is None:
        return f"Conversion from '{from_unit}' to '{to_unit}' is not supported."
    result = conv_fn(value)
    return f"{value} {from_unit} = {result:.4f} {to_unit}"


@tool
def word_counter(text: str) -> str:
    """
    Counts words, characters, sentences, and paragraphs in the given text.
    Returns a formatted summary.
    """
    words = len(text.split())
    chars = len(text)
    chars_no_spaces = len(text.replace(" ", "").replace("\n", ""))
    sentences = len(re.split(r"[.!?]+", text.strip())) - 1 or 1
    paragraphs = len([p for p in text.split("\n\n") if p.strip()])
    return (
        f"Words: {words} | Characters: {chars} | "
        f"Characters (no spaces): {chars_no_spaces} | "
        f"Sentences: ~{sentences} | Paragraphs: {paragraphs}"
    )


@tool
def prime_checker(n: str) -> str:
    """
    Checks whether a given integer is prime and returns the next prime if it is not.
    Input: a positive integer as a string.
    """
    try:
        num = int(n.strip())
    except ValueError:
        return "Input must be a valid integer."
    if num < 2:
        return f"{num} is not a prime number. The smallest prime is 2."

    def _is_prime(x: int) -> bool:
        if x < 2:
            return False
        if x == 2:
            return True
        if x % 2 == 0:
            return False
        for i in range(3, int(x**0.5) + 1, 2):
            if x % i == 0:
                return False
        return True

    if _is_prime(num):
        return f"{num} is a prime number! ✓"
    nxt = num + 1
    while not _is_prime(nxt):
        nxt += 1
    return f"{num} is NOT prime. The next prime after {num} is {nxt}."


# ──────────────────────────────────────────────────────────────
# Public registry — import this in other modules
# ──────────────────────────────────────────────────────────────

TOOLS = [calculator, unit_converter, word_counter, prime_checker]

TOOL_INFO: dict[str, str] = {
    "🧮 calculator":     "Evaluate math expressions",
    "📐 unit_converter": "Convert between units",
    "📝 word_counter":   "Analyse text statistics",
    "🔢 prime_checker":  "Check / find prime numbers",
}

EXAMPLE_QUERIES: list[str] = [
    "What is sqrt(2) * 100 + 2^10?",
    "Convert 37 celsius to fahrenheit, then to kelvin.",
    "Is 997 a prime number?",
    "Count words in: 'The quick brown fox jumps over the lazy dog'",
    "How many miles is a 42.195 km marathon? Then compute 42.195 * 1000.",
]
