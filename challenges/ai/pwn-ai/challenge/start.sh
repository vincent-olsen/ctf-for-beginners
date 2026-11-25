#!/bin/sh
# AI-modus banner (same look as the CTFd lane), then the challenge itself. The
# binary is untouched: the exploit's addresses come from the exact file players
# download, and exec keeps it the process socat talks to.
#
# The look follows the effects level the player picked on the board, i.e. the port
# they connected to: listen.sh hands it over as AI_FX (-1 WEB 1.0, 1 CALM, 2 BURN,
# the default, 3 AI HORROR). Every level prints at once, with no sleep and nothing
# animated (the rain and fire stand still), so the prompt follows straight away.
# Solvers, solution/exploit.py included, wait for the word "enter" in "Speak,
# friend, and enter." before sending the payload, so no banner may contain "enter"
# in any letter case, not even inside another word: the rain is glyphs and digits.
banner() { # the AI-MODUS block letters, one colour (xterm-256) per row
  printf '\033[1;38;5;%sm%s\033[0m\n' \
    "$1" '   █████╗  ██╗        ███╗   ███╗  ██████╗  ██████╗  ██╗   ██╗ ███████╗' \
    "$2" '  ██╔══██╗ ██║        ████╗ ████║ ██╔═══██╗ ██╔══██╗ ██║   ██║ ██╔════╝' \
    "$3" '  ███████║ ██║ █████╗ ██╔████╔██║ ██║   ██║ ██║  ██║ ██║   ██║ ███████╗' \
    "$4" '  ██╔══██║ ██║ ╚════╝ ██║╚██╔╝██║ ██║   ██║ ██║  ██║ ██║   ██║ ╚════██║' \
    "$5" '  ██║  ██║ ██║        ██║ ╚═╝ ██║ ╚██████╔╝ ██████╔╝ ╚██████╔╝ ███████║' \
    "$6" '  ╚═╝  ╚═╝ ╚═╝        ╚═╝     ╚═╝  ╚═════╝  ╚═════╝   ╚═════╝  ╚══════╝'
}
fire() { # three rows of block fire under the banner, one colour per row
  printf '\033[1;38;5;%sm%s\033[0m\n' \
    "$1" '   ▒ ░ ░ ▒  ░░       ░▒   ░ ▒▒ ▒   ▒░░      ▒ ▒░  ░ ▒     ░▒░ ▒ ▒▒▒ ▒' \
    "$2" '  ░▓▓ ▓░▒▒▒▒▒▒▒▒▒░▓▓░▒▓▒▒▒░░ ▓ ▒▒░▓ ░ ▒▓▓▒░ ▒▒▒▒▓░░ ▒░░▓▒▒ ▒ ▓▓░░▒  ▒▒▒' \
    "$3" '  ▓█▓▓█▓███▓▓▓▓▓███▓█▓█████▓▓▓███▓█▓▓▓▓▓▓▓▓█▓████▓▓█▓█▓▓█▓█▓▓▓█▓▓▓██████'
}
case ${AI_FX:-2} in
  -1) # WEB 1.0: dialled into a 2003 BBS
    printf '\033[37m%s\033[0m\n' 'ATDT AI-MODUS 1247'
    printf '\033[1;97m%s\033[0m\n\n' 'CONNECT 2400'
    printf '\033[1;96;44m%s\033[0m\n' \
      ' ╔═════════════════════════════════════════════════════════════╗' \
      ' ║   AI-MODUS BBS  ·  door game: KEYMASTER.EXE  ·  2400 baud   ║' \
      ' ╚═════════════════════════════════════════════════════════════╝'
    echo
    printf '\033[1;93m%s\033[0m\n' '  ▄▀█ █     █▀▄▀█ █▀█ █▀▄ █ █ █▀' '  █▀█ █ ▀▀  █ ▀ █ █▄█ █▄▀ █▄█ ▄█'
    echo
    printf '\033[97m%s\033[0m\n\n' ' You are caller #001337 today. Good luck, traveller.'
    ;;
  1) # CALM: the banner alone
    banner 226 220 214 208 202 196
    printf '\n\033[1;38;5;196m%s\033[0m\033[38;5;180m%s\033[0m\n\n' '  THREAT 5/5' '  ai-pwn · pwn-ai · AI expected. Bring your assistant.'
    ;;
  3) # AI HORROR: pink, and very pleased to help
    printf '\033[38;5;213m%s\033[0m\n\033[2;38;5;213m%s\033[0m\n\033[38;5;213m%s\033[0m\n\n' \
      '       ✧  · ·∞   ◇  ·✧◆  ✧ ◆0       ✦ ·∞✧  ✦    ✧   0✦ 0✦   1  ·· ∞ ∞' \
      '     ◆ ◇  ◇ · 0   ·   ·  ·  ∞✦ ✧1 ∞0  ◆  ◆       0   0          ◇' \
      '      ✦111 ◆  ✦   ·      ✧◇    0◆       ✧ 1    ·       ✦  0·   ·  ✦0∞  1'
    printf '\033[1;38;5;213m%s\033[0m\n' '[ OK ] Certainly! Loading your delightful binary ✦' '[ OK ] Optimising vibes ........ IMMACULATE'
    printf '\033[1;38;5;201m%s\033[0m\n\n' '[WARN] I can see your payload'
    banner 219 213 207 201 165 129
    fire 219 201 129
    printf '\n\033[1;38;5;201m%s\033[0m\033[38;5;177m%s\033[0m\n\n' '  ✦ THREAT: DELIGHTFUL ✦' '  ai-pwn · pwn-ai · Powered by AI. I already read the binary for you.'
    ;;
  *) # BURN, the default: rain, boot lines, the banner on a burning strip
    printf '\033[38;5;46m%s\033[0m\n\033[2;38;5;46m%s\033[0m\n\033[38;5;46m%s\033[0m\n\n' \
      '  ﾂ 1       ｻ ｽ  ｼ  ｾ     7  ｵ  ﾁﾂｲ   4      5    06 1         ｶ  ｴ30' \
      '    ｲ   ｽ     8          ｵ  ｵ    ﾀ  ｺ ﾁ     ｸ       ﾂ        ｹ  ｸ   ﾁ' \
      '  0   ｷ  1ｺ  ｾ                    ﾁ     ｱ 5     ｲﾁ  9  2 ﾃ ｵ   ｳ  ｼｵﾁ ｵ'
    printf '\033[1;38;5;46m%s\033[0m\n' '[ OK ] ssh ai-modus@ctf' '[ OK ] loading difficulty ........ NIGHTMARE' '[WARN] humans alone: not recommended'
    echo
    banner 226 220 214 208 202 196
    fire 226 208 196
    printf '\n\033[1;38;5;196m%s\033[0m\033[38;5;180m%s\033[0m\n\n' '  THREAT 5/5' '  ai-pwn · pwn-ai · AI expected. Bring your assistant.'
    ;;
