FROM golang:1.27.3-bookworm AS build
WORKDIR /src
COPY go.mod .
COPY main.go .
# Product pictures (same as the original viking shop), embedded into the binary.
COPY assets/ assets/
RUN CGO_ENABLED=0 go build -trimpath -o /viking-ai .

FROM debian:12-slim
RUN useradd -m app
COPY --from=build /viking-ai /usr/local/bin/viking-ai
# The real flag lives here (not in distfiles); the app reads ./flag.txt at start.
COPY flag.txt /app/flag.txt
WORKDIR /app
USER app
EXPOSE 5000
CMD ["viking-ai"]
