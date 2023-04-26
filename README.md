# Service mesh proxy solution comparison setups and data

This repository contains setups and data related to my master's thesis: "Comparing service mesh proxy solutions". I compared Istio, Istio gRPC proxyless, and Cilium.

## setups

This directory contains setups for Istio, Istio gRPC proxyless, and Cilium in separate directories. Instructions for using the setups can be found in each setup's directory.

## runner

This directory contains script files required for running the tests. The files have been modified from test files used in the https://github.com/istio/tools project.

## src

This directory contains source files for the containers used in the setups. Normal and proxyless versions of the http-server and demo-service exist in separate directories.

## data

This directory contains the results generated from the setups.
