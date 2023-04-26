#!/usr/bin/env bash

# Copyright (C) 2023 Ville Pihlava
# SPDX-License-Identifier: MIT

protoc --proto_path ../../protobuf --go_out=. --go-grpc_out=. \
    --go_opt=Mdemoservice.proto=./demoservice --go-grpc_opt=Mdemoservice.proto=./demoservice \
    demoservice.proto