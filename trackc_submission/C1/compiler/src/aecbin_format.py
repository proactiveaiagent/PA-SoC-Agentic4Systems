"""AEC 二进制格式：Header + Code + Data + Reloc + Symtab。"""

from __future__ import annotations

import struct
from pathlib import Path

from inst_encode import AecInst

MAGIC = b"AEC\x00"
VERSION = 1
HEADER_SIZE = 64


def write_aecbin(path: Path, instructions: list[AecInst], data: bytes = b"") -> None:
    code_blob = b"".join(i.to_bytes() for i in instructions)
    code_off = HEADER_SIZE
    code_sz = len(code_blob)
    data_off = code_off + code_sz
    data_sz = len(data)
    reloc_off = data_off + data_sz
    reloc_sz = 0
    sym_off = reloc_off + reloc_sz
    sym_sz = 0

    header = bytearray(HEADER_SIZE)
    header[0:4] = MAGIC
    struct.pack_into("<I", header, 4, VERSION)
    struct.pack_into("<Q", header, 8, code_off)
    struct.pack_into("<Q", header, 16, code_sz)
    struct.pack_into("<Q", header, 24, data_off)
    struct.pack_into("<Q", header, 32, data_sz)
    struct.pack_into("<Q", header, 40, reloc_off)
    struct.pack_into("<Q", header, 48, reloc_sz)
    struct.pack_into("<Q", header, 56, sym_off)

    path.write_bytes(bytes(header) + code_blob + data)


def read_aecbin(path: Path) -> tuple[list[AecInst], bytes]:
    raw = path.read_bytes()
    if raw[:4] != MAGIC:
        raise ValueError("invalid AEC magic")
    code_off = struct.unpack_from("<Q", raw, 8)[0]
    code_sz = struct.unpack_from("<Q", raw, 16)[0]
    data_off = struct.unpack_from("<Q", raw, 24)[0]
    data_sz = struct.unpack_from("<Q", raw, 32)[0]
    code = raw[code_off: code_off + code_sz]
    data = raw[data_off: data_off + data_sz]
    insts = []
    for i in range(0, len(code), 16):
        w0, w1, w2, w3 = struct.unpack_from("<IIII", code, i)
        insts.append(AecInst(w0, w1, w2, w3))
    return insts, data
