# Setup instructions

1. Create a cluster with: `kubeadm init --config cluster-configuration.yaml`
2. Install Calico with:
 * `curl https://raw.githubusercontent.com/projectcalico/calico/v3.24.5/manifests/calico.yaml -LO`
 * `kubectl apply -f calico.yaml`
3. Enable Istio injection (this is required even for the proxyless setup): `kubectl label namespace default istio-injection=enabled`
4. Use `deploy.sh` to deploy the test setup (set $REGISTRY). This also enables mTLS.

5. Run test script `runner/runner.py` to run test, for example:
```console
python3 runner.py --qps 100 --duration 300 --conn 10 --perf_targets "http-server_proxyless-http,http-server_pilot-agent,demo-service_proxyless-demo,demo-service_pilot-agent" --extra_labels "proxyless-istio-1" --results_dir "../data/proxyless-istio/flame" --url http://istio-ingressgateway.istio-system/
```

6. Run script `runner/fortio.py` to generate csv, for example:
```console
python3 fortio.py --csv_output "../data/proxyless-istio/proxyless-istio-summary.csv" --json_output_dir "../data/proxyless-istio/json" --resource_usage_targets="proxyless-istio" --prometheus="http://127.0.0.1:32592"
```
