# PA-SoC：主动型智能体加速芯片

> 基于 [Agentic4Systems GPGPU 智能体加速设计竞赛 2026](https://github.com/ephonic/Agentic4SystemSummerSchoolContest) 的 AEC ISA，将主动型智能体（Proactive Agent）完整认知闭环映射到 GPGPU 硬件加速流水线。

## 架构映射

| PA-SoC 子系统 | AEC GPGPU 实现 | 竞赛赛道 |
|--------------|---------------|---------|
| 感知前端 (AOP Island) | `pa_aop_controller.v` + VAD/运动检测 kernel | Track-B RTL |
| 多模态分析引擎 | MFU Cross-Attention + SLM GEMM kernel | Track-C C3 |
| 推理决策引擎 | LLM KV-Cache SRAM + 投机解码 kernel | Track-B/C |
| 记忆子系统 | PMEM 画像存储 + HNSW 向量检索 kernel | Track-C C2 |
| 工具编排引擎 | DMA Agent + Kernel Agent 调度 | Track-C C2 |
| 反馈学习引擎 | 在线 LoRA 更新 + Replay Buffer | Track-C C1 |

## 快速开始

```bash
# 安装依赖
pip install -r software/requirements.txt

# 运行主动型智能体端到端仿真
python examples/proactive_agent_demo.py

# 运行单元测试
python -m pytest tests/ -v

# 构建 CModel
cd cmodel && make && ./pa_cmodel_demo

# RTL 仿真（需 Verilator）
cd scripts && make sim
```

## 目录结构

```
PA-SoC-Agentic4Systems/
├── rtl/                    # PA-SoC 扩展 RTL（基于 AEC GPGPU）
├── cmodel/                 # 功能 CModel
├── software/
│   ├── pa_sdk/             # 主动智能体 SDK
│   ├── agents/             # 竞赛 Agent 接口实现
│   ├── scheduler/          # ONNX 算子调度（C3）
│   └── runtime/            # AEC Runtime 封装（C2）
├── kernels/                # AEC kernel 定义
├── tests/                  # 测试用例
├── examples/               # 端到端演示
├── scripts/                # 构建与仿真脚本
└── reports/                # 设计报告
```

## 原创性声明

本项目使用 LLM 辅助生成架构设计与代码框架，所有实现均可复现与维护。
第三方依赖：numpy, onnx（可选，用于 C3 图解析）。

## 许可证

MIT
