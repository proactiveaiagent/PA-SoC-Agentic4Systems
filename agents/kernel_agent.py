#!/usr/bin/env python3
"""Kernel Agent — C2 Excellent 等级。"""

import json
import sys


def score_candidate(c: dict, case: dict) -> float:
    workspace = case.get("workspace", 8192)
    min_dim = min(case.get("m", 128), case.get("n", 128), case.get("k", 128))
    score = c.get("variant", 0) * 10
    if c.get("workspace", 0) <= workspace:
        score += 20
    else:
        score -= 50
    if min_dim % c.get("divisibility", 1) == 0:
        score += 15
    if c.get("semantic_kernel_id", 0) in (11, 12):
        score += 25
    return score


def decide(case: dict) -> dict:
    candidates = case.get("candidates", [])
    if not candidates:
        return {"kernel_id": ""}
    best = max(candidates, key=lambda c: score_candidate(c, case))
    return {"kernel_id": best["id"]}


def main() -> None:
    case = json.loads(sys.stdin.read())
    json.dump(decide(case), sys.stdout)


if __name__ == "__main__":
    main()
