# PA-SoC：主动型智能体加速芯片
> 基于 [Agentic4Systems GPGPU 竞赛 2026](https://github.com/ephonic/Agentic4SystemSummerSchoolContest) 的 AEC ISA
> 
> **仓库：** https://github.com/proactiveaiagent/PA-SoC-Agentic4Systems

当前的智能体（AI Agent）多属被动响应型，需用户明确指令后方可行动。基于多模态大模型与具身智能的主动型智能体能够在无需用户明确请求的情况下主动识别和推断用户的潜在需求，并即时调用工具，提供相应的援助来满足用户的需求。相比之下，主动型智能体具备更高的便捷性、效率与智能化水平，在日常生活、康养养老、居家护理、生产办公等领域具有广泛应用前景。此项目实现一个专门为主动型智能体优化的芯片，支持主动型智能体更好地完成以下操作：
1. 通过摄像头等传感器实时捕捉用户的多模态数据，给多模态大模型进行实时分析识别
2. 分析识别结果给推理大模型进行建模，预测判断用户的潜在需求，然后调用相应的工具服务满足用户的需求，给用户提供援助
3. 构建用户画像，存储在memory里，并且通过分析识别用户的所作所为更新用户画像，用于更好地进行需求识别判断和满足
4. 观察用户得到所提供支持援助后的反应，判断提供的支持援助是否正确，正确通过强化学习进行强化，不正确自我修改完善



## 架构

```
传感器 → AOP 感知岛 (RTL) → MM-Engine (AEC Kernel)
       → 推理引擎 → 记忆子系统 → 工具编排 → RL 反馈
```

## 官方 testcases 回归

```bash
# 初始化用例（优先网络下载官方 36 用例，离线时使用 bundled）
bash scripts/setup_testcases.sh

# 运行全部公开用例回归
python3 tests/regression/run_regression.py

# 单个用例
python3 tests/regression/run_regression.py --case abi/c0_smoke

# 竞赛标准入口
bash scripts/run_tests.sh --suite public --output evidence/regression
```

回归报告输出至 `evidence/regression/regression_report.json`。

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
