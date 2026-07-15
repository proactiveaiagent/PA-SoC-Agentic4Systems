"""AEC 128-bit 指令编码。"""

from __future__ import annotations

import struct
from dataclasses import dataclass

OP_ADD = 0x0001
OP_SUB = 0x0002
OP_MUL = 0x0003
OP_MAD = 0x0004
OP_FMA = 0x0005
OP_CMP = 0x0020
OP_CMPP = 0x0021
OP_AND = 0x0010
OP_SHR = 0x0014
OP_LD = 0x0030
OP_ST = 0x0031
OP_LDC = 0x0032
OP_BR = 0x0040
OP_BRX = 0x0041
OP_RET = 0x0044
OP_HALT = 0x0045
OP_CVTFF = 0x0050
OP_CPY = 0x0054
OP_LOADI = 0x0055

T_B32 = 0x0
T_U32 = 0x2
T_F32 = 0x8
T_F16 = 0xA
T_NONE = 0xF

SR_TID_X = 0x0100
SR_NTID_X = 0x0101
SR_CTAID_X = 0x0102
SR_TID_Y = 0x0110
SR_CTAID_Y = 0x0112

CMP_EQ, CMP_NE, CMP_LT, CMP_LE, CMP_GT, CMP_GE = 0, 1, 2, 3, 4, 5


@dataclass
class AecInst:
    w0: int = 0
    w1: int = 0
    w2: int = 0
    w3: int = 0

    def to_bytes(self) -> bytes:
        return struct.pack("<IIII", self.w0 & 0xFFFFFFFF, self.w1 & 0xFFFFFFFF,
                           self.w2 & 0xFFFFFFFF, self.w3 & 0xFFFFFFFF)

    def to_hex_line(self) -> str:
        return "".join(f"{w:08x}" for w in (self.w3, self.w2, self.w1, self.w0))


def _ctrl(type_code: int = T_NONE, pred: int = 0, pred_en: int = 0,
          pred_neg: int = 0, subop: int = 0, space: int = 0) -> int:
    return ((pred_en & 1) << 15) | ((pred_neg & 1) << 14) | ((space & 7) << 11) | \
           ((subop & 7) << 8) | ((type_code & 0xF) << 3) | (pred & 7)


def _w3(op: int, ctrl: int) -> int:
    return ((op & 0xFFFF) << 16) | (ctrl & 0xFFFF)


def _rrr(op: int, ty: int, rd: int, rs1: int, rs2: int, subop: int = 0) -> AecInst:
    return AecInst(w1=rs2 & 0xFFFF, w2=((rd & 0xFF) << 16) | (rs1 & 0xFF),
                   w3=_w3(op, _ctrl(ty, subop=subop)))


def loadi(rd: int, imm: int) -> AecInst:
    return AecInst(w0=imm & 0xFFFFFFFF, w2=(rd & 0xFF) << 16, w3=_w3(OP_LOADI, _ctrl(T_NONE)))


def cpy_reg(rd: int, rs: int, ty: int = T_U32) -> AecInst:
    return AecInst(w2=((rd & 0xFF) << 16) | (rs & 0xFF), w3=_w3(OP_CPY, _ctrl(ty)))


def cpy_special(rd: int, sel: int) -> AecInst:
    return AecInst(w2=((rd & 0xFF) << 16) | (sel & 0xFFFF), w3=_w3(OP_CPY, _ctrl(T_U32)))


def add_u32(rd, rs1, rs2): return _rrr(OP_ADD, T_U32, rd, rs1, rs2)
def sub_u32(rd, rs1, rs2): return _rrr(OP_SUB, T_U32, rd, rs1, rs2)
def mul_u32(rd, rs1, rs2): return _rrr(OP_MUL, T_U32, rd, rs1, rs2)
def and_b32(rd, rs1, rs2): return _rrr(OP_AND, T_B32, rd, rs1, rs2)
def shr_u32(rd, rs1, rs2): return _rrr(OP_SHR, T_U32, rd, rs1, rs2)
def add_f32(rd, rs1, rs2): return _rrr(OP_ADD, T_F32, rd, rs1, rs2)
def sub_f32(rd, rs1, rs2): return _rrr(OP_SUB, T_F32, rd, rs1, rs2)
def mul_f32(rd, rs1, rs2): return _rrr(OP_MUL, T_F32, rd, rs1, rs2)


def mad_u32(rd, rs1, rs2, rs3):
    return AecInst(w0=rs3 & 0xFF, w1=rs2 & 0xFFFF, w2=((rd & 0xFF) << 16) | (rs1 & 0xFF),
                   w3=_w3(OP_MAD, _ctrl(T_U32)))


def mad_f32(rd, rs1, rs2, rs3):
    return AecInst(w0=rs3 & 0xFF, w1=rs2 & 0xFFFF, w2=((rd & 0xFF) << 16) | (rs1 & 0xFF),
                   w3=_w3(OP_MAD, _ctrl(T_F32)))


def cmpp_u32(pd: int, rs1: int, rs2: int, cmp_subop: int) -> AecInst:
    return AecInst(w1=rs2 & 0xFFFF, w2=((pd & 7) << 16) | (rs1 & 0xFF),
                   w3=_w3(OP_CMPP, _ctrl(T_U32, subop=cmp_subop)))


def cmp_u32(rd: int, rs1: int, rs2: int, cmp_subop: int) -> AecInst:
    return _rrr(OP_CMP, T_U32, rd, rs1, rs2, cmp_subop)


def ldc(rd: int, addr: int, ty: int = T_U32) -> AecInst:
    return AecInst(w2=((rd & 0xFF) << 16) | (addr & 0xFF), w3=_w3(OP_LDC, _ctrl(ty, space=2)))


def ld_gmem(rd: int, addr: int, ty: int = T_F32) -> AecInst:
    return AecInst(w2=((rd & 0xFF) << 16) | (addr & 0xFF), w3=_w3(OP_LD, _ctrl(ty, space=0)))


def st_gmem(addr: int, val: int, ty: int = T_F32) -> AecInst:
    return AecInst(w1=val & 0xFFFF, w2=addr & 0xFF, w3=_w3(OP_ST, _ctrl(ty, space=0)))


def cvt_f32_f16(rd: int, rs: int) -> AecInst:
    return AecInst(w2=((rd & 0xFF) << 16) | (rs & 0xFF), w3=_w3(OP_CVTFF, _ctrl(T_F16, subop=1)))


def brx(pred: int, pc: int, neg: int = 0) -> AecInst:
    return AecInst(w0=pc & 0xFFFFFFFF, w3=_w3(OP_BRX, _ctrl(T_NONE, pred=pred, pred_en=1, pred_neg=neg)))


def br(pc: int) -> AecInst:
    return AecInst(w0=pc & 0xFFFFFFFF, w3=_w3(OP_BR, _ctrl(T_NONE)))


def ret() -> AecInst:
    return AecInst(w3=_w3(OP_RET, _ctrl(T_NONE)))


def halt() -> AecInst:
    return AecInst(w3=_w3(OP_HALT, _ctrl(T_NONE)))
