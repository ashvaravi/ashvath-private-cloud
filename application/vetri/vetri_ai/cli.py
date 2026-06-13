from __future__ import annotations

import argparse
import sys

from vetri_ai.main import run_once
from vetri_ai.utils.json_utils import to_pretty_json


def configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main() -> None:
    configure_stdout()
    parser = argparse.ArgumentParser(prog="vetri")
    sub = parser.add_subparsers(dest="command")
    ask = sub.add_parser("ask")
    ask.add_argument("text", nargs="+")
    ask.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command != "ask":
        parser.print_help()
        return

    result = run_once(" ".join(args.text))
    if args.json:
        print(to_pretty_json(result))
    else:
        print(result["answer"])


if __name__ == "__main__":
    main()
