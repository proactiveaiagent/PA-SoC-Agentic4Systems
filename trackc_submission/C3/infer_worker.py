#!/usr/bin/env python3
"""C3.5 端到端推理入口。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def _load_inputs(input_dir: Path) -> dict[str, np.ndarray]:
    manifest = json.loads((input_dir / "manifest.json").read_text())
    tensors: dict[str, np.ndarray] = {}
    for item in manifest.get("tensors", []):
        tensors[item["name"]] = np.load(input_dir / item["file"])
    return tensors


def _write_outputs(output_dir: Path, name: str, arr: np.ndarray) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{name}.npy"
    np.save(output_dir / fname, arr.astype(np.float32))
    manifest = {
        "tensors": [
            {
                "name": name,
                "file": fname,
                "dtype": "float32",
                "shape": list(arr.shape),
            }
        ]
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))


def _infer_onnx(onnx_path: Path, inputs: dict[str, np.ndarray], batch_size: int | None) -> np.ndarray:
    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise RuntimeError("需要 onnxruntime: pip install onnxruntime") from exc

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name
    x = inputs[next(iter(inputs))]
    if batch_size:
        x = x[:batch_size]
    outputs = sess.run(None, {input_name: x})
    return outputs[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="C3.5 ONNX 推理")
    parser.add_argument("--onnx", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--batch-size", type=int, default=None)
    args = parser.parse_args()

    try:
        inputs = _load_inputs(args.input)
        logits = _infer_onnx(args.onnx, inputs, args.batch_size)
        _write_outputs(args.output, "logits", logits)
    except Exception as exc:
        print(f"infer_worker: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
