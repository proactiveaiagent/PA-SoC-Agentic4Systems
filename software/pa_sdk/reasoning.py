"""推理决策引擎 — 双轨快慢推理与需求预测。"""

from __future__ import annotations

from .memory import MemorySubsystem
from .types import ActionPlan, NeedType, PerceptionOutput


NEED_RULES: dict[str, dict] = {
    "repeated_typing_errors": {
        "need": NeedType.CODE_HELP,
        "tools": ["code_search", "show_example"],
        "params": {"style": "concise"},
        "fast_track": True,
    },
    "repeated_scroll": {
        "need": NeedType.INFO_SEARCH,
        "tools": ["web_search", "summarize"],
        "params": {"max_results": 3},
        "fast_track": True,
    },
    "long_pause": {
        "need": NeedType.REMINDER,
        "tools": ["gentle_prompt"],
        "params": {"tone": "supportive"},
        "fast_track": False,
    },
    "head_down": {
        "need": NeedType.INFO_SEARCH,
        "tools": ["highlight_text", "define_term"],
        "params": {},
        "fast_track": True,
    },
}


class ReasoningEngine:
    """推理决策引擎：快轨 SLM + 深轨 LLM 协同。

    硬件映射：
    - 快轨: pa_slm_intent_classify (GEMM + Softmax, <20ms)
    - 深轨: pa_llm_need_predict   (GEMM tiled + KV-Cache SRAM)
    - 规划: pa_planner_action_seq  (控制流 + 工具调度)
    """

    def __init__(self, help_threshold: float = 0.6):
        self.help_threshold = help_threshold

    def predict_need(
        self,
        perception: PerceptionOutput,
        memory: MemorySubsystem,
    ) -> ActionPlan | None:
        """双轨推理：快轨初筛 → 深轨确认 → 生成行动计划。"""
        if perception.confidence < self.help_threshold:
            return None

        # 快轨：规则 + 画像模式匹配
        fast_plan = self._fast_track(perception, memory)
        if fast_plan and fast_plan.fast_track:
            return fast_plan

        # 深轨：结合历史与画像深度推理
        return self._deep_track(perception, memory)

    def _fast_track(
        self, perception: PerceptionOutput, memory: MemorySubsystem
    ) -> ActionPlan | None:
        rule = NEED_RULES.get(perception.behavior)
        if not rule:
            return None

        patterns = memory.query_relevant_patterns(perception.behavior)
        confidence = perception.confidence
        if patterns:
            best = patterns[0]
            success_rate = best.success_count / max(best.success_count + best.fail_count, 1)
            confidence = min(confidence * best.weight * (0.5 + 0.5 * success_rate), 1.0)

        style = memory.profile.preferences.get("communication_style", "concise")
        params = {**rule["params"], "style": style}

        return ActionPlan(
            need=rule["need"],
            tools=rule["tools"],
            params=params,
            confidence=confidence,
            fast_track=rule["fast_track"],
        )

    def _deep_track(
        self, perception: PerceptionOutput, memory: MemorySubsystem
    ) -> ActionPlan | None:
        """深轨 LLM 推理：综合情景记忆与反馈历史。"""
        recent = memory.working.get_recent(5)
        negative_recent = sum(
            1 for f in memory.profile.feedback_history[-10:]
            if f.get("outcome") == "negative"
        )

        if negative_recent >= 3:
            return ActionPlan(
                need=NeedType.COMFORT,
                tools=["gentle_prompt"],
                params={"tone": "supportive", "reason": "recent_failures"},
                confidence=0.7,
                fast_track=False,
            )

        if perception.emotion.value == "frustrated" and recent:
            return ActionPlan(
                need=NeedType.CODE_HELP,
                tools=["code_search", "show_example", "explain_concept"],
                params={"detail_level": "step_by_step"},
                confidence=perception.confidence * 0.9,
                fast_track=False,
            )

        return self._fast_track(perception, memory)
