FROM debian:12

# gcc/libc stay in the image: it's a pwn box, and the player may want a compiler.
RUN apt update -y && apt install -y socat gcc libc6-dev tar && apt clean -y

RUN useradd -m ctf -u 1000

# SUID-root "log rotation" helper. It uses an absolute tar and a clean $PATH
# (the naive PATH hijack is closed), but runs the backup through `bash -c`, so
# $BASH_ENV is sourced as root -- a SUID-bash privesc. See challenge/helper.c
# and solution/README.md.
COPY helper.c /tmp/helper.c
RUN gcc -O2 -o /usr/local/bin/logrotate-helper /tmp/helper.c \
  && chown root:root /usr/local/bin/logrotate-helper \
  && chmod 4755 /usr/local/bin/logrotate-helper \
  && rm -f /tmp/helper.c \
  && mkdir -p /var/www /var/backups \
  && echo '<h1>VikeMerch internal</h1>' > /var/www/index.html

ADD bashrc /home/ctf/.bashrc
# Starts one listener per AI-modus effects level (see ENTRYPOINT); root's, not ctf's.
COPY listen.sh /opt/ai-modus/listen.sh
# The flag is readable only by root — no `cat` for the ctf user.
ADD flag.txt /root/flag.txt
RUN chown root:root /root/flag.txt && chmod 0400 /root/flag.txt && chmod 0700 /root \
  && chown root:ctf /home/ctf && chmod 0644 /home/ctf/.bashrc \
  && chmod 0555 /opt/ai-modus/listen.sh

USER 1000
# One port per effects level on the CTFd board (the board's nc command picks it),
# each handing the shell AI_FX=<level> for the bashrc's look: 4445 level 2 BURN
# (the default, host port 4446), 4447 level -1 WEB 1.0, 4448 level 3 AI HORROR,
# 4449 level 1 CALM. Same socat options on every port.
EXPOSE 4445 4447 4448 4449
ENTRYPOINT ["/opt/ai-modus/listen.sh", "EXEC:'/bin/bash -li',pty,stderr,setsid,sane", "4445=2", "4447=-1", "4448=3", "4449=1"]
