// PA-SoC RL 反馈学习引擎
// Replay Buffer + 在线 LoRA 更新信号生成

module pa_rl_engine #(
    parameter REPLAY_DEPTH = 1024,
    parameter Q_VALUE_WIDTH = 32,
    parameter LORA_RANK = 8
) (
    input  logic                       clk,
    input  logic                       rst_n,

    // 奖励输入
    input  logic                       reward_valid,
    input  logic signed [Q_VALUE_WIDTH-1:0] reward_value,
    input  logic [31:0]                action_id,
    input  logic [31:0]                trigger_id,

    // 策略查询
    input  logic                       query_valid,
    output logic                       query_ready,
    input  logic [31:0]                query_trigger,
    output logic                       best_action_valid,
    output logic [31:0]                best_action_id,
    output logic signed [Q_VALUE_WIDTH-1:0] best_q_value,

    // LoRA 更新输出
    output logic                       lora_update_valid,
    output logic [LORA_RANK-1:0]       lora_update_mask,
    output logic signed [15:0]         lora_delta [LORA_RANK],

    // 反思触发
    output logic                       reflection_trigger,
    output logic                       reinforce_done
);

    localparam signed [Q_VALUE_WIDTH-1:0] LEARNING_RATE = 32'sd102; // Q8.8 fixed point

    logic [$clog2(REPLAY_DEPTH)-1:0] replay_head;
    logic [$clog2(REPLAY_DEPTH)-1:0] replay_count;

    logic signed [Q_VALUE_WIDTH-1:0] q_table [REPLAY_DEPTH];
    logic [31:0] action_table [REPLAY_DEPTH];
    logic [31:0] trigger_table [REPLAY_DEPTH];

    integer i;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            replay_head <= '0;
            replay_count <= '0;
            reflection_trigger <= 1'b0;
            lora_update_valid <= 1'b0;
            reinforce_done <= 1'b0;
            best_action_valid <= 1'b0;
            best_action_id <= '0;
            best_q_value <= '0;

            for (i = 0; i < LORA_RANK; i++)
                lora_delta[i] <= 16'sd0;
        end else begin
            reflection_trigger <= 1'b0;
            lora_update_valid <= 1'b0;
            reinforce_done <= 1'b0;
            best_action_valid <= 1'b0;

            if (reward_valid) begin
                q_table[replay_head] <= reward_value;
                action_table[replay_head] <= action_id;
                trigger_table[replay_head] <= trigger_id;
                replay_head <= replay_head + 1'b1;
                if (replay_count < REPLAY_DEPTH)
                    replay_count <= replay_count + 1'b1;

                lora_update_valid <= 1'b1;
                for (i = 0; i < LORA_RANK; i++)
                    lora_delta[i] <= reward_value[15:0];

                if (reward_value < 0)
                    reflection_trigger <= 1'b1;
                else
                    reinforce_done <= 1'b1;
            end

            if (query_valid) begin
                best_q_value <= q_table[0];
                best_action_id <= action_table[0];
                best_action_valid <= 1'b1;
            end
        end
    end

    assign query_ready = 1'b1;
    assign lora_update_mask = '1;

endmodule
