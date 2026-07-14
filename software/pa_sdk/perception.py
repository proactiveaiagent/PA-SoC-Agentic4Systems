"""多模态感知引擎 — 模拟 AEC GPGPU 上的 VPU/APU/MFU 流水线。"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from .types import Emotion, PerceptionOutput, SensorFrame


# 行为模式特征库（硬件中固化在 CMEM）
BEHAVIOR_SIGNATURES: dict[str, dict[str, float]] = {
    "repeated_typing_errors": {"motion": 0.3, "audio_var": 0.33, "video_focus": 0.9},
    "repeated_scroll":        {"motion": 0.2, "audio_var": 0.03, "video_focus": 0.7},
    "long_pause":             {"motion": 0.05, "audio_var": 0.02, "video_focus": 0.5},
    "head_down":              {"motion": 0.1, "audio_var": 0.05, "video_focus": 0.3},
    "normal_work":            {"motion": 0.4, "audio_var": 0.05, "video_focus": 0.5},
}


class MultimodalPerceptionEngine:
    """MM-Engine：在 AEC GPGPU 上执行多模态融合与场景理解。

    硬件映射：
    - VPU kernel: pa_vpu_extract_features  (GEMM + ReLU)
    - APU kernel: pa_apu_audio_classify    (ReduceMax + Softmax)
    - MFU kernel: pa_mfu_cross_attention   (TMUL)
    - SLM kernel: pa_slm_scene_describe    (GEMM naive)
    """

    def __init__(self, feature_dim: int = 64):
        self.feature_dim = feature_dim
        self._fusion_weights = np.random.randn(feature_dim, feature_dim) * 0.01

    def _extract_scalar_features(self, frame: SensorFrame) -> dict[str, float]:
        """从传感器帧提取标量特征（模拟 VPU/APU 硬件输出）。"""
        video = np.array(frame.video_features[: self.feature_dim], dtype=np.float32)
        audio = np.array(frame.audio_features[: self.feature_dim], dtype=np.float32)

        motion = frame.imu_motion
        audio_var = float(np.std(audio)) if len(audio) > 0 else 0.0
        video_focus = float(np.mean(np.abs(video))) if len(video) > 0 else 0.0

        return {"motion": motion, "audio_var": audio_var, "video_focus": video_focus}

    def _cross_attention_fusion(
        self, video: np.ndarray, audio: np.ndarray
    ) -> np.ndarray:
        """MFU Cross-Attention 融合（AEC TMUL 加速）。"""
        v = video.reshape(1, -1)
        a = audio.reshape(1, -1)
        dim = min(v.shape[1], a.shape[1], self._fusion_weights.shape[0])
        v, a = v[:, :dim], a[:, :dim]
        w = self._fusion_weights[:dim, :dim]
        attn = self._softmax(v @ w @ a.T)
        fused = attn @ a + v
        return fused.flatten()

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - np.max(x))
        return e / (e.sum() + 1e-8)

    def _classify_behavior(self, features: dict[str, float]) -> tuple[str, float]:
        """行为分类器（SLM 快轨初筛）。"""
        best_behavior = "normal_work"
        best_score = 0.0

        for behavior, sig in BEHAVIOR_SIGNATURES.items():
            score = 0.0
            for key, target in sig.items():
                actual = features.get(key, 0.0)
                score += 1.0 - abs(actual - target)
            score /= len(sig)
            if score > best_score:
                best_score = score
                best_behavior = behavior

        return best_behavior, best_score

    def _detect_emotion(self, features: dict[str, float], behavior: str) -> Emotion:
        if behavior == "repeated_typing_errors":
            return Emotion.FRUSTRATED
        if behavior == "long_pause":
            return Emotion.CONFUSED
        if features["audio_var"] > 0.25 and behavior != "normal_work":
            return Emotion.FRUSTRATED
        if features["video_focus"] > 0.85 and features["audio_var"] < 0.1:
            return Emotion.FOCUSED
        return Emotion.NEUTRAL

    def _infer_context(self, behavior: str) -> str:
        context_map = {
            "repeated_typing_errors": "coding_in_ide",
            "repeated_scroll": "searching_info",
            "long_pause": "thinking",
            "head_down": "reading",
            "normal_work": "general_work",
        }
        return context_map.get(behavior, "unknown")

    def perceive(self, frame: SensorFrame) -> PerceptionOutput:
        """执行完整多模态感知流水线。"""
        scalar = self._extract_scalar_features(frame)

        video = np.array(frame.video_features[: self.feature_dim], dtype=np.float32)
        audio = np.array(frame.audio_features[: self.feature_dim], dtype=np.float32)
        if len(video) < self.feature_dim:
            video = np.pad(video, (0, self.feature_dim - len(video)))
        if len(audio) < self.feature_dim:
            audio = np.pad(audio, (0, self.feature_dim - len(audio)))

        fused = self._cross_attention_fusion(video, audio)
        _ = fused  # 融合向量供后续 LLM 使用

        behavior, confidence = self._classify_behavior(scalar)
        emotion = self._detect_emotion(scalar, behavior)
        context = self._infer_context(behavior)

        return PerceptionOutput(
            timestamp=frame.timestamp,
            user_state={
                "emotion": emotion.value,
                "attention": scalar["video_focus"],
                "motion_level": scalar["motion"],
            },
            behavior=behavior,
            context=context,
            confidence=confidence,
            emotion=emotion,
            attention_target=context,
        )

    def batch_perceive(self, frames: Sequence[SensorFrame]) -> list[PerceptionOutput]:
        return [self.perceive(f) for f in frames]
