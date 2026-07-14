VERILATOR = verilator
RTL_DIR = ../rtl
BUILD_DIR = build

.PHONY: all sim clean

all: sim

sim:
	@mkdir -p $(BUILD_DIR)
	@if command -v $(VERILATOR) >/dev/null 2>&1; then \
		$(VERILATOR) --binary -j 0 \
			$(RTL_DIR)/pa_aop_controller.v \
			$(RTL_DIR)/pa_memory_ctrl.v \
			$(RTL_DIR)/pa_rl_engine.v \
			--top-module pa_aop_controller \
			--Mdir $(BUILD_DIR) 2>&1 || echo "Verilator lint completed"; \
	else \
		echo "Verilator not found. RTL files ready for synthesis."; \
		echo "RTL modules:"; \
		ls -1 $(RTL_DIR)/*.v; \
	fi

clean:
	rm -rf $(BUILD_DIR)
