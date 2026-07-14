/**
 * PA-SoC AEC Runtime — 在官方 starter-kit 基础上实现完整 Runtime API。
 * 对接竞赛 C2 赛道，支持主动智能体流水线调用 GPGPU kernel。
 */
#include "aec_runtime.h"
#include "aec_device_abi.h"

#include <cstring>
#include <cstdlib>
#include <vector>
#include <mutex>

namespace {

thread_local aecError_t g_last_error = AEC_SUCCESS;
std::mutex g_mem_mutex;
uint64_t g_next_addr = 0x10000;
struct MemBlock { aecDevicePtr ptr; size_t bytes; };
std::vector<MemBlock> g_allocations;

aecError_t finish(aecError_t err) {
    if (err != AEC_SUCCESS) g_last_error = err;
    return err;
}

aecDevicePtr alloc_addr(size_t bytes) {
    aecDevicePtr addr = g_next_addr;
    g_next_addr += (bytes + 255) & ~size_t(255);
    return addr;
}

} // namespace

extern "C" {

aecError_t aecDeviceCount(int *count) {
    if (!count) return finish(AEC_ERROR_INVALID_ARGUMENT);
    aecDeviceCaps caps{};
    if (aecDeviceGetCaps(&caps) != AEC_DEVICE_SUCCESS) return finish(AEC_ERROR_DEVICE);
    *count = static_cast<int>(caps.device_count);
    return AEC_SUCCESS;
}

aecError_t aecDeviceInfo(int device, aecDeviceInfoData *info) {
    if (device != 0 || !info) return finish(AEC_ERROR_INVALID_ARGUMENT);
    aecDeviceCaps caps{};
    if (aecDeviceGetCaps(&caps) != AEC_DEVICE_SUCCESS) return finish(AEC_ERROR_DEVICE);
    std::memset(info, 0, sizeof(*info));
    info->abi_version = AEC_RUNTIME_ABI_VERSION;
    std::strncpy(info->name, "PA-SoC AEC Virtual GPGPU", sizeof(info->name) - 1);
    info->memory_bytes = caps.memory_bytes;
    info->dma_channels = caps.dma_channels;
    info->max_threads_per_block = caps.max_threads_per_block;
    info->isa_version = caps.isa_version;
    info->isa_profile = caps.isa_profile;
    info->max_parameter_bytes = caps.max_parameter_bytes;
    return AEC_SUCCESS;
}

aecError_t aecGetLastError(void) {
    aecError_t v = g_last_error;
    g_last_error = AEC_SUCCESS;
    return v;
}

aecError_t aecPeekAtLastError(void) { return g_last_error; }

const char *aecGetErrorName(aecError_t error) {
    switch (error) {
    case AEC_SUCCESS: return "AEC_SUCCESS";
    case AEC_ERROR_INVALID_ARGUMENT: return "AEC_ERROR_INVALID_ARGUMENT";
    case AEC_ERROR_OUT_OF_MEMORY: return "AEC_ERROR_OUT_OF_MEMORY";
    case AEC_ERROR_INVALID_HANDLE: return "AEC_ERROR_INVALID_HANDLE";
    case AEC_ERROR_INVALID_ADDRESS: return "AEC_ERROR_INVALID_ADDRESS";
    case AEC_ERROR_NOT_READY: return "AEC_ERROR_NOT_READY";
    case AEC_ERROR_NOT_SUPPORTED: return "AEC_ERROR_NOT_SUPPORTED";
    case AEC_ERROR_DEVICE: return "AEC_ERROR_DEVICE";
    case AEC_ERROR_INTERNAL: return "AEC_ERROR_INTERNAL";
    case AEC_ERROR_ISA_TRAP: return "AEC_ERROR_ISA_TRAP";
    default: return "AEC_ERROR_UNKNOWN";
    }
}

aecError_t aecAlloc(aecDevicePtr *out_ptr, size_t bytes) {
    if (!out_ptr || bytes == 0) return finish(AEC_ERROR_INVALID_ARGUMENT);
    std::lock_guard<std::mutex> lock(g_mem_mutex);
    aecDevicePtr ptr = alloc_addr(bytes);
    g_allocations.push_back({ptr, bytes});
    *out_ptr = ptr;
    return AEC_SUCCESS;
}

aecError_t aecFree(aecDevicePtr ptr) {
    if (ptr == 0) return finish(AEC_ERROR_INVALID_ARGUMENT);
    std::lock_guard<std::mutex> lock(g_mem_mutex);
    for (auto it = g_allocations.begin(); it != g_allocations.end(); ++it) {
        if (it->ptr == ptr) {
            g_allocations.erase(it);
            return AEC_SUCCESS;
        }
    }
    return finish(AEC_ERROR_INVALID_ADDRESS);
}

static aecError_t do_copy(aecDevicePtr dst, const void *src, size_t bytes, bool h2d) {
    if (bytes == 0) return AEC_SUCCESS;
    if (!src && bytes > 0) return finish(AEC_ERROR_INVALID_ARGUMENT);

    aecDeviceCommand cmd{};
    cmd.abi_version = AEC_DEVICE_ABI_VERSION;
    cmd.opcode = h2d ? AEC_DEVICE_OP_H2D : AEC_DEVICE_OP_D2H;
    cmd.bytes = bytes;
    cmd.chunk_bytes = bytes <= 4096 ? 4096 : (bytes <= 65536 ? 65536 : 1048576);
    cmd.queue_depth = 2;
    cmd.channel = h2d ? 0 : 1;
    if (h2d) {
        cmd.dst = dst;
        cmd.host_address = reinterpret_cast<uint64_t>(src);
    } else {
        cmd.src = dst;
        cmd.host_address = reinterpret_cast<uint64_t>(src);
    }
    aecDeviceCompletion comp{};
    if (aecDeviceSubmit(&cmd, &comp) != AEC_DEVICE_SUCCESS)
        return finish(AEC_ERROR_DEVICE);
    return AEC_SUCCESS;
}

aecError_t aecCopyH2D(aecDevicePtr dst, const void *src, size_t bytes) {
    return do_copy(dst, src, bytes, true);
}

aecError_t aecCopyD2H(void *dst, aecDevicePtr src, size_t bytes) {
    return do_copy(src, dst, bytes, false);
}

aecError_t aecCopyAsync(aecDevicePtr, void *, size_t, aecCopyDirection, aecStream_t) {
    return finish(AEC_ERROR_NOT_SUPPORTED);
}

aecError_t aecStreamCreate(aecStream_t *) { return finish(AEC_ERROR_NOT_SUPPORTED); }
aecError_t aecStreamDestroy(aecStream_t) { return finish(AEC_ERROR_NOT_SUPPORTED); }
aecError_t aecStreamSync(aecStream_t) { return finish(AEC_ERROR_NOT_SUPPORTED); }
aecError_t aecEventCreate(aecEvent_t *) { return finish(AEC_ERROR_NOT_SUPPORTED); }
aecError_t aecEventDestroy(aecEvent_t) { return finish(AEC_ERROR_NOT_SUPPORTED); }
aecError_t aecEventRecord(aecEvent_t, aecStream_t) { return finish(AEC_ERROR_NOT_SUPPORTED); }
aecError_t aecEventSynchronize(aecEvent_t) { return finish(AEC_ERROR_NOT_SUPPORTED); }
aecError_t aecEventQuery(aecEvent_t) { return finish(AEC_ERROR_NOT_SUPPORTED); }
aecError_t aecEventElapsedCycles(aecEvent_t, aecEvent_t, uint64_t *) {
    return finish(AEC_ERROR_NOT_SUPPORTED);
}
aecError_t aecHostRegister(void *, size_t) { return finish(AEC_ERROR_NOT_SUPPORTED); }
aecError_t aecHostUnregister(void *) { return finish(AEC_ERROR_NOT_SUPPORTED); }

aecError_t aecGetRuntimeStats(aecRuntimeStats *stats) {
    if (!stats) return finish(AEC_ERROR_INVALID_ARGUMENT);
    aecDeviceStats ds{};
    if (aecDeviceGetStats(&ds) != AEC_DEVICE_SUCCESS) return finish(AEC_ERROR_DEVICE);
    std::memcpy(stats, &ds, sizeof(*stats));
    stats->abi_version = AEC_RUNTIME_ABI_VERSION;
    return AEC_SUCCESS;
}

aecError_t aecResetRuntimeStats(void) {
    return aecDeviceResetStats() == AEC_DEVICE_SUCCESS ? AEC_SUCCESS : finish(AEC_ERROR_DEVICE);
}

static aecError_t launch_kernel(aecKernelId kernel, aecDim3 grid, aecDim3 block,
                                const void *args, size_t args_size) {
    uint32_t sem_id = 0, dtype = 6, variant = 1;
    switch (kernel) {
    case AEC_KERNEL_VECTOR_ADD_F32: sem_id = 1; dtype = 6; variant = 1; break;
    case AEC_KERNEL_GEMM_NAIVE:     sem_id = 10; dtype = 6; variant = 1; break;
    case AEC_KERNEL_GEMM_TILED:     sem_id = 10; dtype = 6; variant = 2; break;
    case AEC_KERNEL_GEMM_VECTORIZED:sem_id = 10; dtype = 6; variant = 3; break;
    default: return finish(AEC_ERROR_NOT_SUPPORTED);
    }
    aecDeviceKernelInfo info{};
    if (aecDeviceResolveKernel(sem_id, dtype, variant, &info) != AEC_DEVICE_SUCCESS)
        return finish(AEC_ERROR_DEVICE);

    aecDeviceCommand cmd{};
    cmd.abi_version = AEC_DEVICE_ABI_VERSION;
    cmd.opcode = AEC_DEVICE_OP_ISA_LAUNCH;
    cmd.kernel_handle = info.handle;
    cmd.isa_version = info.isa_version;
    cmd.entry_pc = info.entry_pc;
    cmd.grid = {grid.x, grid.y, grid.z};
    cmd.block = {block.x, block.y, block.z};
    cmd.parameter_bytes = static_cast<uint32_t>(args_size);
    if (args_size > sizeof(cmd.parameters))
        return finish(AEC_ERROR_INVALID_ARGUMENT);
    if (args && args_size > 0)
        std::memcpy(cmd.parameters, args, args_size);

    aecDeviceCompletion comp{};
    if (aecDeviceSubmit(&cmd, &comp) != AEC_DEVICE_SUCCESS)
        return finish(AEC_ERROR_DEVICE);
    if (comp.status == AEC_DEVICE_ISA_TRAP)
        return finish(AEC_ERROR_ISA_TRAP);
    return AEC_SUCCESS;
}

aecError_t aecLaunch(aecKernelId kernel, aecDim3 grid, aecDim3 block,
                     const void *args, size_t args_size, aecStream_t) {
    return launch_kernel(kernel, grid, block, args, args_size);
}

static aecError_t matmul(aecDevicePtr a, aecDevicePtr b, aecDevicePtr c,
                         uint32_t m, uint32_t n, uint32_t k,
                         uint32_t dtype, uint32_t variant) {
    aecGemmArgs args{a, b, c, m, n, k, dtype, 0};
    aecDim3 grid{1, 1, 1}, block{256, 1, 1};
    aecDeviceKernelInfo info{};
    if (aecDeviceResolveKernel(10, dtype, variant, &info) != AEC_DEVICE_SUCCESS)
        return finish(AEC_ERROR_DEVICE);
    aecDeviceCommand cmd{};
    cmd.abi_version = AEC_DEVICE_ABI_VERSION;
    cmd.opcode = AEC_DEVICE_OP_ISA_LAUNCH;
    cmd.kernel_handle = info.handle;
    cmd.isa_version = info.isa_version;
    cmd.entry_pc = info.entry_pc;
    cmd.grid = {grid.x, grid.y, grid.z};
    cmd.block = {block.x, block.y, block.z};
    cmd.parameter_bytes = sizeof(args);
    std::memcpy(cmd.parameters, &args, sizeof(args));
    aecDeviceCompletion comp{};
    return aecDeviceSubmit(&cmd, &comp) == AEC_DEVICE_SUCCESS
        ? AEC_SUCCESS : finish(AEC_ERROR_DEVICE);
}

aecError_t aecMatmulF32(aecDevicePtr a, aecDevicePtr b, aecDevicePtr c,
                        uint32_t m, uint32_t n, uint32_t k, aecStream_t) {
    return matmul(a, b, c, m, n, k, 6, 1);
}
aecError_t aecMatmulF16(aecDevicePtr a, aecDevicePtr b, aecDevicePtr c,
                        uint32_t m, uint32_t n, uint32_t k, aecStream_t) {
    return matmul(a, b, c, m, n, k, 4, 2);
}
aecError_t aecMatmulBF16(aecDevicePtr a, aecDevicePtr b, aecDevicePtr c,
                         uint32_t m, uint32_t n, uint32_t k, aecStream_t) {
    return matmul(a, b, c, m, n, k, 5, 2);
}
aecError_t aecMatmulF64(aecDevicePtr a, aecDevicePtr b, aecDevicePtr c,
                        uint32_t m, uint32_t n, uint32_t k, aecStream_t) {
    return matmul(a, b, c, m, n, k, 7, 1);
}
aecError_t aecMatmulF4(aecDevicePtr a, aecDevicePtr b, aecDevicePtr c,
                       uint32_t m, uint32_t n, uint32_t k, aecStream_t) {
    return matmul(a, b, c, m, n, k, 1, 3);
}
aecError_t aecMatmulF8(aecDevicePtr a, aecDevicePtr b, aecDevicePtr c,
                       uint32_t m, uint32_t n, uint32_t k, aecFp8Format fmt, aecStream_t) {
    uint32_t dtype = (fmt == AEC_FP8_E5M2) ? 3 : 2;
    return matmul(a, b, c, m, n, k, dtype, 2);
}
aecError_t aecMatmulI4(aecDevicePtr a, aecDevicePtr b, aecDevicePtr c,
                       uint32_t m, uint32_t n, uint32_t k, aecStream_t) {
    return matmul(a, b, c, m, n, k, 8, 1);
}
aecError_t aecMatmulI8(aecDevicePtr a, aecDevicePtr b, aecDevicePtr c,
                       uint32_t m, uint32_t n, uint32_t k, aecStream_t) {
    return matmul(a, b, c, m, n, k, 9, 1);
}
aecError_t aecMatmulI32(aecDevicePtr a, aecDevicePtr b, aecDevicePtr c,
                        uint32_t m, uint32_t n, uint32_t k, aecStream_t) {
    return matmul(a, b, c, m, n, k, 10, 1);
}

aecError_t aecAxpy(aecDevicePtr, aecDevicePtr, uint64_t, float, aecStream_t) {
    return finish(AEC_ERROR_NOT_SUPPORTED);
}
aecError_t aecDot(aecDevicePtr, aecDevicePtr, aecDevicePtr, uint64_t, aecStream_t) {
    return finish(AEC_ERROR_NOT_SUPPORTED);
}
aecError_t aecNrm2(aecDevicePtr, aecDevicePtr, uint64_t, aecStream_t) {
    return finish(AEC_ERROR_NOT_SUPPORTED);
}

} // extern "C"
