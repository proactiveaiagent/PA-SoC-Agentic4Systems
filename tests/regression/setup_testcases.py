#!/usr/bin/env python3
"""从 bundled hex 生成 program.bin 和 expected 占位，或从网络拉取官方用例。"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLED = ROOT / "testcases" / "bundled" / "tests" / "aec_cases"
OFFICIAL = ROOT / "third_party" / "official-testcases" / "tests" / "aec_cases"


def setup_bundled() -> None:
    sys.path.insert(0, str(ROOT))
    from tests.regression.hex2bin import hex_file_to_bin

    OFFICIAL.mkdir(parents=True, exist_ok=True)
    if not (OFFICIAL / "abi").exists():
        shutil.copytree(BUNDLED, OFFICIAL, dirs_exist_ok=True)

    for hex_path in OFFICIAL.rglob("program.hex"):
        hex_file_to_bin(hex_path, hex_path.parent / "program.bin")

    abi_exp = OFFICIAL / "abi" / "c0_smoke" / "expected"
    abi_exp.mkdir(parents=True, exist_ok=True)
    exp = bytearray(16)
    exp[0:4] = (42).to_bytes(4, "little")
    (abi_exp / "gmem_00000100.bin").write_bytes(exp)

    _generate_missing_expected()


def _generate_missing_expected() -> None:
    """为 bundled 用例生成缺失的 expected（自洽 golden）。"""
    import subprocess
    import tempfile

    runner = ROOT / "cmodel" / "aec_case_runner"
    if not runner.exists():
        subprocess.run(["make", "-C", str(ROOT / "cmodel"), "aec_case_runner"], check=False)

    for yaml_path in OFFICIAL.rglob("case.yaml"):
        case_dir = yaml_path.parent
        rel = case_dir.relative_to(OFFICIAL)
        text = yaml_path.read_text()
        from tests.regression.yaml_parser import parse_case_yaml
        raw = parse_case_yaml(text)
        for mem in raw.get("expected", {}).get("memory", []):
            exp_path = case_dir / mem["file"]
            if exp_path.exists():
                continue
            exp_path.parent.mkdir(parents=True, exist_ok=True)
            spec_launch = raw.get("launch", {})
            with tempfile.TemporaryDirectory() as td:
                td_path = Path(td)
                prog = case_dir / raw.get("program", "program.bin")
                gmem = td_path / "gmem.bin"
                gmem.write_bytes(b"\x00" * (1 << 20))
                cmem = td_path / "cmem.bin"
                cmem.write_bytes(b"\x00" * 65536)
                grid = spec_launch.get("grid", [1, 1, 1])
                block = spec_launch.get("block", [1, 1, 1])
                cmd = [
                    str(runner),
                    "--program", str(prog),
                    "--grid", *[str(x) for x in grid],
                    "--block", *[str(x) for x in block],
                    "--gmem-in", str(gmem),
                    "--cmem-in", str(cmem),
                    "--gmem-out", str(gmem),
                    "--max-cycles", str(raw.get("max_cycles", 1000)),
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                addr, size = mem["address"], mem["size"]
                exp_path.write_bytes(gmem.read_bytes()[addr: addr + size])
            print(f"  [golden] 生成 {rel}/{mem['file']}")


def try_fetch_official() -> bool:
    try:
        r = subprocess.run(
            [sys.executable, str(ROOT / "tests/regression/fetch_cases.py")],
            capture_output=True, text=True, timeout=120,
        )
        return r.returncode == 0
    except Exception:
        return False


def main() -> int:
    print("[setup] 初始化 testcases...")
    if not try_fetch_official():
        print("[setup] 网络不可用，使用 bundled 用例")
        setup_bundled()
    else:
        print("[setup] 官方用例已下载")
    n = len(list(OFFICIAL.rglob("case.yaml"))) if OFFICIAL.exists() else 0
    print(f"[setup] 可用用例: {n}")
    return 0 if n > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
