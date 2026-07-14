# PA-SoC：主动型智能体加速芯片

> 基于 [Agentic4Systems GPGPU 竞赛 2026](https://github.com/ephonic/Agentic4SystemSummerSchoolContest) 的 AEC ISA

**仓库：** https://github.com/proactiveaiagent/PA-SoC-Agentic4Systems

## 架构

```
传感器 → AOP 感知岛 (RTL) → MM-Engine (AEC Kernel)
       → 推理引擎 → 记忆子系统 → 工具编排 → RL 反馈
```

## 快速开始

```bash
# 1. 主动智能体端到端演示
python3 examples/proactive_agent_demo.py
python3 tests/run_tests.py

# 2. C2 Runtime 集成（需联网获取 starter-kit）
bash runtime/setup_starter_kit.sh
make -C runtime
python3 runtime/pa_aec_bridge.py

# 3. Track-B CModel + RTL
make -C cmodel run
bash scripts/build.sh
make -C scripts sim

# 4. 添加 GitHub Topics
bash scripts/set_github_topics.sh
```

## 目录

| 路径 | 说明 |
|------|------|
| `rtl/aec_eval_top.sv` | Track-B 官方评测顶层 + PA 扩展 |
| `cmodel/aec_interpreter.c` | AEC ISA 功能解释器 |
| `runtime/` | C2 starter-kit 对接 |
| `agents/` | C2 DMA/Kernel/Proactive Agent |
| `software/pa_sdk/` | 主动智能体 SDK |
| `scripts/` | 竞赛标准构建/仿真脚本 |

## Topics

`gpgpu` · `proactive-agent` · `agentic4systems` · `aec-isa` · `chip-design` · `soc` · `ai-agent` · `reinforcement-learning`

## 许可证

MIT
