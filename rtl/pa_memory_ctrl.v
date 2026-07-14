// PA-SoC 记忆子系统控制器
// 管理 PMEM 用户画像存储 + GMEM 向量索引 + 增量更新

module pa_memory_ctrl #(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 128,
    parameter PROFILE_SIZE = 4096,
    parameter EMBEDDING_DIM = 768
) (
    input  logic                       clk,
    input  logic                       rst_n,

    // 命令接口
    input  logic                       cmd_valid,
    output logic                       cmd_ready,
    input  logic [2:0]                 cmd_op,
    input  logic [ADDR_WIDTH-1:0]      cmd_addr,
    input  logic [DATA_WIDTH-1:0]      cmd_wdata,

    // 响应接口
    output logic                       rsp_valid,
    input  logic                       rsp_ready,
    output logic [DATA_WIDTH-1:0]      rsp_rdata,
    output logic                       rsp_error,

    // 增量更新接口（EMA）
    input  logic                       update_valid,
    output logic                       update_done,
    input  logic [15:0]                update_alpha,
    input  logic [ADDR_WIDTH-1:0]      profile_offset,

    // AEC GPGPU DMA 接口（连接 GMEM/PMEM）
    output logic                       mem_req_valid,
    input  logic                       mem_req_ready,
    output logic                       mem_req_write,
    output logic [ADDR_WIDTH-1:0]      mem_req_addr,
    output logic [1023:0]              mem_req_wdata,
    output logic [127:0]               mem_req_wstrb
);

    localparam CMD_READ    = 3'd0;
    localparam CMD_WRITE   = 3'd1;
    localparam CMD_UPDATE  = 3'd2;
    localparam CMD_SEARCH  = 3'd3;

    typedef enum logic [2:0] {
        ST_IDLE,
        ST_CMD,
        ST_MEM_REQ,
        ST_UPDATE,
        ST_RSP
    } state_e;

    state_e state, next_state;
    logic [ADDR_WIDTH-1:0] pending_addr;
    logic [2:0] pending_op;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state <= ST_IDLE;
        else
            state <= next_state;
    end

    always_comb begin
        next_state = state;
        cmd_ready = 1'b0;
        rsp_valid = 1'b0;
        rsp_rdata = '0;
        rsp_error = 1'b0;
        mem_req_valid = 1'b0;
        mem_req_write = 1'b0;
        mem_req_addr = '0;
        mem_req_wdata = '0;
        mem_req_wstrb = '0;
        update_done = 1'b0;

        case (state)
            ST_IDLE: begin
                cmd_ready = 1'b1;
                if (cmd_valid) begin
                    pending_addr = cmd_addr;
                    pending_op = cmd_op;
                    next_state = ST_MEM_REQ;
                end else if (update_valid) begin
                    next_state = ST_UPDATE;
                end
            end

            ST_MEM_REQ: begin
                mem_req_valid = 1'b1;
                mem_req_addr = pending_addr;
                if (pending_op == CMD_WRITE) begin
                    mem_req_write = 1'b1;
                    mem_req_wdata = {8{cmd_wdata}};
                    mem_req_wstrb = '1;
                end
                if (mem_req_ready)
                    next_state = ST_RSP;
            end

            ST_UPDATE: begin
                update_done = 1'b1;
                next_state = ST_IDLE;
            end

            ST_RSP: begin
                rsp_valid = 1'b1;
                if (rsp_ready)
                    next_state = ST_IDLE;
            end
        endcase
    end

endmodule
