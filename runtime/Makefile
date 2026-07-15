# PA-SoC AEC Runtime — 对接竞赛官方 starter-kit

MAKEFILE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
ROOT := $(abspath $(MAKEFILE_DIR)/..)
STARTER_KIT := $(ROOT)/third_party/starter-kit
RUNTIME_SO := $(ROOT)/runtime/libaec.so

CXX ?= g++
CXXFLAGS ?= -O2 -g -std=c++17 -fPIC -Wall -Wextra -Wpedantic -ffp-contract=off
CPPFLAGS ?= -I$(STARTER_KIT)/include -I$(ROOT)/runtime/include

.PHONY: all setup starter-kit examples clean public-test

all: setup $(RUNTIME_SO)

setup: starter-kit

starter-kit:
	@bash $(ROOT)/runtime/setup_starter_kit.sh

$(RUNTIME_SO): src/pa_aec_runtime.cpp \
               $(STARTER_KIT)/include/aec_runtime.h \
               $(STARTER_KIT)/lib/libaec_device.so
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -shared src/pa_aec_runtime.cpp -o $@ \
		-L$(STARTER_KIT)/lib -laec_device -pthread \
		-Wl,-rpath,'$$ORIGIN/../third_party/starter-kit/lib'

examples: all
	@mkdir -p $(ROOT)/runtime/bin
	$(CC) $(CPPFLAGS) -O2 -std=c11 -Wall \
		$(STARTER_KIT)/examples/01_device_query.c \
		-o $(ROOT)/runtime/bin/01_device_query \
		-L$(ROOT)/runtime -laec \
		-Wl,-rpath,'$$ORIGIN/..'

public-test: all
	cd $(STARTER_KIT) && python3 grader/public_grade.py \
		--submission $(ROOT)/runtime/submission_wrapper \
		--profile public 2>/dev/null || \
		echo "[hint] 运行 runtime/submission_wrapper 指向本仓库"

clean:
	rm -f $(RUNTIME_SO)
	rm -rf $(ROOT)/runtime/bin
