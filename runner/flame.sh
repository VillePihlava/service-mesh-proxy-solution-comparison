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
# Original file: https://github.com/istio/tools/blob/1.15.0/perf/benchmark/flame/flame.sh
# Changes made to adapt test runner to test setups.

# Exit immediately for non zero status
set -e
# Check unset variables
set -u
# Print commands
set -x

WD=$(dirname "${0}")
WD=$(cd "${WD}" && pwd)

FLAMEDIR="${WD}/../../FlameGraph"

# Given output of `perf script` produce a flamegraph
FILE=${1:?"get_perfdata script output"}

SVG_FILE_NAME=${2:?"svg output file name"}

"${FLAMEDIR}/stackcollapse-perf.pl" "${FILE}" | "${FLAMEDIR}/flamegraph.pl" > "${SVG_FILE_NAME}"

echo "Wrote CPU flame graph ${SVG_FILE_NAME}"

