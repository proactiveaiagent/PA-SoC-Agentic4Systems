#!/usr/bin/env python3
"""
官方 Track-B testcases 自动化回归。

用法:
  python3 tests/regression/run_regression.py
  python3 tests/regression/run_regression.py --case abi/c0_smoke
  python3 tests/regression/run_regression.py --target cmodel
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.regression.yaml_parser import parse_case_yaml
TESTCASES_ROOT = ROOT / "third_party" / "official-testcases"
CASES_LIST = ROOT / "testcases" / "PUBLIC_CASES.txt"
if not CASES_LIST.exists():
    CASES_LIST = TESTCASES_ROOT / "PUBLIC_CASES.txt"
CASES_DIR = TESTCASES_ROOT / "tests" / "aec_cases"
CMODEL_RUNNER = ROOT / "cmodel" / "aec_case_runner"
SETUP_SCRIPT = ROOT / "scripts" / "setup_testcases.sh"


@dataclass
class CaseSpec:
    path: str
    case_id: str = ""
    program: str = "program.bin"
    grid: list[int] = field(default_factory=lambda: [1, 1, 1])
    block: list[int] = field(default_factory=lambda: [1, 1, 1])
    program_instructions: int = 0
    memory_init: list[dict] = field(default_factory=list)
    expected_status: str = "done"
    expected_memory: list[dict] = field(default_factory=list)
    max_cycles: int = 1000


def ensure_testcases() -> None:
    sample = CASES_DIR / "abi" / "c0_smoke" / "case.yaml"
    if not sample.exists():
        subprocess.run([sys.executable, str(ROOT / "tests/regression/setup_testcases.py")],
                       check=True)


def load_case(rel_path: str) -> CaseSpec:
    case_dir = CASES_DIR / rel_path
    yaml_path = case_dir / "case.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(yaml_path)

    raw = parse_case_yaml(yaml_path.read_text())
    launch = raw.get("launch", {})
    expected = raw.get("expected", {})

    prog_len = launch.get("program_instructions", 0)
    if not prog_len:
        bin_path = case_dir / raw.get("program", "program.bin")
        if bin_path.exists():
            prog_len = bin_path.stat().st_size // 16

    return CaseSpec(
        path=rel_path,
        case_id=raw.get("case_id", rel_path),
        program=raw.get("program", "program.bin"),
        grid=launch.get("grid", [1, 1, 1]),
        block=launch.get("block", [1, 1, 1]),
        program_instructions=prog_len,
        memory_init=raw.get("memory_init", []),
        expected_status=expected.get("status", "done"),
        expected_memory=expected.get("memory", []),
        max_cycles=raw.get("max_cycles", 1000),
    )


def load_program(case_dir: Path, spec: CaseSpec) -> bytes:
    bin_path = case_dir / spec.program
    if not bin_path.exists():
        raise FileNotFoundError(bin_path)
    data = bin_path.read_bytes()
    if spec.program_instructions:
        data = data[: spec.program_instructions * 16]
    return data


def apply_memory_init(gmem: bytearray, cmem: bytearray, case_dir: Path,
                      inits: list[dict]) -> None:
    for entry in inits:
        target = entry.get("target", "gmem")
        addr = entry.get("address", 0)
        fpath = case_dir / entry["file"]
        blob = fpath.read_bytes()
        mem = gmem if target == "gmem" else cmem
        end = addr + len(blob)
        if end > len(mem):
            mem.extend(b"\x00" * (end - len(mem)))
        mem[addr:end] = blob


def compare_memory(gmem: bytes, case_dir: Path, checks: list[dict]) -> tuple[bool, str]:
    for chk in checks:
        addr = chk.get("address", 0)
        size = chk.get("size", 0)
        exp_file = case_dir / chk["file"]
        if not exp_file.exists():
            return False, f"缺少 expected 文件: {exp_file}"
        expected = exp_file.read_bytes()
        if len(expected) != size:
            size = len(expected)
        actual = gmem[addr : addr + size]
        if actual != expected:
            diff_idx = next((i for i in range(size) if actual[i] != expected[i]), -1)
            return False, (
                f"GMEM 不匹配 @0x{addr:x}+{size} "
                f"首差异偏移={diff_idx} "
                f"期望=0x{expected[diff_idx]:02x} 实际=0x{actual[diff_idx]:02x}"
            )
    return True, "ok"


def run_case_cmodel(spec: CaseSpec) -> dict[str, Any]:
    case_dir = CASES_DIR / spec.path
    prog_bin = load_program(case_dir, spec)
    gmem = bytearray(1 << 20)
    cmem = bytearray(65536)
    apply_memory_init(gmem, cmem, case_dir, spec.memory_init)

    if not CMODEL_RUNNER.exists():
        build = subprocess.run(["make", "-C", str(ROOT / "cmodel"), "aec_case_runner"],
                               capture_output=True, text=True)
        if build.returncode != 0:
            return {"case": spec.case_id, "status": "BUILD_FAIL",
                    "message": build.stderr}

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as pf:
        pf.write(prog_bin)
        prog_path = pf.name
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as gf:
        gf.write(gmem)
        gmem_path = gf.name
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as cf:
        cf.write(cmem)
        cmem_path = cf.name

    cmd = [
        str(CMODEL_RUNNER),
        "--program", prog_path,
        "--grid", *map(str, spec.grid),
        "--block", *map(str, spec.block),
        "--gmem-in", gmem_path,
        "--cmem-in", cmem_path,
        "--gmem-out", gmem_path,
        "--max-cycles", str(spec.max_cycles),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    os.unlink(prog_path)

    if result.returncode == 2:
        return {"case": spec.case_id, "status": "EXEC_ERROR",
                "message": result.stderr or result.stdout}
    if result.returncode != 0:
        return {"case": spec.case_id, "status": "RUN_FAIL",
                "message": result.stderr}

    gmem_out = Path(gmem_path).read_bytes()
    os.unlink(gmem_path)
    os.unlink(cmem_path)

    ok, msg = compare_memory(gmem_out, case_dir, spec.expected_memory)
    cycles = 0
    for line in result.stdout.splitlines():
        if line.startswith("cycles="):
            cycles = int(line.split("=", 1)[1])

    return {
        "case": spec.case_id,
        "path": spec.path,
        "status": "PASS" if ok else "FAIL",
        "message": msg,
        "cycles": cycles,
    }


def list_cases(filter_path: str | None = None) -> list[str]:
    if filter_path:
        return [filter_path]
    list_file = CASES_LIST
    if not CASES_DIR.exists() or len(list(CASES_DIR.rglob("case.yaml"))) <= 2:
        bundled = ROOT / "testcases" / "BUNDLED_CASES.txt"
        if bundled.exists():
            list_file = bundled
    lines = list_file.read_text().strip().splitlines()
    paths = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rel = line.split("tests/aec_cases/")[-1]
        paths.append(rel)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="AEC 官方 testcases 回归")
    parser.add_argument("--case", help="单个用例相对路径，如 abi/c0_smoke")
    parser.add_argument("--target", choices=["cmodel", "rtl", "both"],
                        default="cmodel")
    parser.add_argument("--output", default=str(ROOT / "evidence" / "regression"))
    args = parser.parse_args()

    ensure_testcases()
    os.makedirs(args.output, exist_ok=True)

    cases = list_cases(args.case)
    results = []
    t0 = time.time()

    print("=" * 60)
    print(f"  AEC 官方 testcases 回归 ({len(cases)} 用例)")
    print("=" * 60)

    for rel in cases:
        try:
            spec = load_case(rel)
            if args.target in ("cmodel", "both"):
                r = run_case_cmodel(spec)
            else:
                r = {"case": spec.case_id, "status": "SKIP",
                     "message": "RTL runner 待接入"}
            results.append(r)
            mark = "✓" if r["status"] == "PASS" else "✗"
            print(f"  {mark} {r['case']:<30} {r['status']:<12} {r.get('message','')}")
        except Exception as e:
            results.append({"case": rel, "status": "ERROR", "message": str(e)})
            print(f"  ✗ {rel:<30} ERROR        {e}")

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = len(results) - passed
    elapsed = time.time() - t0

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "elapsed_sec": round(elapsed, 2),
        "results": results,
    }
    report_path = Path(args.output) / "regression_report.json"
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print("=" * 60)
    print(f"  结果: {passed}/{len(results)} 通过, 耗时 {elapsed:.1f}s")
    print(f"  报告: {report_path}")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
