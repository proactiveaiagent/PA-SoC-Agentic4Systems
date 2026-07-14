// AEC GPGPU 功能 CModel — ISA 解释器头文件
#ifndef AEC_INTERPRETER_H
#define AEC_INTERPRETER_H

#include <stdint.h>
#include <stddef.h>

#define AEC_WARP_SIZE 32
#define AEC_MAX_WARPS 8
#define AEC_GPR_COUNT 256
#define AEC_PRED_COUNT 8
#define AEC_SMEM_BYTES 65536
#define AEC_LMEM_BYTES 4096

typedef struct {
    uint32_t word0, word1, word2, word3;
} aec_inst_t;

typedef struct {
    uint32_t grid[3];
    uint32_t block[3];
    uint32_t prog_len;
    uint64_t cycles;
    int done;
    int error;
} aec_launch_t;

typedef struct {
    uint32_t gprs[AEC_GPR_COUNT];
    uint8_t  preds[AEC_PRED_COUNT];
    uint32_t pc;
    uint8_t  active;
    uint8_t  halted;
    uint32_t lane_id;
    uint32_t tid[3];
    uint32_t ntid[3];
    uint32_t ctaid[3];
    uint32_t nctaid[3];
} aec_thread_t;

typedef struct {
    aec_thread_t lanes[AEC_WARP_SIZE];
    uint32_t pc;
    uint32_t call_stack[32];
    int call_depth;
    uint8_t completed;
    uint8_t halted;
} aec_warp_t;

typedef struct {
    aec_inst_t *imem;
    size_t imem_count;
    uint8_t *gmem;
    size_t gmem_size;
    uint8_t *cmem;
    size_t cmem_size;
    uint8_t *pmem;
    size_t pmem_size;
    uint8_t smem[AEC_SMEM_BYTES];
    uint8_t lmem[AEC_MAX_WARPS * AEC_WARP_SIZE * AEC_LMEM_BYTES];
    aec_warp_t warps[AEC_MAX_WARPS];
    int warp_count;
    aec_launch_t launch;
    uint64_t cycle_count;
    int exec_error;
} aec_machine_t;

void aec_machine_init(aec_machine_t *m);
void aec_machine_reset(aec_machine_t *m);
int  aec_machine_launch(aec_machine_t *m, uint32_t gx, uint32_t gy, uint32_t gz,
                        uint32_t bx, uint32_t by, uint32_t bz, uint32_t prog_len);
int  aec_machine_step(aec_machine_t *m);
int  aec_machine_run(aec_machine_t *m, uint64_t max_cycles);

/* 回归测试 API */
int aec_run_case(
    const aec_inst_t *prog, size_t prog_count,
    uint32_t gx, uint32_t gy, uint32_t gz,
    uint32_t bx, uint32_t by, uint32_t bz,
    uint8_t *gmem, size_t gmem_size,
    uint8_t *cmem, size_t cmem_size,
    uint64_t max_cycles,
    uint64_t *out_cycles,
    int *out_error
);

uint16_t aec_opcode(const aec_inst_t *i);
uint8_t  aec_type(const aec_inst_t *i);
uint8_t  aec_pred(const aec_inst_t *i);
int      aec_pred_enabled(const aec_inst_t *i);
uint8_t  aec_dst(const aec_inst_t *i);
uint8_t  aec_src1(const aec_inst_t *i);
uint16_t aec_src2(const aec_inst_t *i);
uint32_t aec_imm(const aec_inst_t *i);
uint8_t  aec_mem_space(const aec_inst_t *i);

#endif
