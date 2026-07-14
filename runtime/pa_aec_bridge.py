"""PA-SoC ↔ AEC Runtime 桥接层。

将主动智能体流水线的计算阶段映射到 libaec.so kernel 调用。
"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STARTER_KIT = ROOT / "third_party" / "starter-kit"
RUNTIME_LIB = ROOT / "runtime" / "libaec.so"


class AECRuntimeBridge:
    """Python 桥接：加载 libaec.so 并调用 GPGPU kernel。"""

    def __init__(self, lib_path: str | None = None):
        lib = lib_path or str(RUNTIME_LIB)
        if not os.path.exists(lib):
            raise FileNotFoundError(
                f"libaec.so 未找到: {lib}\n"
                f"请先运行: bash runtime/setup_starter_kit.sh && make -C runtime"
            )
        self._lib = ctypes.CDLL(lib)
        self._setup_signatures()

    def _setup_signatures(self) -> None:
        self._lib.aecDeviceCount.argtypes = [ctypes.POINTER(ctypes.c_int)]
        self._lib.aecDeviceCount.restype = ctypes.c_int
        self._lib.aecMatmulF32.argtypes = [
            ctypes.c_uint64, ctypes.c_uint64, ctypes.c_uint64,
            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        self._lib.aecMatmulF32.restype = ctypes.c_int

    def device_count(self) -> int:
        count = ctypes.c_int(0)
        err = self._lib.aecDeviceCount(ctypes.byref(count))
        if err != 0:
            raise RuntimeError(f"aecDeviceCount failed: {err}")
        return count.value

    def matmul_f32(
        self, a: int, b: int, c: int, m: int, n: int, k: int
    ) -> None:
        err = self._lib.aecMatmulF32(
            ctypes.c_uint64(a), ctypes.c_uint64(b), ctypes.c_uint64(c),
            ctypes.c_uint32(m), ctypes.c_uint32(n), ctypes.c_uint32(k),
            None,
        )
        if err != 0:
            raise RuntimeError(f"aecMatmulF32 failed: {err}")

    def offload_perception_gemm(self, m: int, n: int, k: int) -> dict[str, Any]:
        """主动智能体感知阶段：将 MFU Cross-Attention 卸载到 AEC GEMM。"""
        a = ctypes.c_uint64(0x10000)
        b = ctypes.c_uint64(0x20000)
        c = ctypes.c_uint64(0x30000)
        self.matmul_f32(a.value, b.value, c.value, m, n, k)
        return {
            "phase": "perception",
            "kernel": "aecMatmulF32",
            "shape": [m, n, k],
            "device": "PA-SoC AEC Virtual GPGPU",
        }


def ensure_runtime_ready() -> None:
    setup = ROOT / "runtime" / "setup_starter_kit.sh"
    if not STARTER_KIT.exists() and setup.exists():
        os.system(f"bash {setup}")


if __name__ == "__main__":
    ensure_runtime_ready()
    try:
        bridge = AECRuntimeBridge()
        print(f"设备数: {bridge.device_count()}")
        print(bridge.offload_perception_gemm(64, 64, 64))
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
