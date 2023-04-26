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
# Original file: https://github.com/istio/tools/blob/1.15.0/perf/benchmark/runner/prom.py
# Changes made to adapt test runner to test setups.

from __future__ import print_function
import datetime
import calendar
import requests
import json
import argparse


def calculate_average(item, resource_type):
    data_points_list = item["values"]
    data_sum = 0
    for data_point in data_points_list:
        data_sum += float(data_point[1])
    data_avg = float(data_sum / len(data_points_list))
    if resource_type == "cpu":
        return to_milli_cpus(data_avg)
    else:
        return to_mebibytes(data_avg)


def get_average_within_query_time_range(data, resource_type):
    val_by_pod_name = {"main_fortioclient": -1, "istio-proxy_istio-ingressgateway": -1,
                       "http-server_http-server": -1, "demo-service_demo-service": -1,
                       "istio-proxy_http-server": -1, "istio-proxy_demo-service": -1,
                       "cilium_cilium-agent": -1}
    if data["data"]["result"]:
        for item in data["data"]["result"]:
            item_metric = item["metric"]
            if "pod" in item_metric and "container" in item_metric:
                pod_name = item_metric["pod"]
                container_name = item["metric"]["container"]
                if "fortioclient" in pod_name and "main" == container_name:
                    val_by_pod_name["main_fortioclient"] = calculate_average(item, resource_type)
                if "istio-ingressgateway" in pod_name and "istio-proxy" == container_name:
                    val_by_pod_name["istio-proxy_istio-ingressgateway"] = calculate_average(item, resource_type)
                if "http-server" in pod_name and "http-server" == container_name:
                    val_by_pod_name["http-server_http-server"] = calculate_average(item, resource_type)
                if "http-server" in pod_name and "istio-proxy" == container_name:
                    val_by_pod_name["istio-proxy_http-server"] = calculate_average(item, resource_type)
                if "demo-service" in pod_name and "demo-service" == container_name:
                    val_by_pod_name["demo-service_demo-service"] = calculate_average(item, resource_type)
                if "demo-service" in pod_name and "istio-proxy" == container_name:
                    val_by_pod_name["istio-proxy_demo-service"] = calculate_average(item, resource_type)
                if "cilium" in pod_name and "cilium-agent" == container_name:
                    val_by_pod_name["cilium_cilium-agent"] = calculate_average(item, resource_type)
    return val_by_pod_name

def convert_data_list(item, resource_type):
    data_points_list = item["values"]
    output_list = []
    for data_point in data_points_list:
        value = -1
        if resource_type == "cpu":
            value = to_milli_cpus(float(data_point[1]))
        else:
            value = to_mebibytes(float(data_point[1]))
        output_list.append({"timestamp": data_point[0], "value": value})
    return output_list

def save_to_file_datasets_within_query_time_range(data, resource_type, json_output_dir, filename_suffix, query_url):
    val_by_pod_name = {"main_fortioclient": [], "istio-proxy_istio-ingressgateway": [],
                       "http-server_http-server": [], "demo-service_demo-service": [],
                       "istio-proxy_http-server": [], "istio-proxy_demo-service": [],
                       "cilium_cilium-agent": [],
                       "query_url": query_url}
    if data["data"]["result"]:
        for item in data["data"]["result"]:
            item_metric = item["metric"]
            if "pod" in item_metric and "container" in item_metric:
                pod_name = item_metric["pod"]
                container_name = item["metric"]["container"]
                if "fortioclient" in pod_name and "main" == container_name:
                    val_by_pod_name["main_fortioclient"] = convert_data_list(item, resource_type)
                if "istio-ingressgateway" in pod_name and "istio-proxy" == container_name:
                    val_by_pod_name["istio-proxy_istio-ingressgateway"] = convert_data_list(item, resource_type)
                if "http-server" in pod_name and "http-server" == container_name:
                    val_by_pod_name["http-server_http-server"] = convert_data_list(item, resource_type)
                if "http-server" in pod_name and "istio-proxy" == container_name:
                    val_by_pod_name["istio-proxy_http-server"] = convert_data_list(item, resource_type)
                if "demo-service" in pod_name and "demo-service" == container_name:
                    val_by_pod_name["demo-service_demo-service"] = convert_data_list(item, resource_type)
                if "demo-service" in pod_name and "istio-proxy" == container_name:
                    val_by_pod_name["istio-proxy_demo-service"] = convert_data_list(item, resource_type)
                if "cilium" in pod_name and "cilium-agent" == container_name:
                    val_by_pod_name["cilium_cilium-agent"] = convert_data_list(item, resource_type)
    
    # Save to file
    filename = json_output_dir + "/" + resource_type + "-usage_" + filename_suffix
    with open(filename, "w+") as output_file:
        print(filename)
        output_file.write(json.dumps(val_by_pod_name, indent=2))

