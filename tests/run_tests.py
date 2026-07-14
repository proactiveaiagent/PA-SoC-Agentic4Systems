#!/usr/bin/env python3
"""轻量测试运行器（无需 pytest）。"""

import sys
import os
import json
import subprocess
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "software"))

from pa_sdk.pipeline import ProactiveAgentPipeline
from pa_sdk.perception import MultimodalPerceptionEngine
from pa_sdk.memory import MemorySubsystem
from pa_sdk.rl import RLEngine
from pa_sdk.types import SensorFrame, Emotion, NeedType, ActionPlan
from pa_sdk.tools import ToolOrchestrator
from pa_sdk.reasoning import ReasoningEngine
from scheduler.pa_scheduler import SchedulerStrategy, GraphNode, HardwareProfile


def _frame(behavior: str) -> SensorFrame:
    stuck_audio = ([0.9, 0.1, 0.8, 0.2, 0.85, 0.15, 0.75, 0.25] * 8)[:64]
    hints = {
        "stuck": ([0.9] * 64, stuck_audio, 0.3),
        "scroll": ([0.7] * 64, [0.1] * 64, 0.2),
        "normal": ([0.5] * 64, [0.3] * 64, 0.4),
    }
    v, a, m = hints.get(behavior, hints["normal"])
    return SensorFrame(timestamp=1.0, video_features=v, audio_features=a, imu_motion=m)


passed = 0
failed = 0
errors = []


def test(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  PASS  {name}")
    except Exception as e:
        failed += 1
        errors.append((name, str(e)))
        print(f"  FAIL  {name}: {e}")


def main():
    print("=" * 50)
    print("  PA-SoC 测试套件")
    print("=" * 50)

    # Perception
    test("perception: stuck coding", lambda: (
        MultimodalPerceptionEngine().perceive(_frame("stuck")).behavior
        == "repeated_typing_errors"
        or (_ for _ in ()).throw(AssertionError("wrong behavior"))
    ))
    out = MultimodalPerceptionEngine().perceive(_frame("stuck"))
    test("perception: emotion frustrated", lambda: out.emotion == Emotion.FRUSTRATED or (_ for _ in ()).throw(AssertionError(out.emotion)))
    test("perception: scrolling", lambda: MultimodalPerceptionEngine().perceive(_frame("scroll")).behavior == "repeated_scroll")

    # Memory
    def _mem_test():
        mem = MemorySubsystem("test_user")
        eng = MultimodalPerceptionEngine()
        p = eng.perceive(_frame("stuck"))
        mem.store_perception(p)
        mem.update_profile_from_perception(p)
        assert len(mem.query_relevant_patterns("repeated_typing_errors")) >= 1
    test("memory: profile update", _mem_test)

    # Reasoning
    def _reason_test():
        mem = MemorySubsystem("test_user")
        eng = MultimodalPerceptionEngine()
        r = ReasoningEngine(help_threshold=0.5)
        p = eng.perceive(_frame("stuck"))
        plan = r.predict_need(p, mem)
        assert plan is not None
        assert plan.need == NeedType.CODE_HELP
        assert "code_search" in plan.tools
    test("reasoning: code help", _reason_test)

    # Tools
    def _tool_test():
        orch = ToolOrchestrator()
        plan = ActionPlan(NeedType.CODE_HELP, ["code_search", "show_example"], {"style": "concise"}, 0.8)
        results = orch.execute_plan(plan)
        assert len(results) == 2 and all(r.success for r in results)
    test("tools: execute plan", _tool_test)

    # RL
    def _rl_pos():
        rl = RLEngine()
        eng = MultimodalPerceptionEngine()
        pre, post = eng.perceive(_frame("stuck")), eng.perceive(_frame("normal"))
        plan = ActionPlan(NeedType.CODE_HELP, ["code_search"], {}, 0.8)
        tools = ToolOrchestrator().execute_plan(plan)
        reward = rl.observe_reaction(pre, post, plan, tools)
        assert reward.value > 0
    test("rl: positive reward", _rl_pos)

    def _rl_corr():
        rl = RLEngine()
        ref = rl.correct("repeated_typing_errors", "code_help:code_search")
        assert "correction" in ref.lower()
    test("rl: correction", _rl_corr)

    # Pipeline
    def _e2e():
        agent = ProactiveAgentPipeline("e2e_user")
        r1 = agent.process_sensor_frame(_frame("stuck"))
        assert r1["action"] is not None
        assert r1["action"]["need"] == "code_help"
        r2 = agent.process_reaction(_frame("normal"))
        assert "reward" in r2
    test("pipeline: end-to-end", _e2e)

    # Scheduler
    def _prec():
        s = SchedulerStrategy(HardwareProfile())
        n = GraphNode("softmax", "Softmax", ["in"], ["out"])
        assert s.select_precision(n, [n]).precision == "fp32"
    test("scheduler: fp32 sensitive ops", _prec)

    def _decomp():
        s = SchedulerStrategy()
        n = GraphNode("sm", "Softmax", ["in"], ["out"])
        refs = s.decompose(n, [n], s.select_precision(n, [n]))
        names = [r.kernel_name for r in refs]
        assert "reduce_max" in names and "div" in names
    test("scheduler: softmax decompose", _decomp)

    def _tune():
        s = SchedulerStrategy()
        n = GraphNode("mm", "Gemm", ["a", "b"], ["c"])
        refs = s.decompose(n, [n], s.select_precision(n, [n]))
        t = s.tune_kernel(refs[0], s.select_precision(n, [n]), {"n": 256})
        assert t.block_x > 0 and t.grid_x > 0
    test("scheduler: tune params", _tune)

    # Agents
    def _dma():
        script = os.path.join(os.path.dirname(__file__), "..", "software", "agents", "dma_agent.py")
        inp = json.dumps({"case_id": 1, "direction": "h2d", "bytes": 4096, "alignment": 64, "registered": True, "concurrency": 2})
        r = subprocess.run(["python3", script], input=inp, capture_output=True, text=True)
        out = json.loads(r.stdout)
        assert out["use_zero_copy"] is True
    test("agent: dma", _dma)

    def _kernel():
        script = os.path.join(os.path.dirname(__file__), "..", "software", "agents", "kernel_agent.py")
        inp = json.dumps({
            "case_id": 1, "dtype": "f16", "m": 128, "n": 128, "k": 128,
            "alignment": 16, "workspace": 8192,
            "candidates": [
                {"id": "c1", "semantic_kernel_id": 10, "variant": 1, "workspace": 4096, "divisibility": 8},
                {"id": "c2", "semantic_kernel_id": 12, "variant": 3, "workspace": 4096, "divisibility": 8},
            ],
        })
        r = subprocess.run(["python3", script], input=inp, capture_output=True, text=True)
        out = json.loads(r.stdout)
        assert out["kernel_id"] == "c2"
    test("agent: kernel", _kernel)

    print("=" * 50)
    print(f"  结果: {passed} passed, {failed} failed")
    print("=" * 50)
    if errors:
        for name, err in errors:
            print(f"  - {name}: {err}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
