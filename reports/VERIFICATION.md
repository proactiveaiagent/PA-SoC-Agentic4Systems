# PA-SoC 验证报告

## 1. 验证策略

### 1.1 CModel vs RTL 对齐

- `cmodel/pa_cmodel.c` 实现 AOP 和 RL 引擎的功能参考
- 逐周期对比 `pa_aop_controller.v` 和 `pa_rl_engine.v` 的输出
- 对齐标准：event_valid、event_type、reward 信号完全一致

### 1.2 软件栈验证

- `tests/test_pa_soc.py`：28 项单元测试覆盖五大子系统
- 端到端演示 `examples/proactive_agent_demo.py` 验证完整认知闭环

### 1.3 竞赛 Agent 验证

- DMA Agent：JSON stdin/stdout 接口合规
- Kernel Agent：候选集内选择，不越界
- Proactive Agent：阶段资源分配合法性

## 2. 测试覆盖

| 模块 | 测试数 | 覆盖内容 |
|------|--------|---------|
| 感知引擎 | 2 | 行为检测、情感分类 |
| 记忆子系统 | 1 | 画像更新 |
| 推理引擎 | 1 | 需求预测 |
| 工具编排 | 1 | 并发执行 |
| RL 引擎 | 2 | 正向强化、负向修正 |
| 流水线 | 1 | 端到端 |
| 算子调度 | 3 | 精度路由、分解、调优 |
| Agent | 2 | DMA/Kernel JSON 接口 |

## 3. 运行验证

```bash
# CModel
cd cmodel && make run

# 软件测试
python -m pytest tests/ -v

# 端到端演示
python examples/proactive_agent_demo.py
```

## 4. 已知限制

- RTL 模块为功能级实现，未做完整综合 PPA 优化
- 多模态融合使用 numpy 模拟，未连接真实 AEC binary
- ONNX 解析在无 onnx 库时回退到内置 MLP 模板图
