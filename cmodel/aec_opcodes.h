/* Track-B AEC opcode definitions */
#ifndef AEC_OPCODES_H
#define AEC_OPCODES_H

#define AEC_OP_ADD      0x0001
#define AEC_OP_SUB      0x0002
#define AEC_OP_MUL      0x0003
#define AEC_OP_MAD      0x0004
#define AEC_OP_FMA      0x0005
#define AEC_OP_DIV      0x0006
#define AEC_OP_LD       0x0030
#define AEC_OP_ST       0x0031
#define AEC_OP_LDC      0x0032
#define AEC_OP_ATOM     0x0033
#define AEC_OP_BR       0x0040
#define AEC_OP_BRX      0x0041
#define AEC_OP_CALL     0x0043
#define AEC_OP_RET      0x0044
#define AEC_OP_HALT     0x0045
#define AEC_OP_SYNC_CT  0x0047
#define AEC_OP_MBAR     0x0049
#define AEC_OP_CVTFF    0x0050
#define AEC_OP_CPY      0x0054
#define AEC_OP_LOADI    0x0055
#define AEC_OP_LOADI64  0x0056
#define AEC_OP_SHUF     0x0057
#define AEC_OP_VOTE     0x0058
#define AEC_OP_MTCH     0x0059
#define AEC_OP_RDTSC    0x0080

#endif
