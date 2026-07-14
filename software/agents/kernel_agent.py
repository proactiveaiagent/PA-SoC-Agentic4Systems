#!/usr/bin/env python3
"""Kernel Agent — 竞赛 C2 Excellent 等级接口实现。

从候选 kernel 中选择最优方案。
"""

import json
import sys


def score_candidate(c: dict, case: dict) -> float:
    m, n, k = case.get("m", 128), case.get("n", 128), case.get("k", 128)
    dtype = case.get("dtype", "f16")
    workspace = case.get("workspace", 8192)

    score = 0.0
    variant = c.get("variant", 0)
    c_workspace = c.get("workspace", 0)
    divisibility = c.get("divisibility", 1)

    # 变体越高通常优化越好
    score += variant * 10

    # workspace 充裕度
    if c_workspace <= workspace:
        score += 20
    else:
        score -= 50

    # 整除性匹配
    min_dim = min(m, n, k)
    if min_dim % divisibility == 0:
        score += 15

    # PA-SoC 场景优化：主动智能体推理优先 tiled/vectorized
    sem_id = c.get("semantic_kernel_id", 0)
    if sem_id in (11, 12):  # GEMM_TILED, GEMM_VECTORIZED
        score += 25

    # 精度匹配
    if dtype in ("f16", "bf16") and sem_id >= 10:
        score += 10
    if dtype == "f32" and sem_id == 10:
        score += 5

    return score


def decide(case: dict) -> dict:
    candidates = case.get("candidates", [])
    if not candidates:
        return {"kernel_id": ""}

    best = max(candidates, key=lambda c: score_candidate(c, case))
    return {"kernel_id": best["id"]}


def main() -> None:
    raw = sys.stdin.read()
    case = json.loads(raw)
    result = decide(case)
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
