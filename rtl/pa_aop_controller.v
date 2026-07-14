// PA-SoC Always-On Perception (AOP) 控制器
// 基于 AEC GPGPU 竞赛 Track-B RTL 扩展
// 功能：低功耗持续感知，事件触发唤醒主计算域

module pa_aop_controller #(
    parameter FEATURE_WIDTH = 32,
    parameter EVENT_THRESHOLD = 16'h0100
) (
    input  logic                  clk,
    input  logic                  rst_n,

    // 传感器输入
    input  logic [FEATURE_WIDTH-1:0] motion_level,
    input  logic [FEATURE_WIDTH-1:0] audio_energy,
    input  logic                     vad_active,
    input  logic                     face_detected,

    // 事件输出 → 唤醒 AEC GPGPU 主域
    output logic                     event_valid,
    output logic [2:0]               event_type,
    output logic                     wake_main_domain,

    // 与 AEC eval top 的接口
    output logic                     aop_active,
    output logic [31:0]              aop_cycle_count
);

    typedef enum logic [2:0] {
        EVT_NONE    = 3'd0,
        EVT_MOTION  = 3'd1,
        EVT_AUDIO   = 3'd2,
        EVT_FACE    = 3'd3,
        EVT_COMBO   = 3'd4
    } event_type_e;

    logic motion_event, audio_event, face_event;
    logic [31:0] idle_cycles;
    logic main_domain_sleep;

    assign motion_event = (motion_level > EVENT_THRESHOLD);
    assign audio_event  = vad_active && (audio_energy > EVENT_THRESHOLD);
    assign face_event   = face_detected;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            event_valid        <= 1'b0;
            event_type         <= EVT_NONE;
            wake_main_domain   <= 1'b0;
            aop_active         <= 1'b1;
            aop_cycle_count    <= 32'd0;
            idle_cycles        <= 32'd0;
            main_domain_sleep  <= 1'b1;
        end else begin
            aop_cycle_count <= aop_cycle_count + 32'd1;
            event_valid     <= 1'b0;
            wake_main_domain  <= 1'b0;

            if (motion_event || audio_event || face_event) begin
                idle_cycles <= 32'd0;
                main_domain_sleep <= 1'b0;
                event_valid <= 1'b1;
                wake_main_domain <= 1'b1;

                if ((motion_event && audio_event) || (motion_event && face_event))
                    event_type <= EVT_COMBO;
                else if (motion_event)
                    event_type <= EVT_MOTION;
                else if (audio_event)
                    event_type <= EVT_AUDIO;
                else
                    event_type <= EVT_FACE;
            end else begin
                idle_cycles <= idle_cycles + 32'd1;
                if (idle_cycles > 32'd100000)
                    main_domain_sleep <= 1'b1;
            end
        end
    end

endmodule
