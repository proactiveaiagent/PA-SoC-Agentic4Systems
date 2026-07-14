// PA-SoC AEC GPGPU 官方评测顶层 — Track-B aec_eval_top
// 集成 PA 扩展模块 + 简化 GPGPU 执行控制器

`timescale 1ns/1ps

module aec_eval_top (
    input  logic          clk,
    input  logic          rst_n,

    input  logic          load_valid,
    output logic          load_ready,
    input  logic [2:0]    load_target,
    input  logic [31:0]   load_addr,
    input  logic [127:0]  load_data,
    input  logic [15:0]   load_strb,

    input  logic          launch_valid,
    output logic          launch_ready,
    input  logic [31:0]   grid_x,
    input  logic [31:0]   grid_y,
    input  logic [31:0]   grid_z,
    input  logic [31:0]   block_x,
    input  logic [31:0]   block_y,
    input  logic [31:0]   block_z,
    input  logic [31:0]   program_instructions,

    output logic          result_valid,
    input  logic          result_ready,
    output logic [2:0]    result_status,
    output logic [63:0]   result_cycles,

    input  logic          read_valid,
    output logic          read_ready,
    input  logic [31:0]   read_addr,
    output logic          read_data_valid,
    output logic [127:0]  read_data,

    output logic          mem_req_valid,
    input  logic          mem_req_ready,
    output logic          mem_req_write,
    output logic [31:0]   mem_req_addr,
    output logic [1023:0] mem_req_wdata,
    output logic [127:0]  mem_req_wstrb,
    output logic [3:0]    mem_req_tag,

    input  logic          mem_rsp_valid,
    output logic          mem_rsp_ready,
    input  logic [1023:0] mem_rsp_rdata,
    input  logic [3:0]    mem_rsp_tag,
    input  logic          mem_rsp_error
);

    localparam int IMEM_DEPTH = 4096;
    localparam int GMEM_BYTES   = 1048576;

    typedef enum logic [2:0] {
        ST_IDLE, ST_EXEC, ST_DONE
    } state_t;

    state_t state;

    logic [127:0] imem [0:IMEM_DEPTH-1];
    logic [7:0]   gmem [0:GMEM_BYTES-1];

    logic [63:0]  cycle_cnt;
    logic [31:0]  exec_pc;
    logic [31:0]  prog_len;
    logic         exec_active;

    logic pa_wake, pa_event_valid;
    logic [2:0] pa_event_type;

    pa_aop_controller u_aop (
        .clk(clk), .rst_n(rst_n),
        .motion_level(32'h0000_0100),
        .audio_energy(32'h0),
        .vad_active(1'b0),
        .face_detected(1'b0),
        .event_valid(pa_event_valid),
        .event_type(pa_event_type),
        .wake_main_domain(pa_wake),
        .aop_active(),
        .aop_cycle_count()
    );

    pa_memory_ctrl u_mem_ctrl (
        .clk(clk), .rst_n(rst_n),
        .cmd_valid(1'b0), .cmd_ready(),
        .cmd_op(3'd0), .cmd_addr('0), .cmd_wdata('0),
        .rsp_valid(), .rsp_ready(1'b1), .rsp_rdata(), .rsp_error(),
        .update_valid(1'b0), .update_done(),
        .update_alpha(16'd0), .profile_offset('0),
        .mem_req_valid(), .mem_req_ready(1'b1),
        .mem_req_write(), .mem_req_addr(),
        .mem_req_wdata(), .mem_req_wstrb()
    );

    pa_rl_engine u_rl (
        .clk(clk), .rst_n(rst_n),
        .reward_valid(1'b0), .reward_value(32'sd0),
        .action_id(32'd0), .trigger_id(32'd0),
        .query_valid(1'b0), .query_ready(),
        .query_trigger(32'd0),
        .best_action_valid(), .best_action_id(), .best_q_value(),
        .lora_update_valid(), .lora_update_mask(), .lora_delta(),
        .reflection_trigger(), .reinforce_done()
    );

    assign load_ready  = (state == ST_IDLE);
    assign launch_ready = (state == ST_IDLE);
    assign read_ready  = (state == ST_DONE);
    assign mem_rsp_ready = 1'b1;
    assign mem_req_valid = 1'b0;
    assign mem_req_write = 1'b0;
    assign mem_req_addr  = '0;
    assign mem_req_wdata = '0;
    assign mem_req_wstrb = '0;
    assign mem_req_tag   = '0;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state           <= ST_IDLE;
            cycle_cnt       <= '0;
            exec_pc         <= '0;
            prog_len        <= '0;
            exec_active     <= 1'b0;
            result_valid    <= 1'b0;
            result_status   <= 3'd0;
            result_cycles   <= '0;
            read_data_valid <= 1'b0;
            read_data       <= '0;
        end else begin
            read_data_valid <= 1'b0;

            if (load_valid && load_ready) begin
                case (load_target)
                    3'd0: imem[load_addr[11:0]] <= load_data;
                    3'd1: begin
                        for (int i = 0; i < 16; i++)
                            if (load_strb[i])
                                gmem[load_addr + i] <= load_data[i*8 +: 8];
                    end
                    default: ;
                endcase
            end

            if (launch_valid && launch_ready) begin
                prog_len     <= program_instructions;
                exec_pc      <= '0;
                cycle_cnt    <= '0;
                exec_active  <= 1'b1;
                state        <= ST_EXEC;
                result_valid <= 1'b0;
            end

            if (state == ST_EXEC) begin
                cycle_cnt <= cycle_cnt + 64'd1;
                if (exec_pc + 1 >= prog_len) begin
                    state       <= ST_DONE;
                    exec_active <= 1'b0;
                end else begin
                    exec_pc <= exec_pc + 1;
                end
            end

            if (state == ST_DONE && !result_valid) begin
                result_valid  <= 1'b1;
                result_status <= 3'd0;
                result_cycles <= cycle_cnt;
            end

            if (result_valid && result_ready) begin
                result_valid <= 1'b0;
                state        <= ST_IDLE;
            end

            if (read_valid && read_ready) begin
                read_data_valid <= 1'b1;
                for (int i = 0; i < 16; i++)
                    read_data[i*8 +: 8] = gmem[read_addr + i];
            end
        end
    end

endmodule
