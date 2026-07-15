# Track-C 提交打包指南

## 压缩包命名

```
TrackC-成员1编号+姓名-成员2编号+姓名-成员3编号+姓名.zip
```

示例：`TrackC-20260001张三-20260002李四-20260003王五.zip`

## 解压后目录结构

```
TrackC-20260001张三-20260002李四-20260003王五/
├── C1/
│   └── compiler/
│       ├── aec-cc              # 编译器入口（必需）
│       └── src/                # 源码目录
├── C2/
│   ├── libaec.so               # Runtime 动态库（必需）
│   └── agents/                 # Agent 评分（可选）
│       ├── dma_agent.py
│       └── kernel_agent.py
└── C3/
    ├── pa_scheduler.py         # 框架源码
    ├── infer_worker.py         # C3.5 推理入口
    └── readme.md               # 命令模板说明
```

## 一键打包

```bash
cd /Users/jel/PA-SoC-Agentic4Systems

# 替换为真实队员信息
export TRACKC_MEMBERS="20260001张三-20260002李四-20260003王五"

# C2 需在 Linux x86-64 构建 libaec.so（评测环境为 Linux）
bash runtime/setup_starter_kit.sh
make -C runtime

# 若在本机构建失败，可指定已构建的 libaec.so 路径
# export LIBAEC_SO=/path/to/libaec.so

bash scripts/pack_trackc_submission.sh
```

输出：`dist/TrackC-<成员信息>.zip`

## 各子任务路径对照

| 规范路径 | 本仓库来源 |
|----------|-----------|
| `C1/compiler/aec-cc` | `trackc_submission/C1/compiler/aec-cc` |
| `C1/compiler/src/` | `trackc_submission/C1/compiler/src/` |
| `C2/libaec.so` | `runtime/libaec.so`（Linux 构建） |
| `C2/agents/dma_agent.py` | `agents/dma_agent.py` |
| `C2/agents/kernel_agent.py` | `agents/kernel_agent.py` |
| `C3/pa_scheduler.py` | `software/scheduler/pa_scheduler.py` |
| `C3/infer_worker.py` | `trackc_submission/C3/infer_worker.py` |
| `C3/readme.md` | `trackc_submission/C3/readme.md` |

## C3 readme.md 命令模板

**C3.1**
```
python3 pa_scheduler.py --onnx {onnx} --output {output}
```

**C3.5**
```
python3 infer_worker.py --onnx {onnx} --input {input} --output {output} --batch-size 256
```

## 注意事项

1. **C1** 当前为骨架实现，提交前需完善 PTX → AEC 编译能力。
2. **C2** `libaec.so` 必须链接 Linux 版 `libaec_device.so`，请在 Linux 或 Docker 中构建。
3. **C3** 推理依赖 `onnxruntime`，提交前请用公开 testdata 自测。
