"""PTX 风格 IR 解析器。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class PtxInstr:
    pred: str | None
    mnemonic: str
    args: list[str]
    label: str | None = None


@dataclass
class PtxKernel:
    name: str
    params: list[tuple[str, str]] = field(default_factory=list)
    body: list[PtxInstr] = field(default_factory=list)


REG_RE = re.compile(r"^%(?P<bank>[a-z0-9]+)(?P<num>\d+)$")
FLOAT_IMM = re.compile(r"^0f([0-9a-fA-F]+)$")


def parse_reg(tok: str) -> tuple[str, int]:
    tok = tok.strip()
    m = REG_RE.match(tok)
    if not m:
        raise ValueError(f"invalid register: {tok}")
    return m.group("bank"), int(m.group("num"))


def vreg(bank: str, num: int) -> str:
    return f"v:{bank}:{num}"


def parse_float_imm(tok: str) -> float:
    m = FLOAT_IMM.match(tok.strip())
    if m:
        import struct
        bits = int(m.group(1), 16)
        return struct.unpack(">f", bits.to_bytes(4, "big"))[0]
    return float(tok)


def parse_ptx(text: str) -> PtxKernel:
    kernel = PtxKernel(name="kernel")
    in_body = False

    for raw in text.splitlines():
        line = raw.split("//")[0].split("#")[0].strip()
        if not line:
            continue
        if ".entry" in line:
            m = re.search(r"\.entry\s+(\w+)", line)
            if m:
                kernel.name = m.group(1)
            continue
        if line.startswith(".param"):
            parts = line.replace(",", " ").split()
            ptype = parts[1]
            pname = parts[2]
            kernel.params.append((ptype, pname))
            continue
        if line.startswith(".reg") or line.startswith(".version") or line.startswith(".target"):
            continue
        if line == "{":
            in_body = True
            continue
        if line == "}":
            break
        if not in_body:
            continue

        if line.endswith(":"):
            kernel.body.append(PtxInstr(None, "", [], line[:-1].strip()))
            continue

        pred = None
        if line.startswith("@"):
            pred, _, line = line.partition(" ")

        parts = line.replace(",", " ").replace(";", " ").split()
        if not parts:
            continue
        kernel.body.append(PtxInstr(pred, parts[0], parts[1:]))

    return kernel
