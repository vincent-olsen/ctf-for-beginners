# Makefile
CC      := gcc
CFLAGS  := -O0 -g -Wall -Wextra -fno-stack-protector -U_FORTIFY_SOURCE -no-pie -Wno-stringop-overflow
LDFLAGS := -no-pie

all: clean bin

bin: bin.c
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

clean:
	rm -f bin

