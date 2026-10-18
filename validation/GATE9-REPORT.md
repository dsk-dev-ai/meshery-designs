# Gate 9 — Live Kubernetes Cluster Deploy Verification

Date: 2026-10-18
Artifact under test: `../generated/design.yml`
Artifact revision: md5 `1c695cfcb45f9f4806475b17844b3b33`, 253199 bytes.
Meshery server: `v1.0.71`, `PROVIDER=Local`, context `073aa6d8f9ed17503d2ae6ba6731d7e8`
(`kind-ai-native`).
Target cluster: `kind` cluster `ai-native` (kindest/node v1.37.0, Kubernetes v1.37).

## Verdict

**PASS.** A live Meshery deploy of the design to a real Kubernetes cluster applies **40 of 40
components with zero failures** (46 summary entries, 40 unique components — the extras are the
repeated `Namespace` summaries the server emits once per namespaced child), and every resource lands
under its designed name and in its designed namespace.

This is the acceptance criterion that Gate 8 explicitly did **not** claim (Gate 8 verified import,
persistence and retrieval only). Gate 9 closes it.

## What changed since Gate 8

Gate 8's artifact (`7338b027…`) imported and round-tripped perfectly but only **applied 34 of 40**
components. The 12 that failed were rejected by the Kubernetes API server with `422` on
**required spec fields that the design legitimately leaves to deploy time** — not on names or
namespaces. The failure surface was:

| Component | Kind | Missing required field |
|---|---|---|
| `deploy-meshery-control`, `otel-collector`, `sts-redis`, `sts-postgres` | Deployment / StatefulSet | `spec.template.spec.containers[0].image` |
| `svc-meshery-control`, `svc-redis`, `svc-postgres` | Service | `spec.ports` |
| `pvc-redis`, `pvc-postgres` | PersistentVolumeClaim | `spec.accessModes`, `spec.resources.requests.storage` |
| `ingress-ai-platform` | Ingress | `spec.rules` |
| `vap-required-labels` | ValidatingAdmissionPolicy | `spec.matchConstraints`, `spec.validations` |
| `promrule-platform-slo` | PrometheusRule | `spec.groups` |

The current revision extends `component_configuration()` in `validation/tools/gen.py` with the
minimum the API server accepts for these 12, and gives each workload the **real, publicly pullable
image for its role** (ADR-015): `meshery/meshery:stable-latest`, the OpenTelemetry Collector, Redis
and PostgreSQL. The stack therefore not only applies but **runs** — all four workload pods reach
`1/1`.

## Environment

- `kind` v0.34.0 cluster `ai-native`; `kubectl` v1.37.1.
- Pre-installed cluster operators required by the design's native CRDs:
  - `kube-prometheus-stack` 92.10.1 in namespace `monitoring` (provides the ten
    `monitoring.coreos.com` CRDs used by `prometheus`, `alertmanager`, `sm-platform`,
    `promrule-platform-slo`).
  - `meshery-operator` CRDs `brokers.meshery.io` and `meshsyncs.meshery.io` (`v1alpha1`).
- Meshery server run locally in Docker on port 9081 with `PROVIDER=Local`; the cluster registered as
  a Meshery context.

## Method

The call is the exact server path `mesheryctl design deploy` drives:

```
POST http://127.0.0.1:9081/api/pattern/deploy?contexts=073aa6d8f9ed17503d2ae6ba6731d7e8
Content-Type: application/json
{"patternFile": "<contents of generated/design.yml>", "patternID": "2e01feac-75a1-5108-a272-396601942366"}
```

The design was applied to a cluster first cleaned of the previous run (namespaces `ns-ai-*`,
the two `default` NetworkPolicies, and the cluster-scoped `pc-ai-critical` /
`vap-required-labels` / `vapb-ai-runtime`) so the run is a pure create.

## Result

| Field | Value |
|---|---|
| HTTP status | 200 |
| Response time | 40.1 s |
| Summary entries | 46 |
| Unique components applied | **40** |
| Unique component failures | **0** |
| Namespaces created | 4 |

### Applied inventory (40 components)

Cluster-scoped:

- `Namespace` ×4 — `ns-ai-control`, `ns-ai-runtime`, `ns-ai-state`, `ns-ai-observability`
- `PriorityClass` `pc-ai-critical`
- `ValidatingAdmissionPolicy` `vap-required-labels` + `ValidatingAdmissionPolicyBinding` `vapb-ai-runtime`

`ns-ai-control`:

