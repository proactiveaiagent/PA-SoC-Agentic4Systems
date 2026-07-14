#!/usr/bin/env python3
"""DMA Agent — C2 Excellent 等级（竞赛合规版）。"""

import json
import sys

LEGAL_CHUNKS = (4096, 65536, 1048576)
LEGAL_QUEUES = (1, 2, 4, 8)


def pick_chunk(bytes_: int) -> int:
    for c in reversed(LEGAL_CHUNKS):
        if bytes_ >= c:
            return c
    return 4096


def pick_queue(concurrency: int) -> int:
    for q in reversed(LEGAL_QUEUES):
        if concurrency >= q:
            return q
    return 1


def decide(case: dict) -> dict:
    direction = case.get("direction", "h2d")
    bytes_ = case.get("bytes", 4096)
    alignment = case.get("alignment", 64)
    registered = case.get("registered", False)
    concurrency = case.get("concurrency", 1)

    channel = 0 if direction == "h2d" else 1
    chunk_bytes = pick_chunk(bytes_)
    queue_depth = pick_queue(concurrency)
    use_zero_copy = registered and alignment >= 64

    return {
        "channel": channel,
        "chunk_bytes": chunk_bytes,
        "queue_depth": queue_depth,
        "use_zero_copy": use_zero_copy,
    }


def main() -> None:
    case = json.loads(sys.stdin.read())
    json.dump(decide(case), sys.stdout)


if __name__ == "__main__":
    main()
