"""Hex MSB-first 行 → program.bin (w0..w3 little-endian)"""

from __future__ import annotations

from pathlib import Path


def hex_line_to_inst(line: str) -> bytes:
    line = line.strip().replace(" ", "")
    if len(line) != 32:
        raise ValueError(f"invalid hex line length {len(line)}: {line}")
    raw = bytes.fromhex(line)
    # MSB-first 128-bit: raw[0..3]=w3, raw[4..7]=w2, raw[8..11]=w1, raw[12..15]=w0
    w3, w2, w1, w0 = raw[0:4], raw[4:8], raw[8:12], raw[12:16]
    return w0 + w1 + w2 + w3


def hex_file_to_bin(hex_path: Path, bin_path: Path) -> None:
    lines = [ln for ln in hex_path.read_text().splitlines() if ln.strip()]
    blob = b"".join(hex_line_to_inst(ln) for ln in lines)
    bin_path.write_bytes(blob)
