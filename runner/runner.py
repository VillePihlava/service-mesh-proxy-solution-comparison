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
# Original file: https://github.com/istio/tools/blob/1.15.0/perf/benchmark/runner/runner.py
# Changes made to adapt test runner to test setups.

from __future__ import print_function

import collections
import os
import json
import argparse
import subprocess
import shlex
import uuid
import sys
import multiprocessing
from subprocess import getoutput
from fortio import METRICS_START_SKIP_DURATION, METRICS_END_SKIP_DURATION

APPLICATION_NAMESPACE = "default"
LOADGENERATOR_NAMESPACE = "fortio"
KUBE_SYSTEM_NAMESPACE = "kube-system"
POD = collections.namedtuple('Pod', ['name', 'namespace', 'ip', 'labels'])
processes = []

def pod_info(filterstr="", namespace=APPLICATION_NAMESPACE, multi_ok=True):
    cmd = "kubectl -n {namespace} get pod {filterstr}  -o json".format(
        namespace=namespace, filterstr=filterstr)
    op = getoutput(cmd)
    o = json.loads(op)
    items = o['items']

    if not multi_ok and len(items) > 1:
        raise Exception("more than one found " + op)

    if not items:
        raise Exception("no pods found with command [" + cmd + "]")

    i = items[0]
    return POD(i['metadata']['name'], i['metadata']['namespace'],
               i['status']['podIP'], i['metadata']['labels'])


def run_command(command):
    process = subprocess.Popen(shlex.split(command))
    process.wait()

def kubectl_exec(pod, remote_cmd, runfn=run_command, namespace=LOADGENERATOR_NAMESPACE, container=None):
    c = ""
    if container is not None:
        c = "-c " + container
    cmd = "kubectl --namespace {namespace} exec {pod} {c} -- {remote_cmd}".format(
        pod=pod,
        remote_cmd=remote_cmd,
        c=c,
        namespace=namespace)
    print(cmd, flush=True)
    runfn(cmd)

class Fortio:
    def __init__(
            self,
            conn=None,
            qps=None,
            duration=None,
            frequency=None,
            perf_targets=None,
            extra_labels=None,
            results_dir=None,
            url=""):
        self.run_id = str(uuid.uuid4()).partition('-')[0]
        self.conn = conn
        self.qps = qps
        self.duration = duration
        self.frequency = frequency
        self.perf_targets = perf_targets
        self.extra_labels = extra_labels
        self.labels = self.generate_test_labels()
        self.results_dir = results_dir
        self.url = url
        # bucket resolution in seconds
        self.r = "0.001"
        self.http_server = pod_info("-lapp.kubernetes.io/name=http-server", namespace=APPLICATION_NAMESPACE)
        self.demo_service = pod_info("-lapp.kubernetes.io/name=demo-service", namespace=APPLICATION_NAMESPACE)
        self.client = pod_info("-lapp.kubernetes.io/name=loadgenerator", namespace=LOADGENERATOR_NAMESPACE)

    def generate_test_labels(self):
        labels = self.run_id
        labels += "_qps_" + str(self.qps)
        labels += "_c_" + str(self.conn)
        labels += "_d_" + str(self.duration)
        labels += "_" + self.extra_labels
        return labels

    def generate_fortio_cmd(self):
        fortio_cmd = (
            "fortio load -uniform -nocatchup -c {conn} -qps {qps} -t {duration}s -a -r {r} "
            "-httpbufferkb=128 -labels {labels} -access-log-file {access_log_file} {url}").format(
            conn=self.conn,
            qps=self.qps,
            duration=self.duration,
            r=self.r,
            labels=self.labels,
            access_log_file="/var/lib/access-logs/access-log-file_" + self.extra_labels + ".json",
            url=self.url)
        return fortio_cmd

    def run(self):
        print('-------------- Running test --------------')
        p = multiprocessing.Process(target=kubectl_exec,
                                    args=[self.client.name, self.generate_fortio_cmd()])
        p.start()
        processes.append(p)

        if self.perf_targets != "":
            perf_target_list = self.perf_targets.split(",")

            for perf_target in perf_target_list:
                perf_target_elements = perf_target.split("_")
                perf_label = self.labels + "_f_" + str(self.frequency) + "_t_" + perf_target
                
                if perf_target_elements[0] == "http-server":
                    p = multiprocessing.Process(target=run_perf,
                                                args=[self.http_server.name, perf_label, self.duration, self.frequency, APPLICATION_NAMESPACE, perf_target_elements[1], self.results_dir])
                    p.start()
                    processes.append(p)
                elif perf_target_elements[0] == "demo-service":
                    p = multiprocessing.Process(target=run_perf,
                                                args=[self.demo_service.name, perf_label, self.duration, self.frequency, APPLICATION_NAMESPACE, perf_target_elements[1], self.results_dir])
                    p.start()
                    processes.append(p)
                else:
                    p = multiprocessing.Process(target=run_perf,
                                                args=[perf_target_elements[0], perf_label, self.duration, self.frequency, KUBE_SYSTEM_NAMESPACE, perf_target_elements[1], self.results_dir])
                    p.start()
                    processes.append(p)

        for process in processes:
            process.join()

LOCAL_FLAMEDIR = os.path.dirname(os.path.abspath(__file__))
PERF_PROXY_FILE = "/get_proxy_perf.sh"
LOCAL_FLAME_PROXY_FILE_PATH = LOCAL_FLAMEDIR + PERF_PROXY_FILE

def run_perf(pod, labels, duration, frequency, namespace, process_name, results_dir):
    exitcode, res = subprocess.getstatusoutput(LOCAL_FLAME_PROXY_FILE_PATH +
                                               " -p {pod} -n {namespace} -d {duration} -f {frequency} -a {perf_data_filename} -e {process_name} -r {results_dir}".format(
                                                   pod=pod, namespace=namespace, duration=duration, frequency=frequency, perf_data_filename=labels, process_name=process_name, results_dir=results_dir))

    print("run flame graph status: {}".format(exitcode))
    print("flame graph script output: {}".format(res.strip()))

def run_perf_test(args):
    min_duration = METRICS_START_SKIP_DURATION + METRICS_END_SKIP_DURATION

    fortio = Fortio(
        conn=args.conn,
        qps=args.qps,
        duration=args.duration,
        frequency=args.frequency,
        perf_targets=args.perf_targets,
        extra_labels=args.extra_labels,
        results_dir=args.results_dir,
        url=args.url)

    if fortio.duration <= min_duration:
        print("Duration must be greater than {min_duration}".format(
            min_duration=min_duration))
        exit(1)

    fortio.run()

def get_parser():
    parser = argparse.ArgumentParser("Run performance test")
    parser.add_argument(
        "--conn",
        help="number of connections",
        type=int,
        required=True)
    parser.add_argument(
        "--qps",
        help="qps, comma separated list",
        type=int,
        required=True)
    parser.add_argument(
        "--duration",
        help="duration in seconds of the extract",
        type=int,
        required=True)
    parser.add_argument(
        "--frequency",
        help="sampling frequency of generating flame graph",
        type=int,
        default=99)
    parser.add_argument(
        "--perf_targets",
        help="perf targets",
        default="")
    parser.add_argument(
        "--extra_labels",
        help="extra labels",
        default="")
    parser.add_argument(
        "--results_dir",
        help="results directory",
        required=True)
    parser.add_argument(
        "--url",
        help="url that Fortio will connect to",
        required=True)

    return parser

def main(argv):
    args = get_parser().parse_args(argv)
    return run_perf_test(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
