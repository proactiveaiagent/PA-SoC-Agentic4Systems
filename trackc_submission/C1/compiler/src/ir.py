"""编译器中间表示（IR）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IROp(str, Enum):
    PARAM_LOAD = "param_load"
    MOV_SR = "mov_sr"
    MOV = "mov"
    LOADI = "loadi"
    LOADI_F32 = "loadi_f32"
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    MAD = "mad"
    AND = "and"
    SHR = "shr"
    CMPP = "cmpp"
    LD = "ld"
    ST = "st"
    CVT = "cvt"
    BRA = "bra"
    RET = "ret"
    NOP = "nop"


@dataclass
class IRInst:
    op: IROp
    dst: str | None = None
    srcs: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    pred: str | None = None


@dataclass
class BasicBlock:
    name: str | None
    insts: list[IRInst] = field(default_factory=list)


@dataclass
class IRFunction:
    name: str
    params: list[tuple[str, str]]
    blocks: list[BasicBlock] = field(default_factory=list)
    label_map: dict[str, int] = field(default_factory=dict)
