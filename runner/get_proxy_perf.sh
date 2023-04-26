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
# Original file: https://github.com/istio/tools/blob/1.15.0/perf/benchmark/flame/get_proxy_perf.sh
# Changes made to adapt test runner to test setups.

# Exit immediately for non zero status
set -e
# Check unset variables
set -u
# Print commands
set -x

function usage() {
  echo "usage:
        ./get_proxy_perf.sh -p <pod_name> -n <pod_namespace> -d <duration> -f <sample_frequency> -a <perf_data_filename> -e <process_name> -r <results_dir>
    
    -p name of the pod.
    -n namespace of the given pod.
    -d time duration of profiling in second.
    -f sample frequency in Hz.
    -a perf data filename.
    -e process name.
    -r results directory."
  exit 1
}

while getopts p:n:d:f:a:e:r: arg ; do
  case "${arg}" in
    p) POD_NAME="${OPTARG}";;
    n) POD_NAMESPACE="${OPTARG}";;
    d) PERF_DURATION="${OPTARG}";;
    f) SAMPLE_FREQUENCY="${OPTARG}";;
    a) PERF_DATA_FILENAME="${OPTARG}";;
    e) PROCESS_NAME="${OPTARG}";;
    r) RESULTS_DIR="${OPTARG}";;
    *) usage;;
  esac
done

POD_NAME=${POD_NAME:?"pod name must be provided"}
POD_NAMESPACE=${POD_NAMESPACE:?"pod namespace must be provided"}
PERF_DURATION=${PERF_DURATION:-"20"}
SAMPLE_FREQUENCY=${SAMPLE_FREQUENCY:-"99"}
PERF_DATA_FILENAME=${PERF_DATA_FILENAME:?"perf data filename must be given"}
PROCESS_NAME=${PROCESS_NAME:?"process name must be given"}

WD=$(dirname "${0}")
WD=$(cd "${WD}" && pwd)

RESULTS_DIR=${RESULTS_DIR:-"${WD}/../data"}

echo "Copy profiling script ..."
kubectl cp "${WD}"/get_perfdata.sh "${POD_NAME}":/tmp/get_perfdata.sh -n "${POD_NAMESPACE}" -c ubuntu

echo "Start profiling ..."
kubectl exec "${POD_NAME}" -n "${POD_NAMESPACE}" -c ubuntu -- /tmp/get_perfdata.sh "${PERF_DATA_FILENAME}" "${PERF_DURATION}" "${SAMPLE_FREQUENCY}" "${PROCESS_NAME}"

PERF_FILE_NAME="${PERF_DATA_FILENAME}.perf"
SVG_FILE_NAME="${PERF_DATA_FILENAME}.svg"
PERF_FILE="${RESULTS_DIR}/${PERF_FILE_NAME}"
SVG_FILE="${RESULTS_DIR}/${SVG_FILE_NAME}"
kubectl cp "${POD_NAME}:/tmp/${PERF_DATA_FILENAME}.perf" "${PERF_FILE}" -n "${POD_NAMESPACE}" -c ubuntu

echo "Generating svg file ${SVG_FILE_NAME}"
"${WD}/flame.sh" "${PERF_FILE}" "${SVG_FILE}"
