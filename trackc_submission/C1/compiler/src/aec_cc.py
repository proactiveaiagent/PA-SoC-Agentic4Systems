#!/usr/bin/env python3
"""aec-cc — AEC IR 编译器（PTX -> .aecbin）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aecbin_format import write_aecbin
from codegen import codegen
from passes import run_passes
from ptx_lower import lower_ptx
from ptx_parser import parse_ptx


def compile_ptx(input_path: Path, output_path: Path, opt_level: str = "2") -> int:
    kernel = parse_ptx(input_path.read_text(encoding="utf-8", errors="replace"))
    ir_fn = lower_ptx(kernel)
    ir_fn, regmap = run_passes(ir_fn, opt_level)
    instructions = codegen(ir_fn, regmap)
    write_aecbin(output_path, instructions)
    print(f"aec-cc: {input_path.name} -> {output_path} "
          f"({len(instructions)} inst, {len(regmap)} vregs, -O{opt_level})", file=sys.stderr)
    return len(instructions)


def main() -> int:
    p = argparse.ArgumentParser(prog="aec-cc")
    p.add_argument("input_ptx", type=Path)
    p.add_argument("-o", "--output", required=True, type=Path)
    p.add_argument("-O", dest="opt_level", default="2", choices=("0", "2", "3"))
    args = p.parse_args()
    if not args.input_ptx.exists():
        print(f"aec-cc: error: {args.input_ptx}", file=sys.stderr)
        return 1
    try:
        compile_ptx(args.input_ptx, args.output, args.opt_level)
    except Exception as exc:
        print(f"aec-cc: error: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
