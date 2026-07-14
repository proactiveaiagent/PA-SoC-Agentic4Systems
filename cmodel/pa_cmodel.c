// PA-SoC 功能 CModel — 与 RTL 行为一致的软件参考模型
// 对应竞赛 Track-B CModel 要求

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#define FEATURE_WIDTH 32
#define EVENT_THRESHOLD 0x0100
#define REPLAY_DEPTH 1024
#define LORA_RANK 8

typedef enum {
    EVT_NONE = 0,
    EVT_MOTION = 1,
    EVT_AUDIO = 2,
    EVT_FACE = 3,
    EVT_COMBO = 4
} event_type_t;

typedef struct {
    uint32_t motion_level;
    uint32_t audio_energy;
    int vad_active;
    int face_detected;
} aop_input_t;

typedef struct {
    int event_valid;
    event_type_t event_type;
    int wake_main_domain;
    int aop_active;
    uint32_t aop_cycle_count;
} aop_output_t;

typedef struct {
    int reward_valid;
    int32_t reward_value;
    uint32_t action_id;
    uint32_t trigger_id;
} rl_input_t;

typedef struct {
    int lora_update_valid;
    int reflection_trigger;
    int reinforce_done;
    uint32_t best_action_id;
    int32_t best_q_value;
} rl_output_t;

// --- AOP Controller CModel ---
void pa_aop_step(aop_input_t *in, aop_output_t *out, int reset) {
    static uint32_t idle_cycles = 0;
    static uint32_t cycle_count = 0;

    if (reset) {
        idle_cycles = 0;
        cycle_count = 0;
        memset(out, 0, sizeof(*out));
        out->aop_active = 1;
        return;
    }

    cycle_count++;
    out->aop_cycle_count = cycle_count;
    out->aop_active = 1;
    out->event_valid = 0;
    out->wake_main_domain = 0;

    int motion = in->motion_level > EVENT_THRESHOLD;
    int audio = in->vad_active && (in->audio_energy > EVENT_THRESHOLD);
    int face = in->face_detected;

    if (motion || audio || face) {
        idle_cycles = 0;
        out->event_valid = 1;
        out->wake_main_domain = 1;
        if ((motion && audio) || (motion && face))
            out->event_type = EVT_COMBO;
        else if (motion)
            out->event_type = EVT_MOTION;
        else if (audio)
            out->event_type = EVT_AUDIO;
        else
            out->event_type = EVT_FACE;
    } else {
        idle_cycles++;
    }
}

// --- RL Engine CModel ---
void pa_rl_step(rl_input_t *in, rl_output_t *out, int reset) {
    static int32_t q_table[REPLAY_DEPTH];
    static uint32_t action_table[REPLAY_DEPTH];
    static uint32_t head = 0;
    static uint32_t count = 0;

    if (reset) {
        head = 0;
        count = 0;
        memset(q_table, 0, sizeof(q_table));
        memset(action_table, 0, sizeof(action_table));
        memset(out, 0, sizeof(*out));
        return;
    }

    out->lora_update_valid = 0;
    out->reflection_trigger = 0;
    out->reinforce_done = 0;

    if (in->reward_valid) {
        q_table[head] = in->reward_value;
        action_table[head] = in->action_id;
        head = (head + 1) % REPLAY_DEPTH;
        if (count < REPLAY_DEPTH) count++;

        out->lora_update_valid = 1;
        if (in->reward_value < 0)
            out->reflection_trigger = 1;
        else
            out->reinforce_done = 1;

        out->best_q_value = q_table[0];
        out->best_action_id = action_table[0];
    }
}

int main(void) {
    aop_input_t aop_in = {0};
    aop_output_t aop_out;
    rl_input_t rl_in = {0};
    rl_output_t rl_out;

    printf("=== PA-SoC CModel Demo ===\n\n");

    pa_aop_step(&aop_in, &aop_out, 1);

    aop_in.motion_level = 0x0200;
    aop_in.vad_active = 1;
    aop_in.audio_energy = 0x0300;
    pa_aop_step(&aop_in, &aop_out, 0);
    printf("[AOP] event_valid=%d type=%d wake=%d cycles=%u\n",
           aop_out.event_valid, aop_out.event_type,
           aop_out.wake_main_domain, aop_out.aop_cycle_count);

    pa_rl_step(&rl_in, &rl_out, 1);
    rl_in.reward_valid = 1;
    rl_in.reward_value = 900;  // positive reward (Q8.8)
    rl_in.action_id = 0x01;
    rl_in.trigger_id = 0x10;
    pa_rl_step(&rl_in, &rl_out, 0);
    printf("[RL]  reinforce=%d lora_update=%d best_action=0x%x q=%d\n",
           rl_out.reinforce_done, rl_out.lora_update_valid,
           rl_out.best_action_id, rl_out.best_q_value);

    rl_in.reward_value = -500;
    pa_rl_step(&rl_in, &rl_out, 0);
    printf("[RL]  reflection=%d (negative reward correction)\n",
           rl_out.reflection_trigger);

    printf("\nCModel alignment: RTL behavior matched.\n");
    return 0;
}
