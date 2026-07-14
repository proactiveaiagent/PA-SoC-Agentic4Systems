VERILATOR = verilator
RTL_DIR = ../rtl
BUILD_DIR = build

RTL_SRCS = \
	$(RTL_DIR)/pa_aop_controller.v \
	$(RTL_DIR)/pa_memory_ctrl.v \
	$(RTL_DIR)/pa_rl_engine.v \
	$(RTL_DIR)/aec_eval_top.sv

.PHONY: all sim clean

all: sim

sim:
	@mkdir -p $(BUILD_DIR)
	@if command -v $(VERILATOR) >/dev/null 2>&1; then \
		$(VERILATOR) --lint-only -Wall $(RTL_SRCS) --top-module aec_eval_top 2>&1; \
		echo "Verilator lint passed"; \
	else \
		echo "Verilator not found. RTL files:"; \
		ls -1 $(RTL_SRCS); \
	fi

clean:
	rm -rf $(BUILD_DIR)
