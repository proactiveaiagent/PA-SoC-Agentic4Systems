CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -O2
TARGET = pa_cmodel_demo

all: $(TARGET)

$(TARGET): pa_cmodel.c
	$(CC) $(CFLAGS) -o $@ $<

run: $(TARGET)
	./$(TARGET)

clean:
	rm -f $(TARGET)

.PHONY: all run clean
