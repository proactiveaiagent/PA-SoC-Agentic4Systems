"""记忆子系统 — 四层记忆架构与用户画像管理。"""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from .types import BehaviorPattern, NeedType, PerceptionOutput, RewardSignal, UserProfile


class WorkingMemory:
    """工作记忆 (SRAM 64MB) — 当前会话上下文。"""

    def __init__(self, max_entries: int = 32):
        self._buffer: list[dict[str, Any]] = []
        self._max = max_entries

    def push(self, entry: dict[str, Any]) -> None:
        self._buffer.append(entry)
        if len(self._buffer) > self._max:
            self._buffer.pop(0)

    def get_recent(self, n: int = 5) -> list[dict[str, Any]]:
        return self._buffer[-n:]

    def clear(self) -> None:
        self._buffer.clear()


class EpisodicMemory:
    """情景记忆 (LPDDR5) — 交互历史事件。"""

    def __init__(self, max_events: int = 1000):
        self._events: list[dict[str, Any]] = []
        self._max = max_events

    def record(self, event: dict[str, Any]) -> None:
        event["recorded_at"] = time.time()
        self._events.append(event)
        if len(self._events) > self._max:
            self._events.pop(0)

    def query_by_behavior(self, behavior: str, limit: int = 10) -> list[dict[str, Any]]:
        return [e for e in reversed(self._events) if e.get("behavior") == behavior][:limit]


class SemanticMemory:
    """语义记忆 (NAND) — 用户画像与长期偏好。"""

    def __init__(self):
        self._profiles: dict[str, UserProfile] = {}

    def get_or_create(self, user_id: str) -> UserProfile:
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(
                user_id=user_id,
                preferences={
                    "communication_style": "concise",
                    "help_threshold": 0.6,
                    "active_hours": [9, 22],
                },
                skill_profile={"coding": 0.5, "design": 0.3},
                embedding=[0.0] * 768,
            )
        return self._profiles[user_id]

    def update_embedding(self, profile: UserProfile, delta: list[float], alpha: float = 0.1) -> None:
        """增量更新用户向量（硬件 Incremental Update Engine）。"""
        emb = np.array(profile.embedding, dtype=np.float32)
        d = np.array(delta[: len(emb)], dtype=np.float32)
        profile.embedding = (emb * (1 - alpha) + d * alpha).tolist()


class VectorSearchEngine:
    """HNSW 向量检索引擎（AEC GPGPU 加速）。"""

    def __init__(self, dim: int = 768):
        self.dim = dim
        self._index: list[tuple[str, np.ndarray]] = []

    def insert(self, key: str, vector: list[float]) -> None:
        v = np.array(vector[: self.dim], dtype=np.float32)
        self._index.append((key, v))

    def search(self, query: list[float], top_k: int = 3) -> list[tuple[str, float]]:
        q = np.array(query[: self.dim], dtype=np.float32)
        scores = []
        for key, vec in self._index:
            sim = float(np.dot(q, vec) / (np.linalg.norm(q) * np.linalg.norm(vec) + 1e-8))
            scores.append((key, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class MemorySubsystem:
    """PA-SoC 记忆子系统完整实现。"""

    FORGET_HALF_LIFE = 86400.0  # 24h 遗忘半衰期

    def __init__(self, user_id: str = "default_user"):
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.vector_search = VectorSearchEngine()
        self.profile = self.semantic.get_or_create(user_id)
        self.vector_search.insert(user_id, self.profile.embedding)

    def store_perception(self, perception: PerceptionOutput) -> None:
        entry = {
            "timestamp": perception.timestamp,
            "behavior": perception.behavior,
            "context": perception.context,
            "emotion": perception.emotion.value,
            "confidence": perception.confidence,
        }
        self.working.push(entry)
        self.episodic.record(entry)

    def update_profile_from_perception(self, perception: PerceptionOutput) -> None:
        """根据感知结果更新用户画像。"""
        trigger = perception.behavior
        existing = {p.trigger: p for p in self.profile.behavior_patterns}

        if trigger in existing:
            pattern = existing[trigger]
            pattern.weight = min(pattern.weight + 0.05, 2.0)
        else:
            need = self._behavior_to_need(trigger)
            self.profile.behavior_patterns.append(
                BehaviorPattern(trigger=trigger, likely_need=need, weight=1.0)
            )

        feature_delta = [perception.confidence] * 768
        self.semantic.update_embedding(self.profile, feature_delta)

    def record_feedback(self, reward: RewardSignal, action_desc: str) -> None:
        self.profile.feedback_history.append({
            "action": action_desc,
            "outcome": "positive" if reward.value > 0 else "negative",
            "reward": reward.value,
            "timestamp": reward.timestamp,
        })
        self._update_pattern_weights(reward, action_desc)

    def _update_pattern_weights(self, reward: RewardSignal, action_desc: str) -> None:
        for pattern in self.profile.behavior_patterns:
            if pattern.trigger in action_desc or pattern.likely_need.value in action_desc:
                if reward.value > 0:
                    pattern.success_count += 1
                    pattern.weight = min(pattern.weight + 0.1 * reward.value, 3.0)
                else:
                    pattern.fail_count += 1
                    pattern.weight = max(pattern.weight + 0.1 * reward.value, 0.1)

    def apply_forgetting(self) -> None:
        """遗忘曲线硬件：衰减低价值记忆。"""
        now = time.time()
        for pattern in self.profile.behavior_patterns:
            recent = [
                f for f in self.profile.feedback_history
                if f.get("action", "").find(pattern.trigger) >= 0
            ]
            if not recent:
                pattern.weight *= 0.99
                continue
            last_ts = max(f["timestamp"] for f in recent)
            age = now - last_ts
            decay = 0.5 ** (age / self.FORGET_HALF_LIFE)
            pattern.weight *= decay

    def query_relevant_patterns(self, behavior: str) -> list[BehaviorPattern]:
        return sorted(
            [p for p in self.profile.behavior_patterns if p.trigger == behavior],
            key=lambda p: p.weight,
            reverse=True,
        )

    @staticmethod
    def _behavior_to_need(behavior: str) -> NeedType:
        mapping = {
            "repeated_typing_errors": NeedType.CODE_HELP,
            "repeated_scroll": NeedType.INFO_SEARCH,
            "long_pause": NeedType.REMINDER,
            "head_down": NeedType.INFO_SEARCH,
        }
        return mapping.get(behavior, NeedType.NONE)
