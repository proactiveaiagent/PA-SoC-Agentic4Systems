"""PA-SoC 单元测试。"""

import sys
import os
import json
import subprocess

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "software"))

from pa_sdk.pipeline import ProactiveAgentPipeline
from pa_sdk.perception import MultimodalPerceptionEngine
from pa_sdk.memory import MemorySubsystem
from pa_sdk.rl import RLEngine
from pa_sdk.types import SensorFrame, Emotion, NeedType
from pa_sdk.tools import ToolOrchestrator
from pa_sdk.reasoning import ReasoningEngine
from scheduler.pa_scheduler import SchedulerStrategy, GraphNode, HardwareProfile, export_dag


def _frame(behavior: str) -> SensorFrame:
    stuck_audio = ([0.9, 0.1, 0.8, 0.2, 0.85, 0.15, 0.75, 0.25] * 8)[:64]
    hints = {
        "stuck": ([0.9] * 64, stuck_audio, 0.3),
        "scroll": ([0.7] * 64, [0.1] * 64, 0.2),
        "normal": ([0.5] * 64, [0.3] * 64, 0.4),
    }
    v, a, m = hints.get(behavior, hints["normal"])
    return SensorFrame(timestamp=1.0, video_features=v, audio_features=a, imu_motion=m)


class TestPerception:
    def test_detect_stuck_coding(self):
        engine = MultimodalPerceptionEngine()
        out = engine.perceive(_frame("stuck"))
        assert out.behavior == "repeated_typing_errors"
        assert out.emotion == Emotion.FRUSTRATED
        assert out.confidence > 0.5

    def test_detect_scrolling(self):
        engine = MultimodalPerceptionEngine()
        out = engine.perceive(_frame("scroll"))
        assert out.behavior == "repeated_scroll"


class TestMemory:
    def test_profile_update(self):
        mem = MemorySubsystem("test_user")
        engine = MultimodalPerceptionEngine()
        out = engine.perceive(_frame("stuck"))
        mem.store_perception(out)
        mem.update_profile_from_perception(out)
        patterns = mem.query_relevant_patterns("repeated_typing_errors")
        assert len(patterns) >= 1


class TestReasoning:
    def test_predict_code_help(self):
        mem = MemorySubsystem("test_user")
        engine = MultimodalPerceptionEngine()
        reasoner = ReasoningEngine(help_threshold=0.5)
        out = engine.perceive(_frame("stuck"))
        plan = reasoner.predict_need(out, mem)
        assert plan is not None
        assert plan.need == NeedType.CODE_HELP
        assert "code_search" in plan.tools


class TestTools:
    def test_execute_plan(self):
        from pa_sdk.types import ActionPlan
        orch = ToolOrchestrator()
        plan = ActionPlan(
            need=NeedType.CODE_HELP,
            tools=["code_search", "show_example"],
            params={"style": "concise"},
            confidence=0.8,
        )
        results = orch.execute_plan(plan)
        assert len(results) == 2
        assert all(r.success for r in results)


class TestRL:
    def test_positive_reward(self):
        rl = RLEngine()
        engine = MultimodalPerceptionEngine()
        pre = engine.perceive(_frame("stuck"))
        post = engine.perceive(_frame("normal"))
        from pa_sdk.types import ActionPlan
        plan = ActionPlan(NeedType.CODE_HELP, ["code_search"], {}, 0.8)
        from pa_sdk.tools import ToolOrchestrator
        tools = ToolOrchestrator()
        tool_results = tools.execute_plan(plan)
        reward = rl.observe_reaction(pre, post, plan, tool_results)
        assert reward.value > 0

    def test_negative_correction(self):
        rl = RLEngine()
        reflection = rl.correct("repeated_typing_errors", "code_help:code_search")
        assert "correction" in reflection.lower()


class TestPipeline:
    def test_end_to_end(self):
        agent = ProactiveAgentPipeline("e2e_user")
        r1 = agent.process_sensor_frame(_frame("stuck"))
        assert r1["action"] is not None
        assert r1["action"]["need"] == "code_help"
        r2 = agent.process_reaction(_frame("normal"))
        assert "reward" in r2


class TestScheduler:
    def test_precision_routing(self):
        hw = HardwareProfile()
        strategy = SchedulerStrategy(hw)
        node = GraphNode("softmax", "Softmax", ["in"], ["out"])
        prec = strategy.select_precision(node, [node])
        assert prec.precision == "fp32"

    def test_decompose_softmax(self):
        strategy = SchedulerStrategy()
        node = GraphNode("sm", "Softmax", ["in"], ["out"])
        refs = strategy.decompose(node, [node], strategy.select_precision(node, [node]))
        names = [r.kernel_name for r in refs]
        assert "reduce_max" in names
        assert "div" in names

    def test_tune_params(self):
        strategy = SchedulerStrategy()
        node = GraphNode("mm", "Gemm", ["a", "b"], ["c"])
        refs = strategy.decompose(node, [node], strategy.select_precision(node, [node]))
        tuning = strategy.tune_kernel(refs[0], strategy.select_precision(node, [node]), {"n": 256})
        assert tuning.block_x > 0
        assert tuning.grid_x > 0


class TestAgents:
    def test_dma_agent(self):
        script = os.path.join(os.path.dirname(__file__), "..", "software", "agents", "dma_agent.py")
        inp = json.dumps({"case_id": 1, "direction": "h2d", "bytes": 4096, "alignment": 64, "registered": True, "concurrency": 2})
        result = subprocess.run(["python3", script], input=inp, capture_output=True, text=True)
        out = json.loads(result.stdout)
        assert "channel" in out
        assert out["use_zero_copy"] is True

    def test_kernel_agent(self):
        script = os.path.join(os.path.dirname(__file__), "..", "software", "agents", "kernel_agent.py")
        inp = json.dumps({
            "case_id": 1, "dtype": "f16", "m": 128, "n": 128, "k": 128,
            "alignment": 16, "workspace": 8192,
            "candidates": [
                {"id": "c1", "semantic_kernel_id": 10, "variant": 1, "workspace": 4096, "divisibility": 8},
                {"id": "c2", "semantic_kernel_id": 12, "variant": 3, "workspace": 4096, "divisibility": 8},
            ],
        })
        result = subprocess.run(["python3", script], input=inp, capture_output=True, text=True)
        out = json.loads(result.stdout)
        assert out["kernel_id"] == "c2"
