"""IR -> AEC 机器码生成。"""

from __future__ import annotations

import struct

from inst_encode import (
    AecInst, SR_CTAID_X, SR_NTID_X, SR_TID_X,
    add_f32, add_u32, and_b32, br, brx, cmpp_u32,
    cpy_reg, cpy_special, cvt_f32_f16, halt, ld_gmem, ldc, loadi,
    mad_f32, mad_u32, mul_f32, mul_u32, ret, shr_u32, st_gmem, sub_f32,
)
from ir import IRFunction, IROp

TMP = 250


def _g(m: dict[str, int], v: str) -> int:
    return m.get(v, 0)


def _pred(m: dict[str, int], v: str | None) -> int:
    if not v:
        return 0
    return m.get(v, 0)


def _f32_bits(f: float) -> int:
    return struct.unpack("<I", struct.pack("<f", float(f)))[0]


def codegen(fn: IRFunction, regmap: dict[str, int]) -> list[AecInst]:
    out: list[AecInst] = []
    fixups: list[tuple[int, str]] = []
    label_pc: dict[str, int] = {}

    def emit(i: AecInst) -> None:
        out.append(i)

    for bb in fn.blocks:
        if bb.name:
            label_pc[bb.name] = len(out)
        for inst in bb.insts:
            pred = _pred(regmap, inst.pred)
            if inst.op == IROp.PARAM_LOAD:
                rd = _g(regmap, inst.dst)
                off = inst.meta["offset"]
                ptype = inst.meta["ptype"]
                emit(loadi(TMP, off))
                ty = 0x8 if ptype == ".f32" else 0x2
                emit(ldc(rd, TMP, ty))
            elif inst.op == IROp.MOV_SR:
                sr_sel = {
                    "tid.x": SR_TID_X, "ctaid.x": SR_CTAID_X, "ntid.x": SR_NTID_X,
                    "ctaid.y": 0x0112, "tid.y": 0x0110,
                }[inst.meta["sr"]]
                emit(cpy_special(_g(regmap, inst.dst), sr_sel))
            elif inst.op == IROp.MOV:
                emit(cpy_reg(_g(regmap, inst.dst), _g(regmap, inst.srcs[0])))
            elif inst.op == IROp.LOADI:
                emit(loadi(_g(regmap, inst.dst), int(inst.meta["imm"])))
            elif inst.op == IROp.LOADI_F32:
                emit(loadi(_g(regmap, inst.dst), _f32_bits(inst.meta["imm"])))
            elif inst.op == IROp.ADD:
                ty = inst.meta.get("ty", "u32")
                rd, s1 = _g(regmap, inst.dst), _g(regmap, inst.srcs[0])
                if "imm" in inst.meta:
                    emit(loadi(TMP, int(inst.meta["imm"])))
                    emit(add_u32(rd, s1, TMP) if ty != "f32" else add_f32(rd, s1, TMP))
                else:
                    s2 = _g(regmap, inst.srcs[1])
                    emit(add_f32(rd, s1, s2) if ty == "f32" else add_u32(rd, s1, s2))
            elif inst.op == IROp.SUB:
                emit(sub_f32(_g(regmap, inst.dst), _g(regmap, inst.srcs[0]), _g(regmap, inst.srcs[1])))
            elif inst.op == IROp.MUL:
                rd = _g(regmap, inst.dst)
                if "imm" in inst.meta:
                    emit(loadi(TMP, int(inst.meta["imm"])))
                    emit(mul_u32(rd, _g(regmap, inst.srcs[0]), TMP))
                elif inst.meta.get("ty") == "f32":
                    emit(mul_f32(rd, _g(regmap, inst.srcs[0]), _g(regmap, inst.srcs[1])))
                else:
                    emit(mul_u32(rd, _g(regmap, inst.srcs[0]), _g(regmap, inst.srcs[1])))
            elif inst.op == IROp.MAD:
                ty = inst.meta.get("ty", "u32")
                rd = _g(regmap, inst.dst)
                a, b, c = _g(regmap, inst.srcs[0]), _g(regmap, inst.srcs[1]), _g(regmap, inst.srcs[2])
                emit(mad_f32(rd, a, b, c) if ty == "f32" else mad_u32(rd, a, b, c))
            elif inst.op == IROp.AND:
                rd, s1 = _g(regmap, inst.dst), _g(regmap, inst.srcs[0])
                if "imm" in inst.meta:
                    emit(loadi(TMP, int(inst.meta["imm"])))
                    emit(and_b32(rd, s1, TMP))
                else:
                    emit(and_b32(rd, s1, _g(regmap, inst.srcs[1])))
            elif inst.op == IROp.SHR:
                rd, s1 = _g(regmap, inst.dst), _g(regmap, inst.srcs[0])
                if inst.meta.get("imm") is not None:
                    emit(loadi(TMP, int(inst.meta["imm"])))
                    emit(shr_u32(rd, s1, TMP))
                else:
                    emit(shr_u32(rd, s1, _g(regmap, inst.srcs[1])))
            elif inst.op == IROp.CMPP:
                pd = _g(regmap, inst.dst)
                s1 = _g(regmap, inst.srcs[0])
                sub = inst.meta["cmp"]
                if "imm" in inst.meta:
                    emit(loadi(TMP, int(inst.meta["imm"])))
                    emit(cmpp_u32(pd, s1, TMP, sub))
                else:
                    emit(cmpp_u32(pd, s1, _g(regmap, inst.srcs[1]), sub))
            elif inst.op == IROp.LD:
                rd, addr = _g(regmap, inst.dst), _g(regmap, inst.srcs[0])
                ty = 0x2 if inst.meta.get("ty") == "u16" else 0x8
                emit(ld_gmem(rd, addr, ty))
            elif inst.op == IROp.ST:
                emit(st_gmem(_g(regmap, inst.srcs[0]), _g(regmap, inst.srcs[1]), 0x8))
            elif inst.op == IROp.CVT:
                emit(cvt_f32_f16(_g(regmap, inst.dst), _g(regmap, inst.srcs[0])))
            elif inst.op == IROp.BRA:
                fixups.append((len(out), inst.meta["target"]))
                if inst.pred:
                    emit(brx(pred, 0))
                else:
                    emit(br(0))
            elif inst.op == IROp.RET:
                emit(ret())

    emit(halt())

    for pc, tgt in fixups:
        if tgt in label_pc:
            out[pc].w0 = label_pc[tgt] & 0xFFFFFFFF

    return out
