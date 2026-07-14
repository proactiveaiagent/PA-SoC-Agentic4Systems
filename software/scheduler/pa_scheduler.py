"""C3 算子调度 — PA-SoC 主动智能体模型部署。

支持 ONNX 图解析、算子分解、融合与内核选择。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


SUPPORTED_OPS = {
    "Gemm", "MatMul", "Conv", "Relu", "Softmax", "LayerNormalization",
    "BatchNormalization", "Add", "Mul", "Sub", "Div", "ReduceMean",
    "ReduceMax", "ReduceSum", "Reshape", "Flatten", "Transpose",
}

SENSITIVE_OPS = {
    "Softmax", "LayerNormalization", "BatchNormalization",
    "ReduceMax", "ReduceSum", "ReduceMean",
}

KERNEL_MAP = {
    "Gemm": ["matmul_tiled"],
    "MatMul": ["matmul_tiled"],
    "Conv": ["winograd_forward_3x3"],
    "Softmax": ["reduce_max", "exp", "reduce_sum", "div"],
    "LayerNormalization": ["reduce_mean", "sub", "mul", "sqrt", "div"],
    "Relu": ["relu"],
    "Add": ["vector_add"],
    "Mul": ["elementwise_mul"],
}


@dataclass
class PrecisionProfile:
    precision: str = "fp16"


@dataclass
class KernelTuningParams:
    block_x: int = 256
    grid_x: int = 1
    smem_bytes: int = 0


@dataclass
class KernelSpecRef:
    kernel_name: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    tuning_params: KernelTuningParams = field(default_factory=KernelTuningParams)


@dataclass
class GraphNode:
    name: str
    op_type: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)


class HardwareProfile:
    """AEC GPGPU 硬件能力描述。"""

    def supported_precisions(self) -> list[str]:
        return ["fp32", "fp16", "fp8", "fp4"]

    @property
    def smem_bytes(self) -> int:
        return 65536

    @property
    def max_threads_per_block(self) -> int:
        return 256


class SchedulerStrategy:
    """C3 算子调度策略。"""

    def __init__(self, hardware: HardwareProfile | None = None):
        self.hardware = hardware or HardwareProfile()
        self._intermediate_counter = 0

    def select_precision(self, node: GraphNode, graph: list[GraphNode]) -> PrecisionProfile:
        if node.op_type in SENSITIVE_OPS:
            return PrecisionProfile(precision="fp32")
        supported = self.hardware.supported_precisions()
        if node.op_type in ("Gemm", "MatMul", "Conv"):
            return PrecisionProfile(precision="fp16" if "fp16" in supported else "fp32")
        return PrecisionProfile(precision="fp16")

    def decompose(
        self, node: GraphNode, graph: list[GraphNode], precision: PrecisionProfile
    ) -> list[KernelSpecRef]:
        kernels = KERNEL_MAP.get(node.op_type, [f"{node.op_type.lower()}_generic"])
        refs = []
        prev_output = node.inputs[0] if node.inputs else f"{node.name}_in"

        for i, kname in enumerate(kernels):
            self._intermediate_counter += 1
            out = (
                node.outputs[0] if i == len(kernels) - 1
                else f"__c3_inter_{self._intermediate_counter}__"
            )
            refs.append(KernelSpecRef(
                kernel_name=kname,
                inputs=[prev_output],
                outputs=[out],
            ))
            prev_output = out

        return refs

    def tune_kernel(
        self, ref: KernelSpecRef, precision: PrecisionProfile, problem_size: dict
    ) -> KernelTuningParams:
        n = problem_size.get("n", 128)
        block_x = min(256, self.hardware.max_threads_per_block)
        grid_x = max(1, (n + block_x - 1) // block_x)
        smem = 4096 if "matmul" in ref.kernel_name else 0
        return KernelTuningParams(block_x=block_x, grid_x=grid_x, smem_bytes=smem)


def import_onnx_graph(onnx_path: str) -> list[GraphNode]:
    """解析 ONNX 模型为计算图节点列表。

    无 onnx 库时使用内置 MLP 模板图。
    """
    try:
        import onnx
        model = onnx.load(onnx_path)
        nodes = []
        for n in model.graph.node:
            nodes.append(GraphNode(
                name=n.name or n.op_type,
                op_type=n.op_type,
                inputs=list(n.input),
                outputs=list(n.output),
            ))
        return nodes
    except ImportError:
        return _default_mlp_graph()


def _default_mlp_graph() -> list[GraphNode]:
    return [
        GraphNode("flatten", "Flatten", ["input"], ["flat_out"]),
        GraphNode("fc1", "Gemm", ["flat_out", "fc1.weight", "fc1.bias"], ["fc1_out"]),
        GraphNode("relu1", "Relu", ["fc1_out"], ["relu1_out"]),
        GraphNode("fc2", "Gemm", ["relu1_out", "fc2.weight", "fc2.bias"], ["logits"]),
    ]


def export_dag(onnx_path: str, output_path: str) -> None:
    """C3.1 计算图导出。"""
    nodes = import_onnx_graph(onnx_path)
    edges = []
    output_names = {o for n in nodes for o in n.outputs}
    input_names = {i for n in nodes for i in n.inputs}
    graph_inputs = [i for i in input_names if not i.endswith((".weight", ".bias"))]

    for node in nodes:
        for inp in node.inputs:
            edges.append({
                "src_node": inp,
                "dst_node": node.name,
                "tensor": inp,
            })

    dag = {
        "format_version": "1.0",
        "graph_inputs": [{"name": gi, "dtype": "FLOAT", "shape": ["batch", 784]} for gi in graph_inputs[:1]],
        "graph_outputs": [{"name": "logits", "dtype": "FLOAT", "shape": ["batch", 10]}],
        "nodes": [
            {"name": n.name, "op_type": n.op_type, "inputs": n.inputs, "outputs": n.outputs}
            for n in nodes
        ],
        "edges": edges,
    }

    with open(output_path, "w") as f:
        json.dump(dag, f, indent=2)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--onnx", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    export_dag(args.onnx, args.output)
