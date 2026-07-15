# C3 算子调度提交说明

## C3.1 命令模板

```
python3 pa_scheduler.py --onnx {onnx} --output {output}
```

## C3.5 模型推理启动命令

```
python3 infer_worker.py --onnx {onnx} --input {input} --output {output} --batch-size 256
```

## 依赖

```bash
pip install numpy onnx onnxruntime
```

## 目录说明

| 文件 | 说明 |
|------|------|
| `pa_scheduler.py` | C3.1 DAG 导出 + C3.2/C3.3 调度策略 |
| `infer_worker.py` | C3.5 端到端 ONNX 推理 |
