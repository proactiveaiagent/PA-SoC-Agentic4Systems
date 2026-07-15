# C1 AEC 编译器

## 入口

```bash
./aec-cc input.ptx -O2 -o output.aecbin
./aec-objdump output.aecbin
```

## 编译流水线

```
PTX 源码
  → ptx_parser.py      解析
  → ptx_lower.py       PTX → IR
  → passes.py          DCE / CSE / 寄存器分配 / 调度
  → codegen.py         IR → AEC 128-bit 机器码
  → aecbin_format.py   写入 .aecbin
```

## 已实现能力

| 模块 | 功能 |
|------|------|
| **param 加载** | `ld.param.u32/u64/f32` → CMEM `LDC` |
| **谓词比较** | `setp.{eq,ne,lt,le,gt,ge}.u32` → `CMPP` |
| **优化 Pass** | DCE、CSE、线性扫描寄存器分配、内存/算术调度 |
| **PTX 支持** | PTX-01 ~ PTX-05 公开测试用例均可编译 |

## 源码结构

```
compiler/
├── aec-cc              # 统一入口
├── aec-objdump         # 反汇编器
└── src/
    ├── aec_cc.py       # 主程序
    ├── ptx_parser.py   # PTX 解析
    ├── ptx_lower.py    # Lowering
    ├── ir.py           # 中间表示
    ├── passes.py       # 优化 Pass
    ├── codegen.py      # 代码生成
    ├── inst_encode.py  # 指令编码
    └── aecbin_format.py
```
