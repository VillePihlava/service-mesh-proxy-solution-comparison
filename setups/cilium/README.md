# Setup instructions

1. Create a cluster with: `kubeadm init --config cluster-configuration.yaml`
2. Install Cilium with Helm (replace address): `helm install cilium cilium/cilium --version 1.12.2 -f cilium-chart-values.yaml --set k8sServiceHost=<address> --namespace kube-system`
3. Edit Cilium daemonset to achieve Guaranteed QoS Class (for CPU pinning) with: `kubectl edit daemonsets.apps -n kube-system cilium`. Specifically change initcontainer resources to the following:
```console
resources:
  limits:
    cpu: "1"
    memory: 1000Mi
  requests:
    cpu: "1"
    memory: 1000Mi
```

4. Use `deploy.sh` to deploy the test setup (set $REGISTRY).

5. Run test script `runner/runner.py` to run test, for example:
```console
python3 runner.py --qps 100 --duration 300 --conn 10 --perf_targets "http-server_http-server,demo-service_demo-service" --extra_labels "cilium-1" --results_dir "../data/cilium/flame" --url http://cilium-ingress-app-ingress.default/
```

6. Run script `runner/fortio.py` to generate csv , for example:
```console
python3 fortio.py --csv_output "../data/cilium/cilium-summary.csv" --json_output_dir "../data/cilium/json" --resource_usage_targets="cilium" --prometheus="http://127.0.0.1:30930"
```
