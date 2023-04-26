FROM golang:1.19.2-alpine3.16 as builder
WORKDIR /src

COPY go.mod go.sum main.go ./
COPY demoservice ./demoservice

RUN go mod download
RUN go build -o /src/proxyless-demo-service

FROM alpine:3.16.2
WORKDIR /app

COPY --from=builder /src/proxyless-demo-service /app/proxyless-demo-service

ENTRYPOINT ["/app/proxyless-demo-service"]
