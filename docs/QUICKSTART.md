# Quickstart

This repository contains the `ai-native-platform` Meshery design, its architecture specification, a
deterministic generator, and reproducible validation reports.

The primary Meshery artifact is:

```text
generated/design.yml
```

See `docs/DESIGN.md`, `docs/ARCHITECTURE.md`, and `docs/VALIDATION.md` for the complete
documentation.

## 1. Regenerate the artifact

```bash
python3 validation/tools/gen.py generated/design.yml
```

The generator is deterministic: the same inputs produce a byte-identical file.

## 2. Validate offline

```bash
python3 validation/tools/verify.py generated/design.yml   # structural checks
python3 validation/tools/gate1.py  generated/design.yml /tmp/gate1   # strict schema
bash tests/run_all.sh                                      # full harness
```

All three must be green.

## 3. Deploy to a live cluster

Prerequisites:

- a Kubernetes cluster reachable through a Meshery context;
- the design's native CRDs installed: `kube-prometheus-stack` (the `monitoring.coreos.com` CRDs)
  and the `meshery-operator` CRDs (`brokers.meshery.io`, `meshsyncs.meshery.io`);
- a local Meshery server (`mesheryctl system start -p docker`, `PROVIDER=Local`).

Then:

```bash
bash deploy.sh
```

`deploy.sh` wires the steps together: it regenerates the artifact, runs the offline gates, finds
the target Meshery context, deploys the design, and asserts that **40 of 40** components apply with
zero failures. On success it prints the applied inventory.

> Each workload uses the real, publicly pullable image for its role (Meshery, the OpenTelemetry
> Collector, Redis, PostgreSQL), so the stack runs, not just applies. Sizing and policy values
> (ports, PVC storage, the Postgres password, alert thresholds) are placeholders to replace for a
> production deploy. See `spec/ARCHITECTURAL_DECISIONS.md` ADR-015.

## 4. Inspect the result

```bash
kubectl get ns | grep ns-ai
kubectl -n ns-ai-control get deploy,svc,ingress
kubectl -n ns-ai-state get sts,pvc,svc
kubectl -n ns-ai-observability get prometheus,alertmanager,servicemonitor
```

The full deploy evidence is recorded in `validation/GATE9-REPORT.md`.
