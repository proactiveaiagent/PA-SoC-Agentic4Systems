"""反馈学习引擎 — 在线 RL + LoRA 自我修正。"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from .types import ActionPlan, PerceptionOutput, RewardSignal, ToolResult


@dataclass
class ExperienceTuple:
    state: dict[str, Any]
    action: str
    reward: float
    next_state: dict[str, Any]
    timestamp: float


@dataclass
class PolicyEntry:
    trigger: str
    action: str
    q_value: float = 0.0
    visit_count: int = 0
    lora_delta: list[float] = field(default_factory=list)


REWARD_TABLE: dict[str, float] = {
    "smile": 0.8,
    "adopt_suggestion": 1.0,
    "say_thanks": 1.0,
    "ignore": -0.5,
    "explicit_reject": -1.0,
    "repeat_problem": -0.7,
    "continue_work": 0.3,
    "read_example": 0.9,
}


class RLEngine:
    """RL 反馈学习引擎。

    硬件映射：
    - Replay Buffer: 256MB SRAM, 10K (s,a,r) 元组
    - LoRA Update Unit: 在线低秩适配器更新
    - Reflection Generator: 失败时触发 LLM 反思
    """

    REPLAY_CAPACITY = 10000
    LEARNING_RATE = 0.1
    LORA_RANK = 8

    def __init__(self):
        self.replay_buffer: deque[ExperienceTuple] = deque(maxlen=self.REPLAY_CAPACITY)
        self.policy_table: dict[str, PolicyEntry] = {}
        self.reflections: list[str] = []
        self.total_reward = 0.0

    def observe_reaction(
        self,
        pre_perception: PerceptionOutput,
        post_perception: PerceptionOutput,
        plan: ActionPlan,
        tool_results: list[ToolResult],
    ) -> RewardSignal:
        """观察用户对援助的反应，计算奖励信号。"""
        reward_value, source = self._evaluate_reaction(
            pre_perception, post_perception, plan, tool_results
        )

        action_id = f"{plan.need.value}:{','.join(plan.tools)}"
        signal = RewardSignal(
            value=reward_value,
            source=source,
            action_id=action_id,
            timestamp=time.time(),
        )

        self._store_experience(pre_perception, plan, reward_value, post_perception)
        self._update_policy(pre_perception.behavior, action_id, reward_value)

        if reward_value < 0:
            reflection = self._generate_reflection(pre_perception, plan, reward_value)
            self.reflections.append(reflection)

        self.total_reward += reward_value
        return signal

    def _evaluate_reaction(
        self,
        pre: PerceptionOutput,
        post: PerceptionOutput,
        plan: ActionPlan,
        results: list[ToolResult],
    ) -> tuple[float, str]:
        if not all(r.success for r in results):
            return -0.5, "tool_failure"

        if pre.emotion.value == "frustrated" and post.emotion.value in ("focused", "neutral"):
            return REWARD_TABLE["adopt_suggestion"], "emotion_improved"

        if pre.behavior == "repeated_typing_errors" and post.behavior == "normal_work":
            return REWARD_TABLE["read_example"], "behavior_normalized"

        if post.behavior == pre.behavior:
            return REWARD_TABLE["repeat_problem"], "no_change"

        if post.emotion.value == "happy":
            return REWARD_TABLE["smile"], "positive_emotion"

        return REWARD_TABLE["continue_work"], "neutral_continue"

    def _store_experience(
        self,
        pre: PerceptionOutput,
        plan: ActionPlan,
        reward: float,
        post: PerceptionOutput,
    ) -> None:
        self.replay_buffer.append(ExperienceTuple(
            state={"behavior": pre.behavior, "emotion": pre.emotion.value},
            action=f"{plan.need.value}:{','.join(plan.tools)}",
            reward=reward,
            next_state={"behavior": post.behavior, "emotion": post.emotion.value},
            timestamp=time.time(),
        ))

    def _update_policy(self, trigger: str, action: str, reward: float) -> None:
        """在线 LoRA 策略更新（Q-learning 简化版）。"""
        key = f"{trigger}::{action}"
        if key not in self.policy_table:
            self.policy_table[key] = PolicyEntry(
                trigger=trigger, action=action,
                lora_delta=[0.0] * self.LORA_RANK,
            )

        entry = self.policy_table[key]
        entry.visit_count += 1
        entry.q_value += self.LEARNING_RATE * (reward - entry.q_value)

        for i in range(self.LORA_RANK):
            entry.lora_delta[i] += self.LEARNING_RATE * reward * 0.01

    def _generate_reflection(
        self, perception: PerceptionOutput, plan: ActionPlan, reward: float
    ) -> str:
        return (
            f"[reflection] trigger={perception.behavior}, "
            f"action={plan.need.value}, reward={reward:.2f}: "
            f"援助未达预期，下次对 '{perception.context}' 场景"
            f"降低 '{plan.tools[0]}' 优先级，尝试替代策略。"
        )

    def get_best_action(self, trigger: str) -> str | None:
        candidates = [
            e for k, e in self.policy_table.items() if e.trigger == trigger
        ]
        if not candidates:
            return None
        best = max(candidates, key=lambda e: e.q_value)
        return best.action if best.q_value > 0 else None

    def reinforce(self, trigger: str, action: str, reward: float) -> None:
        """外部强化接口（对应 pa_reinforce() SDK 调用）。"""
        self._update_policy(trigger, action, reward)

    def correct(self, trigger: str, failed_action: str) -> str:
        """自我修正接口（对应 pa_correct() SDK 调用）。"""
        key = f"{trigger}::{failed_action}"
        if key in self.policy_table:
            self.policy_table[key].q_value -= 0.5
        reflection = (
            f"[correction] 禁用策略 {failed_action} for {trigger}, "
            f"已写入程序记忆。"
        )
        self.reflections.append(reflection)
        return reflection
