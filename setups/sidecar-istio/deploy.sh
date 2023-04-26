#!/usr/bin/env bash

# Copyright (C) 2023 Ville Pihlava
# SPDX-License-Identifier: MIT

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"

if [[ -z "${REGISTRY}" ]]; then
    echo "\$REGISTRY must be set"
    exit 1
fi

helm install prometheus prometheus-community/prometheus --version 15.13.0 -f prometheus-chart-values.yaml --namespace monitoring --create-namespace

istioctl install -y -f "${SCRIPT_DIR}/sidecar-istio-configuration.yaml"

envsubst < "${SCRIPT_DIR}/manifests/deployment.yaml" | kubectl apply -f -
kubectl apply -f "${SCRIPT_DIR}/manifests/istio-gw-vs.yaml"
kubectl create ns fortio
kubectl apply -f "${SCRIPT_DIR}/manifests/fortio-loadgenerator.yaml"