"""主动型智能体主流水线 — 端到端认知闭环。"""

from __future__ import annotations

import time
from typing import Any

from .memory import MemorySubsystem
from .perception import MultimodalPerceptionEngine
from .reasoning import ReasoningEngine
from .rl import RLEngine
from .tools import ToolOrchestrator
from .types import AgentState, PerceptionOutput, SensorFrame


class ProactiveAgentPipeline:
    """PA-SoC 主动智能体完整流水线。

    端到端时序：
    T+0   传感器捕获 → T+15ms MM-Engine → T+50ms 推理
    → T+60ms 工具执行 → T+500ms 观察反应 → T+810ms RL 强化
    """

    def __init__(self, user_id: str = "default_user"):
        self.perception = MultimodalPerceptionEngine()
        self.memory = MemorySubsystem(user_id)
        self.reasoning = ReasoningEngine(
            help_threshold=self.memory.profile.preferences.get("help_threshold", 0.6)
        )
        self.tools = ToolOrchestrator()
        self.rl = RLEngine()
        self.state = AgentState(profile=self.memory.profile)

    def process_sensor_frame(self, frame: SensorFrame) -> dict[str, Any]:
        """处理单帧传感器数据，执行完整主动援助循环。"""
        t0 = time.time()
        self.state.cycle_count += 1

        # Phase 1: 多模态感知 (MM-Engine)
        perception = self.perception.perceive(frame)
        self.memory.store_perception(perception)
        self.memory.update_profile_from_perception(perception)
        self.state.last_perception = perception

        # Phase 2: 推理决策 (Reasoning Engine)
        plan = self.reasoning.predict_need(perception, self.memory)
        if plan is None:
            return self._build_result(perception, None, [], None, t0)

        # 检查 RL 策略是否建议替代行动
        best_action = self.rl.get_best_action(perception.behavior)
        if best_action and plan.confidence < 0.8:
            parts = best_action.split(":")
            if len(parts) == 2:
                plan.tools = parts[1].split(",")

        self.state.last_action = plan

        # Phase 3: 工具编排执行 (Tool Orchestrator)
        tool_results = self.tools.execute_plan(plan)

        result = self._build_result(perception, plan, tool_results, None, t0)
        result["awaiting_reaction"] = True
        return result

    def process_reaction(self, post_frame: SensorFrame) -> dict[str, Any]:
        """观察用户对援助的反应，执行 RL 反馈学习。"""
        if self.state.last_perception is None or self.state.last_action is None:
            return {"error": "no prior action to evaluate"}

        post_perception = self.perception.perceive(post_frame)
        tool_results = self.tools.get_history()[-len(self.state.last_action.tools):]

        reward = self.rl.observe_reaction(
            self.state.last_perception,
            post_perception,
            self.state.last_action,
            tool_results,
        )

        self.memory.record_feedback(reward, self.state.last_action.need.value)
        self.memory.apply_forgetting()
        self.state.total_rewards += reward.value

        return {
            "reward": reward.value,
            "reward_source": reward.source,
            "reflections": self.rl.reflections[-1:] if reward.value < 0 else [],
            "policy_updates": len(self.rl.policy_table),
            "profile_summary": {
                "patterns": len(self.memory.profile.behavior_patterns),
                "feedback_count": len(self.memory.profile.feedback_history),
            },
        }

    def _build_result(
        self,
        perception: PerceptionOutput,
        plan: Any,
        tool_results: list,
        reward: Any,
        t0: float,
    ) -> dict[str, Any]:
        elapsed_ms = (time.time() - t0) * 1000
        return {
            "cycle": self.state.cycle_count,
            "latency_ms": round(elapsed_ms, 2),
            "perception": {
                "behavior": perception.behavior,
                "context": perception.context,
                "emotion": perception.emotion.value,
                "confidence": round(perception.confidence, 3),
            },
            "action": {
                "need": plan.need.value if plan else None,
                "tools": plan.tools if plan else [],
                "confidence": round(plan.confidence, 3) if plan else 0,
                "fast_track": plan.fast_track if plan else False,
            } if plan else None,
            "tool_results": [
                {"tool": r.tool_name, "success": r.success, "output": r.output, "latency_ms": round(r.latency_ms, 2)}
                for r in tool_results
            ],
            "reward": reward.value if reward else None,
        }
