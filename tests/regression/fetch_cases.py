#!/usr/bin/env python3
"""按需从 GitHub Raw 下载官方 testcase 文件。"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "third_party" / "official-testcases" / "tests" / "aec_cases"
PUBLIC_LIST = ROOT / "testcases" / "PUBLIC_CASES.txt"
BASE_RAW = (
    "https://raw.githubusercontent.com/ephonic/"
    "Agentic4SystemSummerSchoolContest/main/Track-B/testcases/tests/aec_cases"
)


def _fetch(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as e:
        print(f"  [fetch] 失败 {url}: {e}")
        return False


def ensure_case(rel: str) -> bool:
    case_dir = CASES_DIR / rel
    yaml_path = case_dir / "case.yaml"
    if yaml_path.exists() and (case_dir / "program.bin").exists():
        return True

    prefix = f"{BASE_RAW}/{rel}"
    ok = _fetch(f"{prefix}/case.yaml", yaml_path)
    if not ok:
        return False

    text = yaml_path.read_text()
    _fetch(f"{prefix}/program.bin", case_dir / "program.bin")

    for m in re.finditer(r"file:\s*(\S+)", text):
        fpath = m.group(1)
        _fetch(f"{prefix}/{fpath}", case_dir / fpath)

    return (case_dir / "program.bin").exists()


def ensure_all() -> int:
    if not PUBLIC_LIST.exists():
        return 0
    count = 0
    for line in PUBLIC_LIST.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rel = line.split("tests/aec_cases/")[-1]
        if ensure_case(rel):
            count += 1
    return count


if __name__ == "__main__":
    import sys
    n = ensure_all()
    print(f"[fetch] 就绪用例: {n}")
    sys.exit(0 if n > 0 else 1)
