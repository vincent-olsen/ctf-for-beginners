# Same hardening-off flags as overflow1-3 (see CLAUDE.md); do not "fix" these.
# Unlike the overflows, this binary is STRIPPED (-s, no -g): win()/gadget() as
# named symbols made the ret2win trivial for an AI (it read them straight off
# `nm`), so the player must reverse the logic instead. Stripping removes only the
# symbol table; the no-PIE addresses are unchanged, so the shipped exploit's
# hard-coded addresses still match.
#
# The flag path USES the rdi argument: win() decrypts flag.enc with the key in
# rdi, so only 0xc0ffee yields the flag and returning past the check prints
# noise. flag.enc is produced here from flag.txt by mkenc, with the same cipher
# the binary decrypts with (cipher.h). The plaintext flag.txt stays in the repo
# (source of truth + tools/check-flags.py) but is NOT shipped in the container.
CC      := gcc
CFLAGS  := -O0 -Wall -Wextra -fno-stack-protector -U_FORTIFY_SOURCE -no-pie -Wno-stringop-overflow
LDFLAGS := -no-pie -s

all: clean binary flag.enc

binary: binary.c cipher.h
	$(CC) $(CFLAGS) $< -o $@ $(LDFLAGS)

# mkenc shares cipher.h with the binary; run it to (re)generate flag.enc.
flag.enc: mkenc.c cipher.h flag.txt
	$(CC) -O2 -Wall mkenc.c -o mkenc
	./mkenc
	rm -f mkenc

clean:
	rm -f binary mkenc
