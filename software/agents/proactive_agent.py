#!/usr/bin/env python3
"""Proactive Agent — PA-SoC 专用调度 Agent。

为竞赛 C2 Agent 评分扩展：根据传感器负载和推理阶段
动态选择 GPGPU 计算资源分配策略。
"""

import json
import sys


PHASE_RESOURCE_MAP = {
    "perception": {"priority": 1, "smem_kb": 48, "warps": 4, "precision": "fp16"},
    "reasoning":  {"priority": 2, "smem_kb": 64, "warps": 8, "precision": "fp32"},
    "memory":     {"priority": 0, "smem_kb": 32, "warps": 2, "precision": "fp32"},
    "tool_exec":  {"priority": 3, "smem_kb": 16, "warps": 1, "precision": "fp32"},
    "rl_update":  {"priority": 0, "smem_kb": 8,  "warps": 1, "precision": "fp32"},
}


def decide(case: dict) -> dict:
    phase = case.get("phase", "perception")
    sensor_fps = case.get("sensor_fps", 30)
    confidence = case.get("confidence", 0.5)
    fast_track = case.get("fast_track", False)

    base = PHASE_RESOURCE_MAP.get(phase, PHASE_RESOURCE_MAP["perception"])

    warps = base["warps"]
    if sensor_fps > 60:
        warps = min(warps + 2, 8)
    if fast_track:
        warps = max(warps - 2, 1)

    precision = base["precision"]
    if phase == "reasoning" and confidence < 0.7:
        precision = "fp32"
    elif phase == "perception":
        precision = "fp16"

    return {
        "phase": phase,
        "priority": base["priority"],
        "allocated_warps": warps,
        "smem_bytes": base["smem_kb"] * 1024,
        "precision": precision,
        "enable_aop": phase == "perception",
        "enable_kv_cache": phase == "reasoning",
        "enable_rl_buffer": phase == "rl_update",
    }


def main() -> None:
    raw = sys.stdin.read()
    case = json.loads(raw)
    result = decide(case)
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
