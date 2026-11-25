FROM debian:13-slim
RUN apt-get update && apt-get install -y --no-install-recommends socat  && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY binary /app/binary
COPY flag.txt /app/flag.txt
# /app stays root's, so whoever gets code execution as ctf in this shared container
# can't change or remove the binary or the flag; ctf reads the flag through its group.
RUN useradd -m ctf && chmod 0555 /app/binary && if [ -f /app/flag.txt ];  \
    then chown root:ctf /app/flag.txt && chmod 0440 /app/flag.txt; fi
USER ctf
EXPOSE 1234
CMD ["socat","-T900","TCP-LISTEN:1234,reuseaddr,fork","EXEC:/app/binary,stderr"]