class Prom:
    # url: base url for prometheus
    def __init__(
            self,
            url,
            nseconds,
            end=None,
            host=None,
            start=None,
            aggregate=True,
            resource_usage_targets="",
            json_output_dir="",
            filename_suffix=""):
        self.url = url
        self.nseconds = nseconds
        self.resource_usage_targets=resource_usage_targets
        self.json_output_dir=json_output_dir
        self.filename_suffix=filename_suffix
        if start is None:
            end = end or 0
            self.end = calendar.timegm(
                datetime.datetime.utcnow().utctimetuple()) - end
            self.start = self.end - nseconds
        else:
            self.start = start
            self.end = start + nseconds

        self.headers = {}
        if host is not None:
            self.headers["Host"] = host
        self.aggregate = aggregate

    def fetch_container_cpu_usage(self):
        cpu_query = 'rate(container_cpu_usage_seconds_total[1m])'
        data, query_url = self.fetch_by_query(cpu_query)
        save_to_file_datasets_within_query_time_range(data, "cpu", self.json_output_dir, self.filename_suffix, query_url)
        avg_cpu_dict = get_average_within_query_time_range(data, "cpu")
        return avg_cpu_dict

    def fetch_container_memory_usage(self):
        mem_query = 'container_memory_usage_bytes'
        data, query_url = self.fetch_by_query(mem_query)
        save_to_file_datasets_within_query_time_range(data, "mem", self.json_output_dir, self.filename_suffix, query_url)
        avg_mem_dict = get_average_within_query_time_range(data, "mem")
        return avg_mem_dict

    def fetch_targets_cpu_and_mem(self):
        out = {}

        avg_cpu_dict = self.fetch_container_cpu_usage()
        avg_mem_dict = self.fetch_container_memory_usage()

        out["cpu_milli_avg_main_fortioclient"] = avg_cpu_dict["main_fortioclient"]
        out["cpu_milli_avg_http-server_http-server"] = avg_cpu_dict["http-server_http-server"]
        out["cpu_milli_avg_demo-service_demo-service"] = avg_cpu_dict["demo-service_demo-service"]
        out["mem_MiB_avg_main_fortioclient"] = avg_mem_dict["main_fortioclient"]
        out["mem_MiB_avg_http-server_http-server"] = avg_mem_dict["http-server_http-server"]
        out["mem_MiB_avg_demo-service_demo-service"] = avg_mem_dict["demo-service_demo-service"]

        if self.resource_usage_targets == "cilium":
            out["cpu_milli_avg_cilium_cilium-agent"] = avg_cpu_dict["cilium_cilium-agent"]
            out["mem_MiB_avg_cilium_cilium-agent"] = avg_mem_dict["cilium_cilium-agent"]
        elif self.resource_usage_targets == "baseline":
            out["cpu_milli_avg_istio-proxy_istio-ingressgateway"] = avg_cpu_dict["istio-proxy_istio-ingressgateway"]
            out["mem_MiB_avg_istio-proxy_istio-ingressgateway"] = avg_mem_dict["istio-proxy_istio-ingressgateway"]
        else: # sidecar-istio or proxyless-istio
            out["cpu_milli_avg_istio-proxy_http-server"] = avg_cpu_dict["istio-proxy_http-server"]
            out["cpu_milli_avg_istio-proxy_demo-service"] = avg_cpu_dict["istio-proxy_demo-service"]
            out["cpu_milli_avg_istio-proxy_istio-ingressgateway"] = avg_cpu_dict["istio-proxy_istio-ingressgateway"]
            out["mem_MiB_avg_istio-proxy_http-server"] = avg_mem_dict["istio-proxy_http-server"]
            out["mem_MiB_avg_istio-proxy_demo-service"] = avg_mem_dict["istio-proxy_demo-service"]
            out["mem_MiB_avg_istio-proxy_istio-ingressgateway"] = avg_mem_dict["istio-proxy_istio-ingressgateway"]

        return out

    def fetch_by_query(self, query):
        resp = requests.get(self.url + "/api/v1/query_range", {
            "query": query,
            "start": self.start,
            "end": self.end,
            "step": 15
        }, headers=self.headers)
        print(resp.request.url)

        if not resp.ok:
            raise Exception(str(resp))

        return resp.json(), resp.request.url

# convert float bytes to mebibytes
def to_mebibytes(mem):
    return float(mem / (1024 * 1024))


# convert float cpus to int milli cpus
def to_milli_cpus(cpu):
    return float(cpu * 1000.0)


def main(argv):
    args = get_parser().parse_args(argv)
    p = Prom(args.url, args.nseconds, end=args.end,
             host=args.host)
    out = p.fetch_targets_cpu_and_mem()
    print(json.dumps(out, indent=args.indent))    

def get_parser():
    parser = argparse.ArgumentParser(
        "Fetch cpu and memory stats from prometheus")
    parser.add_argument("url", help="prometheus base url")
    parser.add_argument(
        "nseconds", help="duration in seconds of the extract", type=int)
    parser.add_argument(
        "--end",
        help="relative time in seconds from now to end collection",
        type=int,
        default=0)
    parser.add_argument(
        "--host",
        help="host header when collection is thru ingress",
        default=None)
    parser.add_argument(
        "--indent", help="pretty print json with indent", default=None)

    return parser


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
