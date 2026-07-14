// AEC 单用例执行器 — 供回归框架调用
#include "aec_interpreter.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define GMEM_SIZE (1u << 20)
#define CMEM_SIZE 65536u

static int read_file(const char *path, uint8_t **out, size_t *out_len) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    *out = (uint8_t *)malloc((size_t)sz);
    if (!*out) { fclose(f); return -1; }
    if (fread(*out, 1, (size_t)sz, f) != (size_t)sz) { free(*out); fclose(f); return -1; }
    fclose(f);
    *out_len = (size_t)sz;
    return 0;
}

static int write_file(const char *path, const uint8_t *data, size_t len) {
    FILE *f = fopen(path, "wb");
    if (!f) return -1;
    fwrite(data, 1, len, f);
    fclose(f);
    return 0;
}

int main(int argc, char **argv) {
    const char *prog_path = NULL;
    const char *gmem_in = NULL, *gmem_out = NULL;
    const char *cmem_in = NULL;
    uint32_t grid[3] = {1, 1, 1}, block[3] = {1, 1, 1};
    uint64_t max_cycles = 10000;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--program") && i + 1 < argc) prog_path = argv[++i];
        else if (!strcmp(argv[i], "--grid") && i + 3 < argc) {
            grid[0] = (uint32_t)atoi(argv[++i]);
            grid[1] = (uint32_t)atoi(argv[++i]);
            grid[2] = (uint32_t)atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--block") && i + 3 < argc) {
            block[0] = (uint32_t)atoi(argv[++i]);
            block[1] = (uint32_t)atoi(argv[++i]);
            block[2] = (uint32_t)atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--gmem-in") && i + 1 < argc) gmem_in = argv[++i];
        else if (!strcmp(argv[i], "--gmem-out") && i + 1 < argc) gmem_out = argv[++i];
        else if (!strcmp(argv[i], "--cmem-in") && i + 1 < argc) cmem_in = argv[++i];
        else if (!strcmp(argv[i], "--max-cycles") && i + 1 < argc) max_cycles = (uint64_t)atoll(argv[++i]);
    }

    if (!prog_path || !gmem_in || !gmem_out) {
        fprintf(stderr, "usage: aec_case_runner --program P --grid X Y Z --block X Y Z "
                "--gmem-in IN --gmem-out OUT [--cmem-in IN] [--max-cycles N]\n");
        return 1;
    }

    uint8_t *prog_blob = NULL, *gmem = NULL, *cmem = NULL;
    size_t prog_len = 0, gmem_len = 0, cmem_len = 0;
    if (read_file(prog_path, &prog_blob, &prog_len) != 0) return 1;
    if (read_file(gmem_in, &gmem, &gmem_len) != 0) { free(prog_blob); return 1; }
    if (gmem_len < GMEM_SIZE) {
        gmem = (uint8_t *)realloc(gmem, GMEM_SIZE);
        memset(gmem + gmem_len, 0, GMEM_SIZE - gmem_len);
        gmem_len = GMEM_SIZE;
    }
    cmem = (uint8_t *)calloc(1, CMEM_SIZE);
    if (cmem_in && read_file(cmem_in, &cmem, &cmem_len) != 0) {
        free(prog_blob); free(gmem); return 1;
    }
    if (cmem_len < CMEM_SIZE) cmem_len = CMEM_SIZE;

    size_t inst_count = prog_len / 16;
    aec_inst_t *inst = (aec_inst_t *)prog_blob;

    uint64_t cycles = 0;
    int error = 0;
    int rc = aec_run_case(inst, inst_count,
                          grid[0], grid[1], grid[2],
                          block[0], block[1], block[2],
                          gmem, gmem_len, cmem, cmem_len,
                          max_cycles, &cycles, &error);

    write_file(gmem_out, gmem, gmem_len);
    printf("cycles=%llu\n", (unsigned long long)cycles);
    printf("status=%s\n", error ? "exec_error" : "done");

    free(prog_blob);
    free(gmem);
    free(cmem);
    return (rc != 0) ? 2 : 0;
}