esac
# socat's "sane" pty runs the tty cooked: canonical line-editing, flow control
# (IXON treats the 0x11 in the pop rdi gadget 0x4011fe as XON) and IEXTEN all
# mangle bytes that occur in the ROP chain, ICRNL/INLCR/IGNCR would rewrite a
# 0x0d/0x0a, and ISTRIP would clear the 8th bit. Put the pty in fully raw INPUT
# mode so every payload byte reaches the binary verbatim.
#
# min 1 / time 0 (VMIN=1, VTIME=0): the read returns as soon as the first byte is
# available. vuln() reads once -- read(0, buf, 256) -- and the exploit sends the
# whole chain in a single burst, which socat hands to the pty in one write, so
# that one read collects the ~97 bytes together. Do NOT raise VMIN: a VMIN above
# the payload size (255 was tried) makes this single read over the socat pty
# return a TRUNCATED buffer -- only ~64 of the 72 padding bytes arrive, the ROP
# addresses never reach the binary, and the solve fails every time. Widening
# VTIME does not help; VMIN is the setting that decides it.
#
# OPOST stays on so the banner and flag still print tidily. The raw switch is
# what makes the byte-exact chain survive, so don't hide its failure: if it can't
# be set, warn (the message reaches the player and the container log) rather than
# silently dropping back to a cooked pty that mangles the exploit.
if ! stty -icanon -echo -isig -ixon -ixoff -iexten -icrnl -inlcr -igncr -istrip min 1 time 0; then
  echo '[ERR] could not set raw input mode; byte-exact payloads may be mangled' >&2
fi
exec /app/binary
