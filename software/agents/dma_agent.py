#!/usr/bin/env python3
"""DMA Agent — 竞赛 C2 Excellent 等级接口实现。

从 stdin 读取 JSON，向 stdout 输出调度决策。
"""

import json
import sys


def decide(case: dict) -> dict:
    direction = case.get("direction", "h2d")
    bytes_ = case.get("bytes", 4096)
    alignment = case.get("alignment", 64)
    registered = case.get("registered", False)
    concurrency = case.get("concurrency", 1)

    # PA-SoC 优化：感知数据流优先走 channel 0，反应用 channel 1
    channel = 0 if direction == "h2d" else 1

    # 大块数据分片传输，减少 DMA 延迟
    chunk_bytes = min(bytes_, max(alignment, 4096))
    if bytes_ > 65536:
        chunk_bytes = 16384
    elif bytes_ > 16384:
        chunk_bytes = 8192

    queue_depth = min(concurrency, 4)
    use_zero_copy = registered and bytes_ >= alignment

    return {
        "channel": channel,
        "chunk_bytes": chunk_bytes,
        "queue_depth": queue_depth,
        "use_zero_copy": use_zero_copy,
    }


def main() -> None:
    raw = sys.stdin.read()
    case = json.loads(raw)
    result = decide(case)
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
