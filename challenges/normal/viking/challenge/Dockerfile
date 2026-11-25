FROM golang:1.27.3-alpine AS builder

RUN apk update && apk add xxd sqlite tar xz

WORKDIR /zig

ADD --checksum=sha256:2d00e789fec4f71790a6e7bf83ff91d564943c5ee843c5fd966efc474b423047 https://ziglang.org/download/0.11.0/zig-linux-x86_64-0.11.0.tar.xz zig.tar.xz
RUN tar -xf zig.tar.xz
RUN mv zig-linux-x86_64-0.11.0/* . && rmdir zig-linux-x86_64-0.11.0

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY views/ ./views/
COPY main.go ./

# zig cc is for static CGO binaries
RUN CGO_ENABLED=1 GOOS=linux \
    CC="/zig/zig cc -target native-native-musl" \
    CXX="/zig/zig cc -target native-native-musl" \
    go build -v -o vikemerch .

COPY seed.sh ./
RUN ./seed.sh

RUN rm -rf seed.sh


FROM scratch 

COPY --from=alpine:3.21 /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

WORKDIR /app

COPY assets/ ./assets/

COPY --from=builder /app/ .

ENV FLAG="flag{1m_th3_fl4g_u_4r3_l00k1ng_f0r}"

# scratch has no /etc/passwd: run unprivileged as nobody, by number.
USER 65534:65534

EXPOSE 8080

CMD ["./vikemerch"]
