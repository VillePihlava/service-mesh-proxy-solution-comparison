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
# Original file: https://github.com/istio/tools/blob/1.15.0/perf/benchmark/runner/fortio.py
# Changes made to adapt test runner to test setups.

from __future__ import print_function
import json
import os
import shlex
import requests
from datetime import datetime
import calendar
import argparse
import subprocess
import tempfile
import prom
from subprocess import getoutput

"""
    returns data in a single line format
    Labels, StartTime, RequestedQPS, ActualQPS, NumThreads,
    min, max, p50, p75, p90, p99, p999
"""

NAMESPACE = "fortio"

def convert_data(data):
    obj = {}

    # These keys are generated from fortio default json file
    for key in "Labels,StartTime,RequestedQPS,ActualQPS,NumThreads,RunType,ActualDuration".split(
            ","):
        if key == "RequestedQPS" and data[key] == "max":
            obj[key] = 99999999
            continue
        if key in ["RequestedQPS", "ActualQPS"]:
            obj[key] = int(round(float(data[key])))
            continue
        if key == "ActualDuration":
            obj[key] = int(data[key] / 10 ** 9)
            continue
        # fill out other data key to obj key
        obj[key] = data[key]

    h = data["DurationHistogram"]
    obj["min"] = h["Min"]
    obj["max"] = h["Max"]
    obj["avg"] = h["Avg"]

    p = h["Percentiles"]
    for pp in p:
        obj["p" + str(pp["Percentile"])] = pp["Value"]

    success = 0
    if '200' in data["RetCodes"]:
        success = int(data["RetCodes"]["200"])

    # "Sizes" key is not in RunType: TCP
    if data["RunType"] == "HTTP":
        obj["errorPercent"] = 100 * \
            (int(data["Sizes"]["Count"]) - success) / int(data["Sizes"]["Count"])
        obj["Payload"] = int(data['Sizes']['Avg'])
    return obj


def fetch(url):
    data = None
    if url.startswith("http"):
        try:
            d = requests.get(url)
            if d.status_code != 200:
                return None
            # Add debugging info for JSON parsing error in perf pipeline (nighthawk)
            print("fetching data from fortioclient")
            print(d)
            data = d.json()
        except Exception:
            print("Error while fetching from " + url)
            raise
    else:
        data = json.load(open(url))

    return convert_data(data)

# number of seconds to skip after test begins.
METRICS_START_SKIP_DURATION = 15
# number of seconds to skip before test ends.
METRICS_END_SKIP_DURATION = 15

def run_command(command):
    process = subprocess.Popen(shlex.split(command))
    process.wait()


