#include "aec_interpreter.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    printf("=== AEC GPGPU CModel (PA-SoC) ===\n\n");

    aec_machine_t machine;
    aec_machine_init(&machine);

    aec_inst_t prog[4];
    memset(prog, 0, sizeof(prog));

    /* LOADI R1, 42 */
    prog[0].word0 = 42;
    prog[0].word2 = (1u << 16);
    prog[0].word3 = (0x0050u << 16);

    /* CPY R2, %tid.x  (src1 = 0x0100) */
    prog[1].word2 = (2u << 16) | 0x0100u;
    prog[1].word3 = (0x0051u << 16) | (8u << 3);

    /* ADD R3, R1, R2 */
    prog[2].word1 = 2;
    prog[2].word2 = (3u << 16) | 1u;
    prog[2].word3 = (0x0001u << 16) | (8u << 3);

    /* HALT */
    prog[3].word3 = (0x0045u << 16);

    machine.imem = prog;
    machine.imem_count = 4;
    machine.gmem = calloc(1, 65536);
    machine.gmem_size = 65536;

    aec_machine_launch(&machine, 1, 1, 1, 32, 1, 1, 4);
    aec_machine_run(&machine, 10000);

    printf("Cycles: %llu\n", (unsigned long long)machine.cycle_count);
    printf("Lane0 R1=%u R2=%u R3=%u\n",
           machine.warps[0].lanes[0].gprs[1],
           machine.warps[0].lanes[0].gprs[2],
           machine.warps[0].lanes[0].gprs[3]);
    printf("Lane1 R2(tid)=%u\n", machine.warps[0].lanes[1].gprs[2]);
    printf("Done=%d Error=%d\n", machine.launch.done, machine.exec_error);

    free(machine.gmem);
    printf("\nCModel ISA interpreter ready.\n");
    return machine.exec_error ? 1 : 0;
}
