#!/usr/bin/env python3
"""Terminal demo: `python cli.py` — reads sample_docs + optional paths."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipeline import analyze_documents


def main() -> int:
    p = argparse.ArgumentParser(description="PMO risk & dependency scan (offline or OpenAI).")
    p.add_argument("files", nargs="*", help="Extra .txt files to include")
    p.add_argument("--model", default="gpt-4o-mini", help="OpenAI model when API key is set")
    args = p.parse_args()

    parts: list[str] = []
    base = Path(__file__).resolve().parent / "sample_docs"
    if base.is_dir():
        for name in sorted(x.name for x in base.glob("*.txt")):
            parts.append(f"### FILE: {name}\n" + (base / name).read_text(encoding="utf-8"))
    for fp in args.files:
        path = Path(fp)
        parts.append(f"### FILE: {path.name}\n" + path.read_text(encoding="utf-8"))

    bundle = "\n\n".join(parts).strip()
    if not bundle:
        print("No input: add sample_docs/*.txt or pass file paths.", file=sys.stderr)
        return 1

    result, mode = analyze_documents(bundle, model=args.model)
    out = {"mode": mode, "result": result.model_dump()}
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
