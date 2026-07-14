#!/usr/bin/env python3
"""PA-SoC 主动型智能体端到端演示。

模拟完整认知闭环：
  感知 → 推理 → 工具援助 → 观察反应 → RL 强化
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "software"))

from pa_sdk.pipeline import ProactiveAgentPipeline
from pa_sdk.types import SensorFrame


def make_frame(timestamp: float, behavior_hint: str) -> SensorFrame:
    """根据行为提示生成模拟传感器帧。"""
    profiles = {
        "stuck_coding": {
            "video": [0.9] * 64,
            "audio": ([0.9, 0.1, 0.8, 0.2, 0.85, 0.15, 0.75, 0.25] * 8)[:64],
            "motion": 0.3,
        },
        "normal_work": {
            "video": [0.5] * 64,
            "audio": [0.3] * 64,
            "motion": 0.4,
        },
        "scrolling": {
            "video": [0.7] * 64,
            "audio": [0.1] * 64,
            "motion": 0.2,
        },
    }
    p = profiles.get(behavior_hint, profiles["normal_work"])
    return SensorFrame(
        timestamp=timestamp,
        video_features=p["video"],
        audio_features=p["audio"],
        imu_motion=p["motion"],
    )


def main():
    print("=" * 60)
    print("  PA-SoC 主动型智能体端到端演示")
    print("  Agentic4Systems GPGPU 加速设计竞赛 2026")
    print("=" * 60)

    agent = ProactiveAgentPipeline(user_id="demo_user")

    # --- Cycle 1: 用户反复删改代码（沮丧） ---
    print("\n[Cycle 1] 传感器检测：用户反复删改代码...")
    frame1 = make_frame(1718342400.0, "stuck_coding")
    result1 = agent.process_sensor_frame(frame1)
    print(json.dumps(result1, indent=2, ensure_ascii=False))

    # --- Cycle 2: 观察用户反应（开始阅读示例） ---
    print("\n[Cycle 2] 观察用户反应：停止删改，开始阅读...")
    frame2 = make_frame(1718342400.5, "normal_work")
    result2 = agent.process_reaction(frame2)
    print(json.dumps(result2, indent=2, ensure_ascii=False))

    # --- Cycle 3: 用户反复滚动页面 ---
    print("\n[Cycle 3] 传感器检测：用户反复滚动页面...")
    frame3 = make_frame(1718342401.0, "scrolling")
    result3 = agent.process_sensor_frame(frame3)
    print(json.dumps(result3, indent=2, ensure_ascii=False))

    # --- 汇总 ---
    print("\n" + "=" * 60)
    print("  运行汇总")
    print("=" * 60)
    print(f"  总周期数:     {agent.state.cycle_count}")
    print(f"  累计奖励:     {agent.state.total_rewards:.2f}")
    print(f"  策略条目数:   {len(agent.rl.policy_table)}")
    print(f"  画像模式数:   {len(agent.memory.profile.behavior_patterns)}")
    print(f"  反思记录数:   {len(agent.rl.reflections)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
