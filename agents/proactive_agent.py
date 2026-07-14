#!/usr/bin/env python3
"""Proactive Agent — PA-SoC 阶段资源调度。"""

import json
import sys

PHASE_MAP = {
    "perception": {"priority": 1, "smem_kb": 48, "warps": 4, "precision": "fp16"},
    "reasoning":  {"priority": 2, "smem_kb": 64, "warps": 8, "precision": "fp32"},
    "memory":     {"priority": 0, "smem_kb": 32, "warps": 2, "precision": "fp32"},
    "tool_exec":  {"priority": 3, "smem_kb": 16, "warps": 1, "precision": "fp32"},
    "rl_update":  {"priority": 0, "smem_kb": 8,  "warps": 1, "precision": "fp32"},
}


def decide(case: dict) -> dict:
    phase = case.get("phase", "perception")
    base = PHASE_MAP.get(phase, PHASE_MAP["perception"])
    warps = base["warps"]
    if case.get("sensor_fps", 30) > 60:
        warps = min(warps + 2, 8)
    if case.get("fast_track"):
        warps = max(warps - 2, 1)
    return {
        "phase": phase,
        "priority": base["priority"],
        "allocated_warps": warps,
        "smem_bytes": base["smem_kb"] * 1024,
        "precision": base["precision"],
        "enable_aop": phase == "perception",
        "enable_kv_cache": phase == "reasoning",
        "enable_rl_buffer": phase == "rl_update",
    }


def main() -> None:
    json.dump(decide(json.loads(sys.stdin.read())), sys.stdout)


if __name__ == "__main__":
    main()
