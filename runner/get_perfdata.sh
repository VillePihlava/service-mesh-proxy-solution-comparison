#!/bin/bash

# Copyright Istio Authors
# Copyright (C) 2023 Ville Pihlava
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Source project of original file: https://github.com/istio/tools
# Original file: https://github.com/istio/tools/blob/1.15.0/perf/benchmark/flame/get_perfdata.sh
# Changes made to adapt test runner to test setups.

# Exit immediately for non zero status
set -e
# Check unset variables
set -u
# Print commands
set -x

WD="/tmp"

PERF_FILENAME=${1:?"perf filename is missing"}
PERF_DURATION=${2:?"perf duration is missing"}
SAMPLE_FREQUENCY=${3:-"99"}
PROCESS_NAME=${4:?"process name is missing"}

PID=$(pgrep ${PROCESS_NAME})

perf record -o "${WD}/${PERF_FILENAME}" -F "${SAMPLE_FREQUENCY}" -p "${PID}" -g -- sleep "${PERF_DURATION}"
perf script -i "${WD}/${PERF_FILENAME}" --demangle > "${WD}/${PERF_FILENAME}.perf"

echo "Wrote ${WD}/${PERF_FILENAME}.perf"
