// Copyright (C) 2023 Ville Pihlava
// SPDX-License-Identifier: MIT

package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"os"

	pb "proxy-comparison/demo-service/demoservice"

	"google.golang.org/grpc"

	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/credentials/insecure"
	xdscredentials "google.golang.org/grpc/credentials/xds"
	"google.golang.org/grpc/xds"
)

var serverCredentials credentials.TransportCredentials

type concatenationServiceServer struct {
	pb.UnimplementedConcatenationServiceServer
}

func (s *concatenationServiceServer) Concatenate(ctx context.Context, concatenationRequest *pb.ConcatenationRequest) (*pb.ConcatenatedString, error) {
	return &pb.ConcatenatedString{Str: concatenationRequest.Str1 + concatenationRequest.Str2}, nil
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		log.Fatal("PORT environment variable must be set.")
	}

	log.Printf("PORT: %s", port)

	var err error
	serverCredentials, err = xdscredentials.NewServerCredentials(xdscredentials.ServerOptions{FallbackCreds: insecure.NewCredentials()})
	if err != nil {
		log.Fatal(err)
	}

	lis, err := net.Listen("tcp", fmt.Sprintf(":%s", port))
	if err != nil {
		log.Fatal(err)
	}

	grpcServer := xds.NewGRPCServer(grpc.Creds(serverCredentials))
	pb.RegisterConcatenationServiceServer(grpcServer, &concatenationServiceServer{})
	err = grpcServer.Serve(lis)
	if err != nil {
		log.Fatal(err)
	}
}
