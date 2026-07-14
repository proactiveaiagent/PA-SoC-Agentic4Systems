// AEC ISA 功能解释器 — Track-B 官方 testcases 回归用
#include "aec_interpreter.h"
#include "aec_opcodes.h"
#include <string.h>
#include <math.h>
#include <stdlib.h>

uint16_t aec_opcode(const aec_inst_t *i) { return (uint16_t)(i->word3 >> 16); }
uint8_t  aec_type(const aec_inst_t *i)   { return (uint8_t)((i->word3 >> 3) & 0xf); }
uint8_t  aec_pred(const aec_inst_t *i)   {
    if (aec_opcode(i) == AEC_OP_BRX) return (uint8_t)(i->word3 & 7);
    if (!(i->word3 & 0x8000)) return 0xff;
    return (uint8_t)(i->word3 & 7);
}
int aec_pred_enabled(const aec_inst_t *i) {
    if (aec_opcode(i) == AEC_OP_BRX) return 1;
    return (i->word3 & 0x8000) != 0;
}
uint8_t  aec_dst(const aec_inst_t *i)    { return (uint8_t)((i->word2 >> 16) & 0xff); }
uint8_t  aec_src1(const aec_inst_t *i)   { return (uint8_t)(i->word2 & 0xff); }
uint16_t aec_src2(const aec_inst_t *i)   { return (uint16_t)(i->word1 & 0xffff); }
uint32_t aec_imm(const aec_inst_t *i)    { return i->word0; }
uint8_t  aec_mem_space(const aec_inst_t *i) { return (uint8_t)((i->word3 >> 11) & 7); }

static int lane_active(aec_thread_t *t) { return t->active && !t->halted; }

static int pred_true(aec_thread_t *t, const aec_inst_t *inst) {
    if (!aec_pred_enabled(inst)) return 1;
    uint8_t p = aec_pred(inst);
    int val = t->preds[p] != 0;
    if (inst->word3 & 0x4000) val = !val;
    return val;
}

static uint32_t special_reg(aec_thread_t *t, uint16_t sel) {
    switch (sel) {
    case 0x0100: return t->tid[0];
    case 0x0101: return t->ntid[0];
    case 0x0102: return t->ctaid[0];
    case 0x0103: return t->nctaid[0];
    case 0x0104: return t->lane_id;
    case 0x0110: return t->tid[1];
    case 0x0111: return t->ntid[1];
    case 0x0112: return t->ctaid[1];
    case 0x0113: return t->nctaid[1];
    case 0x0120: return t->tid[2];
    case 0x0121: return t->ntid[2];
    case 0x0122: return t->ctaid[2];
    case 0x0123: return t->nctaid[2];
    default: return 0;
    }
}

static uint8_t *mem_ptr(aec_machine_t *m, int space, uint32_t addr,
                        aec_thread_t *t, int warp_id) {
    switch (space) {
    case 0: return (addr < m->gmem_size) ? m->gmem + addr : NULL;
    case 1: return (addr < AEC_SMEM_BYTES) ? m->smem + addr : NULL;
    case 2: return (addr < m->cmem_size) ? m->cmem + addr : NULL;
    case 3: {
        size_t off = (size_t)warp_id * AEC_WARP_SIZE * AEC_LMEM_BYTES
                   + (size_t)t->lane_id * AEC_LMEM_BYTES + addr;
        return (addr < AEC_LMEM_BYTES) ? m->lmem + off : NULL;
    }
    default: return NULL;
    }
}

