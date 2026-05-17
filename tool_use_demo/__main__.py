"""
Entry point for `python -m tool_use_demo`.

Launches the Streamlit UI defined in st_app.py.
"""

import sys
from pathlib import Path
import streamlit.web.cli as stcli


def main() -> None:
    app = Path(__file__).parent / "st_app.py"
    sys.argv = ["streamlit", "run", str(app), "--server.headless", "true"]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
