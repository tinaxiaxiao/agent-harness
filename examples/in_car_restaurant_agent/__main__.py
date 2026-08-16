from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import DEFAULT_UTTERANCE, run_scenario


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the sandbox vehicle restaurant agent")
    parser.add_argument("--scenario", default="happy_path")
    parser.add_argument("--input", default=DEFAULT_UTTERANCE)
    parser.add_argument("--trace", type=Path)
    args = parser.parse_args()
    result, trace = run_scenario(args.scenario, transcript=args.input)
    if args.trace:
        trace.save(args.trace)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
