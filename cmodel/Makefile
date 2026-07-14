CC = gcc
CXX = g++
CFLAGS = -Wall -Wextra -std=c11 -O2
CXXFLAGS = -Wall -Wextra -std=c++17 -O2

TARGETS = pa_cmodel_demo aec_cmodel_demo

all: $(TARGETS)

pa_cmodel_demo: pa_cmodel.c
	$(CC) $(CFLAGS) -o $@ $<

aec_cmodel_demo: aec_interpreter.c aec_cmodel_main.c
	$(CC) $(CFLAGS) -o $@ aec_interpreter.c aec_cmodel_main.c

run: aec_cmodel_demo
	./aec_cmodel_demo

clean:
	rm -f $(TARGETS)

.PHONY: all run clean