static uint32_t read_mem32(aec_machine_t *m, int space, uint32_t addr,
                           aec_thread_t *t, int warp_id) {
    uint8_t *p = mem_ptr(m, space, addr, t, warp_id);
    if (!p) { m->exec_error = 1; return 0; }
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void write_mem32(aec_machine_t *m, int space, uint32_t addr, uint32_t val,
                        aec_thread_t *t, int warp_id) {
    uint8_t *p = mem_ptr(m, space, addr, t, warp_id);
    if (!p) { m->exec_error = 1; return; }
    p[0] = val & 0xff; p[1] = (val >> 8) & 0xff;
    p[2] = (val >> 16) & 0xff; p[3] = (val >> 24) & 0xff;
}

static float f32_bits(uint32_t u) { float f; memcpy(&f, &u, 4); return f; }
static uint32_t f32_u(float f) { uint32_t u; memcpy(&u, &f, 4); return u; }

void aec_machine_init(aec_machine_t *m) { memset(m, 0, sizeof(*m)); }

void aec_machine_reset(aec_machine_t *m) {
    memset(m->smem, 0, sizeof(m->smem));
    memset(m->lmem, 0, sizeof(m->lmem));
    memset(m->warps, 0, sizeof(m->warps));
    m->cycle_count = 0;
    m->exec_error = 0;
    m->launch.done = 0;
}

int aec_machine_launch(aec_machine_t *m, uint32_t gx, uint32_t gy, uint32_t gz,
                       uint32_t bx, uint32_t by, uint32_t bz, uint32_t prog_len) {
    aec_machine_reset(m);
    m->launch.grid[0] = gx; m->launch.grid[1] = gy; m->launch.grid[2] = gz;
    m->launch.block[0] = bx; m->launch.block[1] = by; m->launch.block[2] = bz;
    m->launch.prog_len = prog_len;

    uint32_t total = bx * by * bz;
    m->warp_count = (int)((total + 31) / 32);
    if (m->warp_count > AEC_MAX_WARPS) return -1;

    for (int w = 0; w < m->warp_count; w++) {
        m->warps[w].pc = 0;
        m->warps[w].halted = 0;
        m->warps[w].completed = 0;
        m->warps[w].call_depth = 0;
        for (int l = 0; l < AEC_WARP_SIZE; l++) {
            uint32_t t = (uint32_t)(w * 32 + l);
            aec_thread_t *th = &m->warps[w].lanes[l];
            th->active = (t < total);
            th->halted = 0;
            th->lane_id = (uint32_t)l;
            memset(th->gprs, 0, sizeof(th->gprs));
            memset(th->preds, 0, sizeof(th->preds));
            if (th->active) {
                th->ntid[0] = bx; th->ntid[1] = by; th->ntid[2] = bz;
                th->nctaid[0] = gx; th->nctaid[1] = gy; th->nctaid[2] = gz;
                th->ctaid[0] = th->ctaid[1] = th->ctaid[2] = 0;
                th->tid[2] = t / (bx * by);
                uint32_t rem = t % (bx * by);
                th->tid[1] = rem / bx;
                th->tid[0] = rem % bx;
            }
        }
    }
    return 0;
}

/* warp 锁步执行：返回 1=PC 前进, 2=PC 跳转, 0=HALT */
static int exec_warp(aec_machine_t *m, int warp_id, const aec_inst_t *inst) {
    aec_warp_t *warp = &m->warps[warp_id];
    if (warp->halted || warp->completed) return 0;

    uint16_t op = aec_opcode(inst);
    uint8_t rd = aec_dst(inst), rs1 = aec_src1(inst);
    uint16_t rs2 = aec_src2(inst);
    uint32_t imm = aec_imm(inst);
    int branch_taken = 0;

    for (int l = 0; l < AEC_WARP_SIZE; l++) {
        aec_thread_t *t = &warp->lanes[l];
        if (!lane_active(t) || !pred_true(t, inst)) continue;

        switch (op) {
        case AEC_OP_LOADI:  t->gprs[rd] = imm; break;
        case AEC_OP_LOADI64:
            t->gprs[rd] = imm;
            t->gprs[rd + 1] = inst->word1;
            break;
        case AEC_OP_CPY:
            if ((inst->word2 & 0xffffu) >= 0x0100u)
                t->gprs[rd] = special_reg(t, (uint16_t)(inst->word2 & 0xffffu));
            else
                t->gprs[rd] = t->gprs[rs1];
            break;
        case AEC_OP_ADD: t->gprs[rd] = t->gprs[rs1] + t->gprs[rs2 & 0xff]; break;
        case AEC_OP_SUB: t->gprs[rd] = t->gprs[rs1] - t->gprs[rs2 & 0xff]; break;
        case AEC_OP_MUL: t->gprs[rd] = t->gprs[rs1] * t->gprs[rs2 & 0xff]; break;
        case AEC_OP_MAD:
            t->gprs[rd] = t->gprs[rs1] * t->gprs[rs2 & 0xff] + t->gprs[imm & 0xff];
            break;
        case AEC_OP_FMA: {
            float a = f32_bits(t->gprs[rs1]), b = f32_bits(t->gprs[rs2 & 0xff]);
            float c = f32_bits(t->gprs[imm & 0xff]);
            t->gprs[rd] = f32_u(a * b + c);
            break;
        }
        case AEC_OP_DIV:
            if (t->gprs[rs2 & 0xff] == 0) { m->exec_error = 1; return 0; }
            t->gprs[rd] = t->gprs[rs1] / t->gprs[rs2 & 0xff];
            break;
        case AEC_OP_LD:
            t->gprs[rd] = read_mem32(m, aec_mem_space(inst), t->gprs[rs1], t, warp_id);
            break;
        case AEC_OP_ST:
            write_mem32(m, aec_mem_space(inst), t->gprs[rs1], t->gprs[rs2 & 0xff], t, warp_id);
            break;
        case AEC_OP_LDC:
            t->gprs[rd] = read_mem32(m, 2, t->gprs[rs1], t, warp_id);
            break;
        case AEC_OP_BR:
            warp->pc = imm;
            branch_taken = 2;
            break;
        case AEC_OP_BRX:
            if (t->preds[aec_pred(inst)]) { warp->pc = imm; branch_taken = 2; }
            break;
        case AEC_OP_CALL:
            if (warp->call_depth < 32) {
                warp->call_stack[warp->call_depth++] = warp->pc + 1;
                warp->pc = imm;
                branch_taken = 2;
            } else m->exec_error = 1;
            break;
        case AEC_OP_RET:
            if (warp->call_depth > 0) {
                warp->pc = warp->call_stack[--warp->call_depth];
                branch_taken = 2;
            } else m->exec_error = 1;
            break;
        case AEC_OP_HALT:
            t->halted = 1;
            break;
        case AEC_OP_RDTSC:
            t->gprs[rd] = (uint32_t)m->cycle_count;
            break;
        default:
            break;
        }
    }

    if (op == AEC_OP_HALT) {
        int any = 0;
        for (int l = 0; l < AEC_WARP_SIZE; l++)
            if (lane_active(&warp->lanes[l])) any = 1;
        if (!any) { warp->halted = 1; warp->completed = 1; }
        return 0;
    }
    if (branch_taken == 2) return 2;
    return 1;
}

int aec_machine_step(aec_machine_t *m) {
    if (m->launch.done || m->exec_error) return 0;

    int any_running = 0;
    for (int w = 0; w < m->warp_count; w++) {
        aec_warp_t *warp = &m->warps[w];
        if (warp->completed || warp->halted) continue;
        if (warp->pc >= m->launch.prog_len) {
            warp->completed = 1;
            continue;
        }
        int rc = exec_warp(m, w, &m->imem[warp->pc]);
        if (m->exec_error) { m->launch.done = 1; return 0; }
        if (rc == 1) warp->pc++;
        any_running = 1;
    }

    m->cycle_count++;
    if (!any_running) m->launch.done = 1;
    return any_running && !m->launch.done;
}

int aec_machine_run(aec_machine_t *m, uint64_t max_cycles) {
    while (m->cycle_count < max_cycles && aec_machine_step(m))
        ;
    if (m->cycle_count >= max_cycles && !m->launch.done) m->exec_error = 1;
    return m->exec_error ? -1 : 0;
}

int aec_run_case(
    const aec_inst_t *prog, size_t prog_count,
    uint32_t gx, uint32_t gy, uint32_t gz,
    uint32_t bx, uint32_t by, uint32_t bz,
    uint8_t *gmem, size_t gmem_size,
    uint8_t *cmem, size_t cmem_size,
    uint64_t max_cycles,
    uint64_t *out_cycles,
    int *out_error
) {
    aec_machine_t machine;
    aec_machine_init(&machine);
    machine.imem = (aec_inst_t *)prog;
    machine.imem_count = prog_count;
    machine.gmem = gmem;
    machine.gmem_size = gmem_size;
    machine.cmem = cmem;
    machine.cmem_size = cmem_size;
    machine.pmem = NULL;
    machine.pmem_size = 0;

    uint32_t prog_len = (uint32_t)prog_count;
    if (aec_machine_launch(&machine, gx, gy, gz, bx, by, bz, prog_len) != 0) {
        if (out_error) *out_error = 1;
        return -1;
    }
    aec_machine_run(&machine, max_cycles);
    if (out_cycles) *out_cycles = machine.cycle_count;
    if (out_error) *out_error = machine.exec_error;
    return machine.exec_error ? -1 : 0;
}
