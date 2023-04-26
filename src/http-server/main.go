// Copyright (C) 2023 Ville Pihlava
// SPDX-License-Identifier: MIT

package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"

	pb "proxy-comparison/http-server/demoservice"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

var demoServiceAddress string
var conn *grpc.ClientConn
var client pb.ConcatenationServiceClient

func handler(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	str1 := "This string will be concatenated "
	str2 := "with this string!\n"

	concatenatedString, err := client.Concatenate(ctx, &pb.ConcatenationRequest{Str1: str1, Str2: str2})
	if err != nil {
		log.Print(err)
		http.Error(w, http.StatusText(http.StatusInternalServerError), http.StatusInternalServerError)
		return
	}

	fmt.Fprintf(w, concatenatedString.GetStr())
	log.Printf("Succesful request from: %s, to: %s", r.RemoteAddr, r.Host)
}

func main() {
	http.HandleFunc("/", handler)

	port := os.Getenv("PORT")
	if port == "" {
		log.Fatal("PORT environment variable must be set.")
	}

	demoServiceAddress = os.Getenv("DEMO_SERVICE_ADDRESS")
	if demoServiceAddress == "" {
		log.Fatal("DEMO_SERVICE_ADDRESS environment variable must be set.")
	}

	log.Printf("DEMO_SERVICE_ADDRESS: %s", demoServiceAddress)
	log.Printf("PORT: %s", port)

	var err error
	conn, err = grpc.DialContext(context.Background(), demoServiceAddress, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Print(err)
		return
	}
	defer conn.Close()

	client = pb.NewConcatenationServiceClient(conn)

	err = http.ListenAndServe(fmt.Sprintf(":%s", port), nil)
	if err != nil {
		log.Fatal(err)
	}
}
