#!/bin/sh
# One socat listener per AI-modus effects level, all in this one container: the
# CTFd board points a player's nc command at the port of the level they picked.
#
#   listen.sh '<socat address to run>' <port>=<level> ...
#
# Every connection to <port> runs the address with AI_FX=<level> in its
# environment (-1 WEB 1.0, 1 CALM, 2 BURN, 3 AI HORROR), and the banner picks its
# look from that. A listener that stops (or that someone with a shell here kills)
# is back a second later; docker stop (TERM) ends them all.
set -u
addr=$1
shift
trap 'trap - TERM INT; kill 0 2>/dev/null; exit 0' TERM INT
for spec in "$@"; do
  (
    port=${spec%%=*}
    level=${spec#*=}
    while :; do
      # A script's background job starts with Ctrl-C and Ctrl-\ ignored, which
      # would carry over into every player's session: give socat the defaults.
      AI_FX=$level env --default-signal socat -T900 "TCP-LISTEN:$port,reuseaddr,fork" "$addr"
      echo "listen.sh: the listener on port $port stopped (exit $?); restarting it" >&2
      sleep 1
    done
  ) &
done
wait
