FROM golang:1.19.2-alpine3.16 as builder
WORKDIR /src

COPY go.mod go.sum main.go ./
COPY demoservice ./demoservice

RUN go mod download
RUN go build -o /src/proxyless-http-server

FROM alpine:3.16.2
WORKDIR /app

COPY --from=builder /src/proxyless-http-server /app/proxyless-http-server

ENTRYPOINT ["/app/proxyless-http-server"]
