"""PTX -> IR Lowering。"""

from __future__ import annotations

from ir import BasicBlock, IRFunction, IRInst, IROp
from ptx_parser import PtxKernel, parse_float_imm, parse_reg, vreg

CMP_MAP = {"eq": 0, "ne": 1, "lt": 2, "le": 3, "gt": 4, "ge": 5}

SR_MAP = {
    "%tid.x": "tid.x", "%tid": "tid.x",
    "%ctaid.x": "ctaid.x", "%ctaid": "ctaid.x",
    "%ntid.x": "ntid.x", "%ntid": "ntid.x",
    "%ctaid.y": "ctaid.y",
    "%tid.y": "tid.y",
}


def _is_reg(tok: str) -> bool:
    return tok.startswith("%")


def _src(tok: str) -> str | None:
    return vreg(*parse_reg(tok)) if _is_reg(tok) else None


def _param_offsets(params: list[tuple[str, str]]) -> dict[str, tuple[int, str]]:
    off = 0
    table: dict[str, tuple[int, str]] = {}
    for ptype, pname in params:
        table[pname] = (off, ptype)
        off += 8 if ptype == ".u64" else 4
    return table


def lower_ptx(kernel: PtxKernel) -> IRFunction:
    fn = IRFunction(kernel.name, kernel.params)
    block = BasicBlock(None)
    ptab = _param_offsets(kernel.params)

    for item in kernel.body:
        if item.label:
            if block.insts:
                fn.blocks.append(block)
            block = BasicBlock(item.label)
            continue

        pred = vreg(*parse_reg(item.pred.lstrip("@"))) if item.pred else None
        mn, args = item.mnemonic, item.args

        def emit(op: IROp, dst=None, srcs=None, meta=None, p=None):
            block.insts.append(IRInst(op, dst, srcs or [], meta or {}, p or pred))

        if mn.startswith("ld.param"):
            dst = vreg(*parse_reg(args[0]))
            pname = args[1].strip("[]")
            off, ptype = ptab[pname]
            emit(IROp.PARAM_LOAD, dst, [], {"offset": off, "ptype": ptype})
        elif mn == "mov.u32":
            dst = vreg(*parse_reg(args[0]))
            src = args[1]
            if src in SR_MAP:
                emit(IROp.MOV_SR, dst, [], {"sr": SR_MAP[src]})
            elif _is_reg(src):
                emit(IROp.MOV, dst, [vreg(*parse_reg(src))])
            else:
                emit(IROp.LOADI, dst, [], {"imm": int(src)})
        elif mn == "mov.f32":
            dst = vreg(*parse_reg(args[0]))
            if args[1].startswith("0f"):
                emit(IROp.LOADI_F32, dst, [], {"imm": parse_float_imm(args[1])})
            else:
                emit(IROp.MOV, dst, [vreg(*parse_reg(args[1]))])
        elif mn.startswith("setp."):
            cmp_op = mn.split(".")[1]
            pd = vreg(*parse_reg(args[0]))
            rs1 = vreg(*parse_reg(args[1]))
            meta = {"cmp": CMP_MAP[cmp_op]}
            if _is_reg(args[2]):
                emit(IROp.CMPP, pd, [rs1, vreg(*parse_reg(args[2]))], meta)
            else:
                meta["imm"] = int(args[2])
                emit(IROp.CMPP, pd, [rs1], meta)
        elif mn == "mad.lo.u32":
            dst = vreg(*parse_reg(args[0]))
            a = vreg(*parse_reg(args[1]))
            if _is_reg(args[2]):
                b = vreg(*parse_reg(args[2]))
                c = vreg(*parse_reg(args[3]))
                emit(IROp.MAD, dst, [a, b, c], {"ty": "u32"})
            else:
                # mad.lo.u32 dst, a, imm, c  ->  dst = a*imm + c
                emit(IROp.MUL, dst, [a], {"imm": int(args[2]), "ty": "u32"})
                emit(IROp.ADD, dst, [dst, vreg(*parse_reg(args[3]))], {"ty": "u32"})
        elif mn == "mad.f32":
            emit(IROp.MAD, vreg(*parse_reg(args[0])),
                 [vreg(*parse_reg(args[1])), vreg(*parse_reg(args[2])), vreg(*parse_reg(args[3]))], {"ty": "f32"})
        elif mn == "mul.wide.u32":
            emit(IROp.MUL, vreg(*parse_reg(args[0])), [vreg(*parse_reg(args[1]))], {"imm": int(args[2])})
        elif mn == "mul.lo.u32":
            s2 = _src(args[2]) if _is_reg(args[2]) else None
            meta = {"ty": "u32"}
            if s2 is None:
                meta["imm"] = int(args[2])
                emit(IROp.MUL, vreg(*parse_reg(args[0])), [vreg(*parse_reg(args[1]))], meta)
            else:
                emit(IROp.MUL, vreg(*parse_reg(args[0])), [vreg(*parse_reg(args[1])), s2], meta)
        elif mn == "mul.f32":
            emit(IROp.MUL, vreg(*parse_reg(args[0])), [vreg(*parse_reg(args[1])), vreg(*parse_reg(args[2]))], {"ty": "f32"})
        elif mn == "add.u32":
            dst = vreg(*parse_reg(args[0]))
            s1 = vreg(*parse_reg(args[1]))
            if _is_reg(args[2]):
                emit(IROp.ADD, dst, [s1, vreg(*parse_reg(args[2]))], {"ty": "u32"})
            else:
                emit(IROp.ADD, dst, [s1], {"ty": "u32", "imm": int(args[2])})
        elif mn == "add.u64":
            emit(IROp.ADD, vreg(*parse_reg(args[0])), [vreg(*parse_reg(args[1])), vreg(*parse_reg(args[2]))], {"ty": "u64"})
        elif mn == "add.f32":
            emit(IROp.ADD, vreg(*parse_reg(args[0])), [vreg(*parse_reg(args[1])), vreg(*parse_reg(args[2]))], {"ty": "f32"})
        elif mn == "sub.f32":
            emit(IROp.SUB, vreg(*parse_reg(args[0])), [vreg(*parse_reg(args[1])), vreg(*parse_reg(args[2]))], {"ty": "f32"})
        elif mn == "and.b32":
            dst, s1 = vreg(*parse_reg(args[0])), vreg(*parse_reg(args[1]))
            if _is_reg(args[2]):
                emit(IROp.AND, dst, [s1, vreg(*parse_reg(args[2]))])
            else:
                emit(IROp.AND, dst, [s1], {"imm": int(args[2])})
        elif mn.startswith("shr.u32"):
            dst, s1 = vreg(*parse_reg(args[0])), vreg(*parse_reg(args[1]))
            if _is_reg(args[2]):
                emit(IROp.SHR, dst, [s1, vreg(*parse_reg(args[2]))])
            else:
                emit(IROp.SHR, dst, [s1], {"imm": int(args[2])})
        elif mn.startswith("ld.global"):
            dst = vreg(*parse_reg(args[0]))
            addr = vreg(*parse_reg(args[1].strip("[]")))
            ty = "u16" if ".u16" in mn else "f32"
            emit(IROp.LD, dst, [addr], {"ty": ty})
        elif mn.startswith("st.global.f32"):
            emit(IROp.ST, None, [vreg(*parse_reg(args[0].strip("[]"))), vreg(*parse_reg(args[1]))], {"ty": "f32"})
        elif mn.startswith("cvt.f32.f16"):
            emit(IROp.CVT, vreg(*parse_reg(args[0])), [vreg(*parse_reg(args[1]))], {"from": "f16", "to": "f32"})
        elif mn == "bra":
            emit(IROp.BRA, None, [], {"target": args[0]})
        elif mn == "ret":
            emit(IROp.RET)

    if block.insts or block.name:
        fn.blocks.append(block)
    return fn
