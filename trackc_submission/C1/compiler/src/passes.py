"""编译优化 Pass。"""

from __future__ import annotations

from ir import IRFunction, IRInst, IROp


def pass_dce(fn: IRFunction) -> IRFunction:
    for bb in fn.blocks:
        live: set[str] = set()
        kept: list[IRInst] = []
        for inst in reversed(bb.insts):
            if inst.op in (IROp.ST, IROp.BRA, IROp.RET, IROp.CMPP, IROp.PARAM_LOAD):
                kept.append(inst)
                if inst.dst:
                    live.add(inst.dst)
                live.update(inst.srcs)
                continue
            if inst.dst and inst.dst.startswith("v:") and inst.dst not in live:
                continue
            kept.append(inst)
            if inst.dst:
                live.add(inst.dst)
            live.update(inst.srcs)
        bb.insts = list(reversed(kept))
    return fn


def pass_cse(fn: IRFunction) -> IRFunction:
    for bb in fn.blocks:
        table: dict[tuple, str] = {}
        out: list[IRInst] = []
        for inst in bb.insts:
            if inst.op in (IROp.ADD, IROp.MUL, IROp.MAD, IROp.SUB) and inst.dst:
                key = (inst.op, tuple(inst.srcs), inst.meta.get("ty"), inst.meta.get("imm"))
                if key in table:
                    out.append(IRInst(IROp.MOV, inst.dst, [table[key]], inst.meta, inst.pred))
                    continue
                table[key] = inst.dst
            out.append(inst)
        bb.insts = out
    return fn


def pass_regalloc(fn: IRFunction) -> tuple[IRFunction, dict[str, int]]:
    regmap: dict[str, int] = {}
    gpr, pred = 1, 0
    for bb in fn.blocks:
        for inst in bb.insts:
            refs = ([inst.dst] if inst.dst else []) + inst.srcs + ([inst.pred] if inst.pred else [])
            for v in refs:
                if not v or v in regmap:
                    continue
                if v.startswith("v:p:"):
                    regmap[v] = pred
                    pred += 1
                else:
                    regmap[v] = gpr
                    gpr += 1
    return fn, regmap


def pass_schedule(fn: IRFunction) -> IRFunction:
    for bb in fn.blocks:
        mem, alu, ctrl = [], [], []
        for inst in bb.insts:
            if inst.op in (IROp.LD, IROp.ST, IROp.PARAM_LOAD):
                mem.append(inst)
            elif inst.op in (IROp.ADD, IROp.MUL, IROp.MAD, IROp.SUB, IROp.CVT, IROp.CMPP):
                alu.append(inst)
            else:
                ctrl.append(inst)
        merged: list[IRInst] = []
        i = j = 0
        while i < len(mem) or j < len(alu):
            if i < len(mem):
                merged.append(mem[i])
                i += 1
            if j < len(alu):
                merged.append(alu[j])
                j += 1
        merged.extend(ctrl)
        if merged:
            bb.insts = merged
    return fn


def run_passes(fn: IRFunction, opt_level: str) -> tuple[IRFunction, dict[str, int]]:
    if opt_level != "0":
        fn = pass_cse(fn)
        fn = pass_dce(fn)
        fn = pass_schedule(fn)
    fn, regmap = pass_regalloc(fn)
    if opt_level == "3":
        fn = pass_cse(fn)
        fn = pass_dce(fn)
    return fn, regmap
