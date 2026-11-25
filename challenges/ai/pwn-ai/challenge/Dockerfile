FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends socat \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
# Ship and run the exact same binary players receive (addresses must match).
COPY binary /app/binary
# Prints the AI-modus banner, then execs the binary.
COPY start.sh /app/start.sh
# Starts one listener per AI-modus effects level (see ENTRYPOINT).
COPY listen.sh /app/listen.sh
# The flag exists on the server ONLY in encrypted form (flag.enc). The binary
# decrypts it with the key passed in rdi, so the plaintext flag.txt is never put
# in the image: only the right exploit (0xc0ffee in rdi) turns it back into the
# flag. flag.enc is built from flag.txt by the Makefile (mkenc), not here.
COPY flag.enc /app/flag.enc

# /app stays root's, so whoever gets code execution as ctf in this shared container
# can't change or remove the binary or the flag; ctf reads flag.enc through its group.
RUN useradd -m ctf \
  && chmod 0555 /app/binary /app/start.sh /app/listen.sh \
  && chown root:ctf /app/flag.enc && chmod 0440 /app/flag.enc

USER ctf
# One port per effects level on the CTFd board (the board's nc command picks it),
# each running start.sh with AI_FX=<level> for the banner's look: 1234 level 2 BURN
# (the default, host port 1246), 1247 level -1 WEB 1.0, 1248 level 3 AI HORROR,
# 1249 level 1 CALM. listen.sh gives every port the same socat options (-T900 and
# the EXEC address below).
EXPOSE 1234 1247 1248 1249
# ixon=0,ixoff=0,iexten=0: the ROP chain contains 0x11 (XON) and 0x12 bytes, which
# a "sane" pty with flow-control/IEXTEN on would swallow. socat sets these on the
# pty before start.sh runs, so a payload sent the instant the client connects (not
# only one that waits for the prompt) still arrives intact. start.sh then puts the
# pty in fully raw input mode before exec'ing the binary.
ENTRYPOINT ["/app/listen.sh", "EXEC:'/app/start.sh',pty,stderr,setsid,sane,ixon=0,ixoff=0,iexten=0", "1234=2", "1247=-1", "1248=3", "1249=1"]
