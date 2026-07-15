#!/usr/bin/env python3
"""aec-objdump — AEC 反汇编器。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from aecbin_format import read_aecbin

OP = {
    0x0001: "ADD", 0x0002: "SUB", 0x0003: "MUL", 0x0004: "MAD",
    0x0010: "AND", 0x0014: "SHR", 0x0020: "CMP", 0x0021: "CMPP",
    0x0030: "LD", 0x0031: "ST", 0x0032: "LDC",
    0x0040: "BR", 0x0041: "BRX", 0x0044: "RET", 0x0045: "HALT",
    0x0050: "CVTFF", 0x0054: "CPY", 0x0055: "LOADI",
}


def dis(pc: int, i) -> str:
    op = (i.w3 >> 16) & 0xFFFF
    name = OP.get(op, f"OP_{op:04x}")
    rd = (i.w2 >> 16) & 0xFF
    rs1 = i.w2 & 0xFF
    rs2 = i.w1 & 0xFFFF
    imm = i.w0
    pred_en = (i.w3 >> 15) & 1
    pred = i.w3 & 7
    subop = (i.w3 >> 8) & 7
    if op == 0x0055:
        return f"{pc:4d}: LOADI R{rd}, #{imm}"
    if op == 0x0054:
        if rs1 >= 0x100:
            return f"{pc:4d}: CPY R{rd}, SR#{rs1:04x}"
        return f"{pc:4d}: CPY R{rd}, R{rs1}"
    if op == 0x0021:
        return f"{pc:4d}: CMPP P{rd}, R{rs1}, R{rs2}, subop={subop}"
    if op in (0x0030, 0x0031):
        return f"{pc:4d}: {name} R{rd}/[R{rs1}], R{rs2}"
    if op == 0x0041:
        return f"{pc:4d}: @{pred} BRX #{imm}"
    if op == 0x0040:
        return f"{pc:4d}: BR #{imm}"
    if op in (0x0001, 0x0002, 0x0003, 0x0004):
        return f"{pc:4d}: {name} R{rd}, R{rs1}, R{rs2}"
    return f"{pc:4d}: {name} rd={rd} rs1={rs1} rs2={rs2} imm={imm}"


def main() -> int:
    p = argparse.ArgumentParser(prog="aec-objdump")
    p.add_argument("input_bin", type=Path)
    args = p.parse_args()
    insts, _ = read_aecbin(args.input_bin)
    print(f"; {args.input_bin} ({len(insts)} instructions)")
    for pc, inst in enumerate(insts):
        print(dis(pc, inst))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
