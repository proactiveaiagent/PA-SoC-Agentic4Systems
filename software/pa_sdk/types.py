"""PA-SoC 核心数据类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Emotion(str, Enum):
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    HAPPY = "happy"
    CONFUSED = "confused"
    FOCUSED = "focused"


class NeedType(str, Enum):
    CODE_HELP = "code_help"
    INFO_SEARCH = "info_search"
    REMINDER = "reminder"
    COMFORT = "comfort"
    NONE = "none"


@dataclass
class SensorFrame:
    """多模态传感器帧。"""
    timestamp: float
    video_features: list[float]       # VPU 输出特征向量
    audio_features: list[float]       # APU 输出特征向量
    imu_motion: float = 0.0
    proximity: float = 0.0


@dataclass
class PerceptionOutput:
    """MM-Engine 结构化感知输出。"""
    timestamp: float
    user_state: dict[str, Any]
    behavior: str
    context: str
    confidence: float
    emotion: Emotion = Emotion.NEUTRAL
    attention_target: str = "unknown"


@dataclass
class BehaviorPattern:
    trigger: str
    likely_need: NeedType
    weight: float = 1.0
    success_count: int = 0
    fail_count: int = 0


@dataclass
class UserProfile:
    """记忆子系统用户画像。"""
    user_id: str
    preferences: dict[str, Any] = field(default_factory=dict)
    behavior_patterns: list[BehaviorPattern] = field(default_factory=list)
    skill_profile: dict[str, float] = field(default_factory=dict)
    feedback_history: list[dict[str, Any]] = field(default_factory=list)
    embedding: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "preferences": self.preferences,
            "behavior_patterns": [
                {
                    "trigger": p.trigger,
                    "likely_need": p.likely_need.value,
                    "weight": p.weight,
                    "success_count": p.success_count,
                    "fail_count": p.fail_count,
                }
                for p in self.behavior_patterns
            ],
            "skill_profile": self.skill_profile,
            "feedback_history": self.feedback_history,
            "embedding": self.embedding,
        }


@dataclass
class ActionPlan:
    """推理决策引擎输出的行动计划。"""
    need: NeedType
    tools: list[str]
    params: dict[str, Any]
    confidence: float
    fast_track: bool = False


@dataclass
class ToolResult:
    tool_name: str
    success: bool
    output: Any
    latency_ms: float


@dataclass
class RewardSignal:
    """RL Engine 奖励信号。"""
    value: float
    source: str
    action_id: str
    timestamp: float


@dataclass
class AgentState:
    """主动智能体全局状态。"""
    profile: UserProfile
    last_perception: PerceptionOutput | None = None
    last_action: ActionPlan | None = None
    cycle_count: int = 0
    total_rewards: float = 0.0
