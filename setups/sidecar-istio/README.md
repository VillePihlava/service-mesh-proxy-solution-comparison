# Setup instructions

## baseline (no sidecar injection)

1. `kubeadm init --config cluster-configuration.yaml`
2. Install Calico with:
 * `curl https://raw.githubusercontent.com/projectcalico/calico/v3.24.5/manifests/calico.yaml -LO`
 * `kubectl apply -f calico.yaml`
3. Use `deploy.sh` to deploy the test setup (set $REGISTRY).

4. Run test script `runner/runner.py` to run test, for example:
```console
python3 runner.py --qps 100 --duration 300 --conn 10 --perf_targets "http-server_http-server,demo-service_demo-service" --extra_labels "baseline-1" --results_dir "../data/baseline/flame" --url http://istio-ingressgateway.istio-system/
```

5. Run script `runner/fortio.py` to generate csv , for example:
```console
python3 fortio.py --csv_output "../data/baseline/baseline-summary.csv" --json_output_dir "../data/baseline/json" --resource_usage_targets="baseline" --prometheus="http://127.0.0.1:32418"
```

## sidecar-istio

1. `kubeadm init --config cluster-configuration.yaml`
2. Install Calico with:
 * `curl https://raw.githubusercontent.com/projectcalico/calico/v3.24.5/manifests/calico.yaml -LO`
 * `kubectl apply -f calico.yaml`
3. Enable Istio injection (this is required even for the proxyless setup): `kubectl label namespace default istio-injection=enabled`
4. Use `deploy.sh` to deploy the test setup (set $REGISTRY).

5. Apply strict mTLS. Istio should automatically use mTLS, but this forces its use.
 * `kubectl apply -f strict-mtls.yaml`

6. Run test script `runner/runner.py` to run test, for example:
```console
python3 runner.py --qps 100 --duration 300 --conn 10 --perf_targets "http-server_http-server,http-server_envoy,demo-service_envoy,demo-service_demo-service" --extra_labels "sidecar-istio-1" --results_dir "../data/sidecar-istio/flame" --url http://istio-ingressgateway.istio-system/
```

7. Run script `runner/fortio.py` to generate csv , for example:
```console
python3 fortio.py --csv_output "../data/sidecar-istio/sidecar-istio-summary.csv" --json_output_dir "../data/sidecar-istio/json" --resource_usage_targets="sidecar-istio" --prometheus="http://127.0.0.1:32418"
```