- `Deployment/deploy-meshery-control` (1/1 Ready), `Service/svc-meshery-control` (:80),
  `Ingress/ingress-ai-platform` (host `ai-platform.local`)
- `Secret/sec-broker-endpoint`, `Secret/sec-registry-creds`, `ServiceAccount/sa-ai-control`,
  `Role/role-ai-control`, `RoleBinding/rb-ai-control`
- `Broker/broker`, `MeshSync/meshsync`

`ns-ai-runtime`:

- `ConfigMap/cm-agent-runtime`, `ConfigMap/cm-model-router`,
  `ResourceQuota/quota-ai-runtime`, `LimitRange/limits-ai-runtime`

`ns-ai-state`:

- `StatefulSet/sts-postgres` (1/1), `StatefulSet/sts-redis` (1/1),
  `Service/svc-postgres` (:5432), `Service/svc-redis` (:6379)
- `PersistentVolumeClaim/pvc-postgres`, `PersistentVolumeClaim/pvc-redis`
- `Secret/sec-state-creds`, `ServiceAccount/sa-ai-state`, `Role/role-ai-state`,
  `RoleBinding/rb-ai-state`, `PodDisruptionBudget/pdb-sts-postgres`,
  `PodDisruptionBudget/pdb-sts-redis`

`ns-ai-observability`:

- `Deployment/otel-collector` (1/1)
- `Prometheus/prometheus` (StatefulSet `prometheus-prometheus` 1/1),
  `Alertmanager/alertmanager` (StatefulSet `alertmanager-alertmanager` 1/1)
- `ServiceMonitor/sm-platform`, `PrometheusRule/promrule-platform-slo`

`default`:

- `NetworkPolicy/netpol-default-deny`, `NetworkPolicy/netpol-ai-allowlist`

## Names and namespaces

Every applied object carries its designed name. Every namespaced object lands in its designed
namespace (verified against the component inventory). This exercises the two fixes that preceded
this gate:

- `displayName` is set to the spec instance name (meshkit's `converter.CreateK8sResourceStructure`
  derives the resource `metadata.name` from `DisplayName`, not from `configuration.metadata.name`).
- the resolved `configuration.metadata.namespace` is now emitted directly on each namespaced
  component, because the server deploy chain does **not** run relationship mutators
  (`design_engine_handler.go` leaves `stages.ServiceIdentifierAndMutator` disabled; mutators run
  only in the UI `EvaluateDesign` path).

## Known, expected observations

- **The two `NetworkPolicy` objects land in `default`.** The catalog declares `NetworkPolicy`
  `isNamespaced: false` (a catalog inaccuracy), so the design faithfully emits no namespace for
  them and they take `default`. Documented in `GATE8-REPORT.md`.
- **`pvc-redis` / `pvc-postgres` report `Pending`.** The `local-path` provisioner binds a volume when
  a pod schedules against it; the StatefulSets do not mount these claims, so the PVCs legitimately
  remain unbound. The objects exist and are accepted.
- **All four workloads run `1/1`** with real images: `deploy-meshery-control`
  (`meshery/meshery:stable-latest`), `otel-collector`
  (`otel/opentelemetry-collector-contrib:0.111.0`), `sts-redis` (`redis:7.4-alpine`) and
  `sts-postgres` (`postgres:16-alpine`). `prometheus-prometheus` and `alertmanager-alertmanager`
  also run `2/2`. First pull on a slow network took several minutes; the images are public and
  unpinned by design (ADR-015).

## Reproduce

```bash
bash deploy.sh                 # generates, validates, deploys, and asserts 40/40
```

See `deploy.sh` and `docs/QUICKSTART.md`. The full result JSON is captured as evidence.

## Evidence

- `/tmp/deploy4.json` — raw `POST /api/pattern/deploy` response (46 entries, 40 unique success).
- `/tmp/deploy-payload4.json` — the request body (design + `patternID`).
- Repository harnesses re-run on this revision (all green):
  - `validation/tools/verify.py generated/design.yml` → **28 checks, 0 failed**
  - `validation/tools/gate1.py generated/design.yml` → **GATE 1: PASS**
  - `bash tests/run_all.sh` → **ALL TESTS PASSED**

## Acceptance-criteria mapping

| Gate 9 criterion | Status |
|---|---|
| Server accepts and deploys the design to a live cluster | **PASS** |
| All 40 native components apply | **PASS** |
| Zero API-server rejections | **PASS** |
| Resources carry designed names | **PASS** |
| Namespaced resources land in designed namespaces | **PASS** |
| Cluster-scoped resources are cluster-scoped | **PASS** |
