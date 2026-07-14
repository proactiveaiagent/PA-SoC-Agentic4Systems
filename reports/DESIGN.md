# PA-SoC 设计报告

## 1. 设计概述

PA-SoC（Proactive Agent System-on-Chip）在 [Agentic4Systems GPGPU 竞赛](https://github.com/ephonic/Agentic4SystemSummerSchoolContest) 的 AEC 128-bit ISA 基础上，扩展了主动型智能体所需的五大硬件子系统。

## 2. 架构映射

### 2.1 感知前端 → `pa_aop_controller.v`

- Always-On 低功耗域（<50mW 等效）
- 运动/音频/人脸事件检测
- 事件触发唤醒 AEC GPGPU 主计算域
- 与 AEC `aec_eval_top` 通过 `wake_main_domain` 信号互联

### 2.2 多模态分析 → AEC Kernel 流水线

| Kernel | AEC 指令 | 功能 |
|--------|---------|------|
| `pa_vpu_extract` | GEMM + ReLU | 视觉特征提取 |
| `pa_apu_classify` | ReduceMax + Softmax | 音频情感分类 |
| `pa_mfu_fusion` | TMUL | Cross-Attention 融合 |
| `pa_slm_describe` | GEMM naive | 场景快述 |

### 2.3 推理决策 → 双轨架构

- **快轨**：SLM（1-7B）毫秒级意图初筛，KV-Cache 512MB SRAM
- **深轨**：LLM（7-13B）秒级需求预测，投机解码硬件加速

### 2.4 记忆子系统 → `pa_memory_ctrl.v`

四层记忆映射到 AEC 内存空间：

| 记忆层 | AEC Space | 容量 |
|--------|-----------|------|
| 工作记忆 | SMEM | 64MB/CTA |
| 情景记忆 | GMEM | 4GB |
| 语义记忆 | PMEM | 64GB |
| 程序记忆 | CMEM | 只读 |

### 2.5 工具编排 → C2 Agent 接口

- `dma_agent.py`：DMA 通道/分片/zero-copy 调度
- `kernel_agent.py`：GEMM kernel 候选选择
- `proactive_agent.py`：PA-SoC 阶段资源分配

### 2.6 反馈学习 → `pa_rl_engine.v`

- Replay Buffer：1024 条目片上 SRAM
- 在线 LoRA 更新：rank=8，Q8.8 定点
- 反思触发：负奖励自动生成修正信号

## 3. 微架构选择

- **Warp Scheduler**：优先级调度，感知阶段 warp 优先
- **Register Banking**：4-bank 避免感知/推理端口冲突
- **Cache**：GMEM 128B line，16 outstanding，32 cycle latency（遵循 AEC spec）
- **Scoreboard**：工具并发执行乱序完成

## 4. 与 AEC ISA 的关系

所有 PA 扩展模块通过 MMIO 寄存器与标准 AEC GPGPU 交互，不修改 AEC 128-bit 指令格式。PA 专用操作通过自定义 CSR（Control Status Register）触发：

| CSR 地址 | 功能 |
|---------|------|
| 0xPA00 | AOP 事件状态 |
| 0xPA01 | 记忆读写命令 |
| 0xPA02 | RL 奖励输入 |
| 0xPA03 | 工具编排启动 |

## 5. 性能预估

| 阶段 | 延迟 | 算力需求 |
|------|------|---------|
| 感知 | <15ms | 128 TOPS INT8 |
| 快轨推理 | <20ms | 32 TOPS |
| 深轨推理 | <50ms | 72 TOPS |
| 工具执行 | <200ms | DMA + CPU |
| RL 更新 | <10ms | LoRA rank=8 |

端到端：感知到首次援助 <200ms。
