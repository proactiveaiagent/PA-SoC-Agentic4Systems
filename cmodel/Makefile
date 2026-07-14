CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -O2

TARGETS = pa_cmodel_demo aec_cmodel_demo aec_case_runner

all: $(TARGETS)

pa_cmodel_demo: pa_cmodel.c
	$(CC) $(CFLAGS) -o $@ $<

aec_cmodel_demo: aec_interpreter.c aec_cmodel_main.c
	$(CC) $(CFLAGS) -o $@ aec_interpreter.c aec_cmodel_main.c

aec_case_runner: aec_interpreter.c aec_case_runner.c
	$(CC) $(CFLAGS) -o $@ aec_interpreter.c aec_case_runner.c

run: aec_cmodel_demo
	./aec_cmodel_demo

clean:
	rm -f $(TARGETS)

.PHONY: all run clean