def sync_fortio(promUrl="", csv=None, csv_output="", namespace=NAMESPACE, json_output_dir="../data", resource_usage_targets=""):
    get_fortioclient_pod_cmd = "kubectl -n {namespace} get pods | grep fortioclient".format(namespace=namespace)
    fortioclient_pod_name = getoutput(get_fortioclient_pod_cmd).split(" ")[0]
    copy_json_to_results_cmd = "kubectl cp -c shell {namespace}/{fortioclient}:/var/lib/fortio {dir}"\
        .format(namespace=namespace, fortioclient=fortioclient_pod_name, dir=json_output_dir)
    run_command(copy_json_to_results_cmd)
    copy_access_logs_to_results_cmd = "kubectl cp -c shell {namespace}/{fortioclient}:/var/lib/access-logs {dir}"\
        .format(namespace=namespace, fortioclient=fortioclient_pod_name, dir=json_output_dir)
    run_command(copy_access_logs_to_results_cmd)

    with tempfile.TemporaryDirectory() as temp_dir_path:
        get_fortio_json_cmd = "kubectl cp -c shell {namespace}/{fortioclient}:/var/lib/fortio {tempdir}"\
            .format(namespace=namespace, fortioclient=fortioclient_pod_name, tempdir=temp_dir_path)
        run_command(get_fortio_json_cmd)

        data = []
        for filename in os.listdir(temp_dir_path):
            print(filename)
            with open(os.path.join(temp_dir_path, filename), 'r') as f:
                try:
                    data_dict = json.load(f, strict=False)
                    one_char = f.read(1)
                    if not one_char:
                        print("json file is not empty")
                except json.JSONDecodeError as e:
                    print(f.read())
                    while True:
                        line = f.readline()
                        print(line)
                        if "" == line:
                            print("file finished!")
                            break
                    print(e)

                gd = convert_data(data_dict)
                if gd is None:
                    continue
                st = gd['StartTime']

                if promUrl:
                    sd = datetime.strptime(st[:19], "%Y-%m-%dT%H:%M:%S")
                    print("Fetching prometheus metrics for", sd, gd["Labels"])
                    if gd.get('errorPercent', 0) > 10:
                        print("... Run resulted in", gd['errorPercent'], "% errors")
                        continue
                    min_duration = METRICS_START_SKIP_DURATION + METRICS_END_SKIP_DURATION
                    if min_duration > gd['ActualDuration']:
                        print("... {} duration={}s is less than minimum {}s".format(
                            gd["Labels"], gd['ActualDuration'], min_duration))
                        continue
                    prom_start = calendar.timegm(
                        sd.utctimetuple()) + METRICS_START_SKIP_DURATION
                    duration = gd['ActualDuration'] - min_duration
                    p = prom.Prom(promUrl, duration, start=prom_start, resource_usage_targets=resource_usage_targets, json_output_dir=json_output_dir, filename_suffix=filename)
                    prom_metrics = p.fetch_targets_cpu_and_mem()
                    if not prom_metrics:
                        print("... Not found")
                        continue
                    else:
                        print("")

                    gd.update(prom_metrics)

                data.append(gd)

    if csv is not None:
        write_csv(csv, data, csv_output)

    return 0

def write_csv(keys, data, csv_output):
    if csv_output is None or csv_output == "":
        fd, csv_output = tempfile.mkstemp(suffix=".csv")
        out = os.fdopen(fd, "wt")
    else:
        out = open(csv_output, "w+")

    lst = keys.split(',')
    out.write(keys + "\n")

    for gd in data:
        row = []
        for key in lst:
            row.append(str(gd.get(key, '-')))

        out.write(','.join(row) + "\n")

    out.close()
    print("Wrote {} csv records to {}".format(len(data), csv_output))

def main(argv):
    args = get_parser().parse_args(argv)
    return sync_fortio(
        args.prometheus,
        args.csv,
        args.csv_output,
        NAMESPACE,
        args.json_output_dir,
        args.resource_usage_targets)


def get_parser():
    parser = argparse.ArgumentParser("Fetch and upload results to bigQuery")
    parser.add_argument(
        "--csv",
        help="columns in the csv file",
        default="StartTime,ActualDuration,Labels,NumThreads,RequestedQPS,ActualQPS,errorPercent,avg,min,max,p50,p90,p99,p99.9,"
                "cpu_milli_avg_main_fortioclient,cpu_milli_avg_http-server_http-server,cpu_milli_avg_demo-service_demo-service,"
                "cpu_milli_avg_istio-proxy_istio-ingressgateway,cpu_milli_avg_istio-proxy_http-server,cpu_milli_avg_istio-proxy_demo-service,cpu_milli_avg_cilium_cilium-agent,"
                "mem_MiB_avg_main_fortioclient,mem_MiB_avg_http-server_http-server,mem_MiB_avg_demo-service_demo-service,"
                "mem_MiB_avg_istio-proxy_istio-ingressgateway,mem_MiB_avg_istio-proxy_http-server,mem_MiB_avg_istio-proxy_demo-service,mem_MiB_avg_cilium_cilium-agent")
    parser.add_argument(
        "--csv_output",
        help="output path of csv file",
        required=True)
    parser.add_argument(
        "--prometheus",
        help="url to fetch prometheus results from. if blank, will only output Fortio metrics.",
        required=True)
    parser.add_argument(
        "--json_output_dir",
        help="output directory of json file",
        required=True)
    parser.add_argument(
        "--resource_usage_targets",
        help="resource usage targets",
        required=True)
    return parser


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
