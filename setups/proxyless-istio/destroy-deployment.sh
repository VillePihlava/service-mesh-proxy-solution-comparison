#!/usr/bin/env bash

# Copyright (C) 2023 Ville Pihlava
# SPDX-License-Identifier: MIT

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"

kubectl delete -f "${SCRIPT_DIR}/manifests"
istioctl uninstall --purge -y
helm uninstall -n monitoring prometheus
