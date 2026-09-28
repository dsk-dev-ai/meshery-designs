# Component Inventory — `ai-native-platform`

66 components: **40 native** (`isAnnotation: false`), **26 annotation** (`isAnnotation: true`). This document is the
authoritative component list; every other spec's totals are derived from it.

Every component below is traceable to a file in the Meshery model catalog. The `Source` column names the exact
catalog path, so each row can be re-verified without re-running discovery.

Model versions used:

| Model | Version | Components used |
|---|---|---|
| `kubernetes` | `v1.37.1` / `v1.0.0` | 18 distinct kinds, 33 instances |
| `meshery-core` | `0.7.2` / `v1.0.0` | 5 distinct kinds, 26 instances |
| `meshery-operator` | `1.0.70` / `v1.0.0` | `MeshSync`, `Broker` |
| `kube-prometheus-stack` | `89.2.2` / `v1.0.0` | `Prometheus`, `ServiceMonitor`, `Alertmanager`, `PrometheusRule` |
| `sumologic` | `4.18.0` / `v1.0.0` | `OpenTelemetryCollector` |

---

## Group 1 — Namespaces and scoping

### `ns-ai-control`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `Namespace` (`v1`)
- **Class:** Native
- **Source:** `models/kubernetes/v1.37.1/v1.0.0/components/Namespace.json`
- **Purpose:** Isolated namespace holding the Meshery control plane, its broker, its GitOps sync, and its ingress.
- **Why it exists:** The control plane is the highest-value compromise target in the platform. Giving it its own
  namespace means an `ai-runtime` breach does not inherit control-plane RBAC, and `netpol-default-deny` can be
  applied there independently.
- **Dependencies:** none (top of the containment hierarchy)
- **Expected relationships:** target of ~9 `hierarchical/parent/inventory` edges from control-plane components

### `ns-ai-runtime`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `Namespace` (`v1`)
- **Class:** Native
- **Purpose:** Holds the runtime configuration contract (`cm-agent-runtime`, `cm-model-router`) and the quota and
  limit objects that govern runtime workloads.
- **Why it exists:** Separates *policy about* runtime workloads from the control plane that applies them. A quota
  change in this namespace can never alter control-plane RBAC.
- **Dependencies:** none
- **Expected relationships:** target of 4 `hierarchical/parent/inventory` edges

### `ns-ai-state`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `Namespace` (`v1`)
- **Class:** Native
- **Purpose:** Holds both stateful stores, their Services, their PersistentVolumeClaims, and their credentials.
- **Why it exists:** Redis and PostgreSQL hold the platform's session and grounding state. They are the crown
  jewels and get the strictest network posture and their own ServiceAccount.
- **Dependencies:** none
- **Expected relationships:** target of ~10 `hierarchical/parent/inventory` edges

### `ns-ai-observability`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `Namespace` (`v1`)
- **Class:** Native
- **Purpose:** Holds the OpenTelemetry Collector and the full Prometheus Operator CRD set.
- **Why it exists:** The telemetry path must be able to *read* every namespace while not being *reachable* from
  them. A dedicated namespace makes that asymmetry expressible in one place.
- **Dependencies:** none
- **Expected relationships:** target of 5 `hierarchical/parent/inventory` edges

### `env-production`
- **Model:** `meshery-core` 0.7.2 · **Kind:** `Environment` (`core.meshery.io/v1alpha1`)
- **Class:** Annotation-grouped (note: `isAnnotation: false` upstream — it is a scoping primitive, not a
  conceptual node)
- **Source:** `models/meshery-core/0.7.2/v1.0.0/components/Environment.json`
- **Purpose:** Declares the target environment for the whole design.
- **Why it exists:** A design that is environment-agnostic cannot be reviewed for promotion. Naming the
  environment in-graph is cheaper than maintaining it in prose.
- **Dependencies:** none
- **Expected relationships:** `hierarchical/parent/alias` containment over the four `Namespace` components
  (`metadata.isAnnotation: true`)

---

## Group 2 — Control plane (layer 6)

### `meshsync`
- **Model:** `meshery-operator` 1.0.70 · **Kind:** `MeshSync` (`meshery.io/v1alpha1`)
- **Class:** Native
- **Source:** `models/meshery-operator/1.0.70/v1.0.0/components/MeshSync.json`
- **Purpose:** GitOps synchronisation resource — reconciles desired design state against the cluster.
- **Why it exists:** The design must have a real reconciliation path, not just a diagram. `MeshSync` is the
  upstream CRD that makes the design authoritative rather than documentary.
- **Dependencies:** `ns-ai-control`, `broker`, `sec-broker-endpoint`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-control`; annotation-level
  `edge/non-binding/reference` → `meshery-control-plane`

### `broker`
- **Model:** `meshery-operator` 1.0.70 · **Kind:** `Broker` (`meshery.io/v1alpha1`)
- **Class:** Native
- **Source:** `models/meshery-operator/1.0.70/v1.0.0/components/Broker.json`
- **Purpose:** Declares the message-broker endpoint the operator components talk to.
- **Why it exists:** `MeshSync` and the control plane need a broker address. Declaring it as a real CRD means the
  broker connection is reviewable configuration rather than an implicit default.
- **Dependencies:** `ns-ai-control`, `sec-broker-endpoint`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-control`; annotation-level
  `edge/non-binding/reference` → `meshery-control-plane`

### `deploy-meshery-control`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `Deployment` (`apps/v1`)
- **Class:** Native
- **Purpose:** The workload slot for the Meshery control-plane server.
- **Why it exists:** `meshery-operator` supplies the CRDs but not the server. A `Deployment` is a confirmed real
  component and a generic workload declaration; it asserts *a workload lives here* without claiming a model
  exists for it. The design deliberately leaves `configuration` minimal — image selection happens at deploy time
  from the component form, matching the upstream convention where namespaced components carry empty
  `configuration`.
- **Dependencies:** `ns-ai-control`, `sa-ai-control`, `cm-agent-runtime`, `cm-model-router`, `sec-broker-endpoint`,
  `sec-registry-creds`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-control`; `edge/non-binding/network` ←
  `svc-meshery-control`; `edge/non-binding/reference` → `cm-agent-runtime`, `cm-model-router`,
  `sec-broker-endpoint`, `sec-registry-creds`

### `svc-meshery-control`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `Service` (`v1`)
- **Class:** Native
- **Purpose:** Cluster-internal endpoint for the control-plane server.
- **Why it exists:** Required for `Ingress` to have a backend and for the control plane to be reachable by
  `MeshSync`. Also a scrape target for `sm-platform`.
- **Dependencies:** `ns-ai-control`, `deploy-meshery-control`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-control`;
  `edge/non-binding/network` → `deploy-meshery-control` (real blueprint
  `edge-non-binding-network-duixv.json`); `edge/non-binding/network` ← `ingress-ai-platform`;
  `edge/non-binding/reference` → `sm-platform`

### `ingress-ai-platform`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `Ingress` (`networking.k8s.io/v1`)
- **Class:** Native
- **Purpose:** North-south entry point terminating external access to the control plane.
- **Why it exists:** The MCP access layer needs a real, enforced ingress point. `Ingress` is the only
  general-purpose ingress in the `kubernetes` model — Gateway API CRDs are absent (see
  `UNSUPPORTED_CONCEPTS.md`).
- **Dependencies:** `ns-ai-control`, `svc-meshery-control`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-control`;
  `edge/non-binding/network` → `svc-meshery-control` (real blueprint `edge-non-binding-network-jccsr.json`)

### `meshery-control-plane`
- **Model:** `meshery-core` 0.7.2 · **Kind:** `GenericNode`
- **Class:** Annotation
- **Source:** `models/meshery-core/0.7.2/v1.0.0/components/GenericNode.json`
- **Purpose:** The architectural node naming the Meshery design-and-control layer as a whole.
- **Why it exists:** The design has real CRDs (`meshsync`, `broker`) but no *model* for the Meshery server
  itself. This annotation names the concept so the layer is legible, and its annotation-level edges to `meshsync`
  and `broker` make the correspondence explicit.
- **Dependencies:** `meshsync`, `broker`, `deploy-meshery-control`
- **Expected relationships:** annotation-level `edge/non-binding/reference` → `meshsync`, `broker`; containment
  under `sec-L6-control-plane`

---

## Group 3 — Configuration and secrets (layers 5, 8)

### `cm-agent-runtime`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `ConfigMap` (`v1`)
- **Class:** Native
- **Purpose:** Non-sensitive configuration contract for the agent runtime: timeouts, concurrency limits,
  grounding requirements.
- **Why it exists:** The agent runtime is an annotation, so its configuration would otherwise be pure prose. A
  real `ConfigMap` makes the agent's configuration a reviewable, diffable artifact. This is the mechanism that
  keeps the conceptual layer from being content-free.
- **Dependencies:** `ns-ai-runtime`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-runtime`; `edge/non-binding/reference` →
  `deploy-meshery-control` (real blueprint `hierarchical-parent-inventory-pfnyn.json`)

### `cm-model-router`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `ConfigMap` (`v1`)
- **Class:** Native
- **Purpose:** Non-sensitive routing policy: tier preference order, fallback triggers, cost and privacy ceilings.
- **Why it exists:** Layer 4 (cloud/local/offline fallback) is a policy, and policy belongs in configuration, not
  in a diagram. This `ConfigMap` is where the fallback ladder becomes real.
- **Dependencies:** `ns-ai-runtime`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-runtime`; `edge/non-binding/reference` →
  `deploy-meshery-control`; annotation-level reference → `model-router`

### `sec-broker-endpoint`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `Secret` (`v1`)
- **Class:** Native
- **Purpose:** Broker connection credentials for `meshsync` and `broker`.
- **Why it exists:** `Broker` needs a URL and credentials. Keeping them in a `Secret` rather than the `Broker`
  spec separates the secret material from the resource declaration.
- **Dependencies:** `ns-ai-control`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-control`; `edge/non-binding/reference` →
  `deploy-meshery-control` (real blueprint `reference-secret-to-deployment.json`)

### `sec-registry-creds`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `Secret` (`v1`)
- **Class:** Native
- **Purpose:** Credentials for the model registry referenced by layer 5 grounding.
- **Why it exists:** Layer 5 binds the model registry to a credential. Making the counterpart a real `Secret`
  means the binding has a concrete, secured target instead of dangling in an annotation.
- **Dependencies:** `ns-ai-control`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-control`; `edge/non-binding/reference` →
  `deploy-meshery-control`; annotation-level reference → `registry-credential`

### `sec-state-creds`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `Secret` (`v1`)
- **Class:** Native
- **Purpose:** PostgreSQL and Redis credentials.
- **Why it exists:** Both stores need credentials; placing them in the state namespace keeps them subject to
  `netpol-default-deny` and the state ServiceAccount's access policy.
- **Dependencies:** `ns-ai-state`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-state`; hand-authored
  `edge/non-binding/reference` → `sts-postgres`, `sts-redis` (no `Secret → StatefulSet` blueprint exists)

### `registry-credential`
- **Model:** `meshery-core` 0.7.2 · **Kind:** `Credential`
- **Class:** Annotation
- **Source:** `models/meshery-core/0.7.2/v1.0.0/components/Credential.json`
- **Purpose:** Names the credential that the model registry requires, from the design's point of view.
- **Why it exists:** `Credential` is a real `meshery-core` component purpose-built for this. It is the correct
  annotation for "this concept needs a secret", and it pairs with the real `sec-registry-creds`.
- **Dependencies:** `sec-registry-creds`
- **Expected relationships:** annotation-level `edge/non-binding/reference` ← `model-registry`; ←
  `sec-registry-creds`

---

## Group 4 — State (layer 9)

### `sts-redis`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `StatefulSet` (`apps/v1`)
- **Class:** Native
- **Purpose:** Session, cache, and agent short-term memory store.
- **Why it exists:** Layer 9 requires a Redis state tier. A `StatefulSet` with a `PersistentVolumeClaim` is the
  smallest real Kubernetes primitive that provides stable identity and durable storage. Using an operator would
  add a control loop the platform does not need. See ADR-004.
- **Dependencies:** `ns-ai-state`, `sa-ai-state`, `pvc-redis`, `sec-state-creds`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-state`; `edge/non-binding/reference` →
  `pvc-redis` (real blueprint `edge-non-binding-reference-rcycs.json`); ← `svc-redis`; ← `pdb-sts-redis`;
  ← `pc-ai-critical`; → `sec-state-creds`

### `svc-redis`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `Service` (`v1`)
- **Class:** Native
- **Purpose:** Cluster-internal endpoint for the Redis store.
- **Why it exists:** Consumers need a stable address; `StatefulSet` pod DNS is not a stable contract. Also a
  scrape target.
- **Dependencies:** `ns-ai-state`, `sts-redis`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-state`; hand-authored
  `edge/non-binding/network` → `sts-redis`; `edge/non-binding/reference` → `sm-platform`

### `pvc-redis`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `PersistentVolumeClaim` (`v1`)
- **Class:** Native
- **Purpose:** Durable volume claim for the Redis store.
- **Why it exists:** Redis holds session state that must survive pod replacement. Without a claim, graceful
  degradation is not graceful — state is lost on every rollout.
- **Dependencies:** `ns-ai-state`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-state`;
  `edge/non-binding/reference` → `sts-redis`

### `sts-postgres`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `StatefulSet` (`apps/v1`)
- **Class:** Native
- **Purpose:** Durable store for grounding artefacts: model registry entries, context records, policy versions.
- **Why it exists:** Layer 5 grounding must be durable and queryable — grounding that is only in memory is not
  auditable. Same operator-avoidance rationale as `sts-redis`.
- **Dependencies:** `ns-ai-state`, `sa-ai-state`, `pvc-postgres`, `sec-state-creds`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-state`; `edge/non-binding/reference` →
  `pvc-postgres`; ← `svc-postgres`; ← `pdb-sts-postgres`; ← `pc-ai-critical`; → `sec-state-creds`

### `svc-postgres`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `Service` (`v1`)
- **Class:** Native
- **Purpose:** Cluster-internal endpoint for the PostgreSQL store.
- **Why it exists:** Same contract as `svc-redis`.
- **Dependencies:** `ns-ai-state`, `sts-postgres`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-state`; hand-authored
  `edge/non-binding/network` → `sts-postgres`; `edge/non-binding/reference` → `sm-platform`

### `pvc-postgres`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `PersistentVolumeClaim` (`v1`)
- **Class:** Native
- **Purpose:** Durable volume claim for the PostgreSQL store.
- **Why it exists:** Grounding records must outlive pod replacement.
- **Dependencies:** `ns-ai-state`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-state`;
  `edge/non-binding/reference` → `sts-postgres`

---

## Group 5 — Observability (layer 10)

### `otel-collector`
- **Model:** `sumologic` 4.18.0 · **Kind:** `OpenTelemetryCollector` (`opentelemetry.io/v1alpha1`)
- **Class:** Native
- **Source:** `models/sumologic/4.18.0/v1.0.0/components/OpenTelemetryCollector.json` (`isNamespaced: true`,
  `status: enabled`)
- **Purpose:** Receives, processes, and exports traces and metrics from every namespace.
- **Why it exists:** Layer 10 requires OpenTelemetry. `sumologic` 4.18.0 is the **only** model in the 477-model
  catalog that provides a real `OpenTelemetryCollector` component. Using it is honest; it is a genuine upstream
  CRD, and the `sumologic` provenance is disclosed rather than hidden.
- **Dependencies:** `ns-ai-observability`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-observability`; hand-authored annotation-level
  `edge/non-binding/reference` → `prometheus` (`sumologic` ships no relationship blueprints)

### `prometheus`
- **Model:** `kube-prometheus-stack` 89.2.2 · **Kind:** `Prometheus` (`monitoring.coreos.com/v1`)
- **Class:** Native
- **Purpose:** Metrics store and evaluation engine for the platform.
- **Why it exists:** Layer 10 requires Prometheus. The Prometheus Operator CRDs are not in the `kubernetes`
  model — they live in `kube-prometheus-stack`. Selecting the right model is mandatory for a valid design.
- **Dependencies:** `ns-ai-observability`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-observability`;
  `edge/non-binding/reference` → `sm-platform`, `promrule-platform-slo`; `edge/binding/permission` →
  `sa-ai-control`

### `sm-platform`
- **Model:** `kube-prometheus-stack` 89.2.2 · **Kind:** `ServiceMonitor` (`monitoring.coreos.com/v1`)
- **Class:** Native
- **Purpose:** Declares the scrape targets for the control plane and both state stores.
- **Why it exists:** Without a `ServiceMonitor`, `Prometheus` has nothing to scrape. One monitor selecting all
  three services keeps the scrape surface explicit and minimal.
- **Dependencies:** `ns-ai-observability`, `prometheus`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-observability`; ← `prometheus`;
  `edge/non-binding/reference` → `svc-meshery-control`, `svc-redis`, `svc-postgres`

### `alertmanager`
- **Model:** `kube-prometheus-stack` 89.2.2 · **Kind:** `Alertmanager` (`monitoring.coreos.com/v1`)
- **Class:** Native
- **Purpose:** Routes alerts raised by `promrule-platform-slo`.
- **Why it exists:** Layer 12 degradation must be *observable*; degradation that fails silently is worse than no
  degradation. Alert routing is what turns the tier ladder into an operable system.
- **Dependencies:** `ns-ai-observability`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-observability`;
  `edge/non-binding/reference` → `promrule-platform-slo`; ← `prometheus`

### `promrule-platform-slo`
- **Model:** `kube-prometheus-stack` 89.2.2 · **Kind:** `PrometheusRule` (`monitoring.coreos.com/v1`)
- **Class:** Native
- **Purpose:** Alerting rules covering fallback-tier exhaustion, store unavailability, and control-plane health.
- **Why it exists:** Gives layer 12 a concrete definition — the SLOs are the criteria by which a tier is
  considered degraded. It also supplies the semantic content for the `edge` to `Alertmanager`; without it,
  `Alertmanager` has no source.
- **Dependencies:** `ns-ai-observability`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-observability`; → `prometheus`;
  → `alertmanager`

---

## Group 6 — Security (layer 11)

### `sa-ai-control`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `ServiceAccount` (`v1`)
- **Class:** Native
- **Purpose:** Workload identity for the control-plane server.
- **Why it exists:** Running without a dedicated ServiceAccount means the pod uses `default`, which is
  namespace-wide and defeats namespace isolation. This is a prerequisite, not an optimisation.
- **Dependencies:** `ns-ai-control`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-control`;
  `edge/binding/permission` → `role-ai-control` (real blueprint `edge-binding-permission-homji.json`)

### `role-ai-control`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `Role` (`rbac.authorization.k8s.io/v1`)
- **Class:** Native
- **Purpose:** Least-privilege permissions for the control-plane identity — read designs, read broker config.
- **Why it exists:** Layer 11 requires scoped identity. A `ClusterRole` would over-grant; a namespaced `Role` is
  the correct scope for a namespaced control plane.
- **Dependencies:** `sa-ai-control`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-control`;
  `edge/binding/permission` → `sa-ai-control`; ← `rb-ai-control` (real blueprint
  `edge-non-binding-reference-keceb.json`, `RoleBinding → Role`)

### `rb-ai-control`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `RoleBinding` (`rbac.authorization.k8s.io/v1`)
- **Class:** Native
- **Purpose:** Binds `role-ai-control` to `sa-ai-control`.
- **Why it exists:** Required for the permission edge to take effect.
- **Dependencies:** `role-ai-control`, `sa-ai-control`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-control`;
  `edge/non-binding/reference` → `role-ai-control`

### `sa-ai-state`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `ServiceAccount` (`v1`)
- **Class:** Native
- **Purpose:** Workload identity for both stateful stores.
- **Why it exists:** Stores are the most privileged data holders in the platform; they must not run as `default`.
- **Dependencies:** `ns-ai-state`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-state`;
  `edge/binding/permission` → `role-ai-state`

### `role-ai-state`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `Role` (`rbac.authorization.k8s.io/v1`)
- **Class:** Native
- **Purpose:** Least-privilege permissions for the state identity — read only its own Secrets and PVCs.
- **Why it exists:** Constrains blast radius if a store pod is compromised.
- **Dependencies:** `sa-ai-state`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-state`;
  `edge/binding/permission` → `sa-ai-state`; ← `rb-ai-state`

### `rb-ai-state`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `RoleBinding` (`rbac.authorization.k8s.io/v1`)
- **Class:** Native
- **Purpose:** Binds `role-ai-state` to `sa-ai-state`.
- **Why it exists:** Required for the permission edge to take effect.
- **Dependencies:** `role-ai-state`, `sa-ai-state`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-state`;
  `edge/non-binding/reference` → `role-ai-state`

### `netpol-default-deny`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `NetworkPolicy` (`networking.k8s.io/v1`)
- **Class:** Native
- **Purpose:** Deny-all ingress/egress baseline for the state and control namespaces.
- **Why it exists:** Layer 11 requires a security boundary. A default-deny baseline is the only posture from which
  allow-rules mean anything. Native `NetworkPolicy` achieves this with no CNI operator.
- **Dependencies:** `ns-ai-state`, `ns-ai-control`
- **Expected relationships:** containment under `sec-L11-security`; the two available blueprints
  (`edge/binding/firewall-dynit.json`, `edge/binding/firewall-kllzw.json`) both target `Pod`, and this design
  declares no `Pod` components, so **no `edge` is authored** — see `RELATIONSHIP_MATRIX.md` §6.1

### `netpol-ai-allowlist`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `NetworkPolicy` (`networking.k8s.io/v1`)
- **Class:** Native
- **Purpose:** Explicit east-west permissions: control plane → stores, collector → workloads, Prometheus →
  scrape targets.
- **Why it exists:** Default-deny without allow-rules makes the platform uncommunicable. This is the other half
  of a complete network posture.
- **Dependencies:** `ns-ai-state`, `ns-ai-observability`
- **Expected relationships:** containment under `sec-L11-security`; no `edge` — see above

### `trust-boundary`
- **Model:** `meshery-core` 0.7.2 · **Kind:** `GenericNode`
- **Class:** Annotation
- **Purpose:** Names the boundary between the untrusted MCP ingress zone and the trusted platform zone.
- **Why it exists:** A `NetworkPolicy` expresses which flows are permitted but not *why* a particular line is
  drawn. This annotation carries that intent so the security review does not have to infer it.
- **Dependencies:** `mcp-access-gateway`, `ingress-ai-platform`
- **Expected relationships:** annotation-level `edge/non-binding/reference` → `mcp-access-gateway`;
  → `ingress-ai-platform`; containment under `sec-L11-security`

---

## Group 7 — Policy (layer 7)

### `vap-required-labels`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `ValidatingAdmissionPolicy` (`admissionregistration.k8s.io/v1`
  — verified directly in `models/kubernetes/v1.37.1/v1.0.0/components/ValidatingAdmissionPolicy.json`;
  `status: enabled`, `isAnnotation: false`)
- **Class:** Native
- **Purpose:** Admission policy requiring platform labels on workload resources.
- **Why it exists:** Layer 7 requires a real enforcement point, and this is the cheapest one that exists:
  `ValidatingAdmissionPolicy` is a built-in Kubernetes API evaluated in-process by the API server. No webhook,
  no operator, no external dependency. See ADR-006.
- **Dependencies:** none (cluster-scoped)
- **Expected relationships:** `edge/non-binding/reference` → `vapb-ai-runtime` (real blueprint
  `edge-binding-reference-ecilr.json`)

### `vapb-ai-runtime`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `ValidatingAdmissionPolicyBinding` (same API group)
- **Class:** Native
- **Purpose:** Binds `vap-required-labels` to the runtime and state namespaces.
- **Why it exists:** A policy without a binding is inert. This is the component that makes the policy real, and
  scoping it by namespace means the control plane is not subject to runtime labelling rules.
- **Dependencies:** `vap-required-labels`, `ns-ai-runtime`, `ns-ai-state`
- **Expected relationships:** `edge/non-binding/reference` → `vap-required-labels` (real blueprint
  `edge-binding-reference-kwjtj.json`)

### `quota-ai-runtime`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `ResourceQuota` (`v1`)
- **Class:** Native
- **Purpose:** Caps total CPU, memory, and pod count in the runtime namespace.
- **Why it exists:** A runaway agent loop must not be able to exhaust the cluster. Quota is the hard stop; layer
  12's graceful degradation is the soft stop.
- **Dependencies:** `ns-ai-runtime`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-runtime`; containment under
  `sec-L7-policy-boundary`

### `limits-ai-runtime`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `LimitRange` (`v1`)
- **Class:** Native
- **Purpose:** Supplies default CPU/memory requests and limits for containers lacking them.
- **Why it exists:** Paired with `quota-ai-runtime`. Quota rejects pods that exceed the total; `LimitRange`
  ensures pods are shaped before they are judged. Without it, a pod with no limits causes quota rejection with
  an unhelpful error instead of being sensibly bounded.
- **Dependencies:** `ns-ai-runtime`
- **Expected relationships:** `hierarchical/parent/inventory` → `ns-ai-runtime`; containment under
  `sec-L7-policy-boundary`

### `policy-boundary`
- **Model:** `meshery-core` 0.7.2 · **Kind:** `GenericNode`
- **Class:** Annotation
- **Purpose:** The architectural choke point where a request is checked before any model tier is contacted.
- **Why it exists:** `vap-required-labels` enforces *labelling*, not *request policy*. Request-time policy has
  no native component. This annotation names the boundary; `grounding-validator` fills it.
- **Dependencies:** `grounding-validator`, `vap-required-labels`
- **Expected relationships:** annotation-level `edge/non-binding/reference` → `grounding-validator`;
  → `vap-required-labels`; containment under `sec-L7-policy-boundary`

### `grounding-validator`
- **Model:** `meshery-core` 0.7.2 · **Kind:** `GenericNode`
- **Class:** Annotation
- **Purpose:** Checks that a request is answerable from registered, permitted context before it reaches a tier.
- **Why it exists:** Layer 5 grounding and layer 4 fallback interact: an ungrounded request must not silently
  fall through to a cheaper tier. Making that check a named node prevents the fallback ladder from becoming an
  accidental bypass.
- **Dependencies:** `context-store`, `model-registry`, `policy-boundary`
- **Expected relationships:** annotation-level `edge/non-binding/reference` → `context-store`, `model-registry`;
  → `policy-boundary`; ← `model-router`; containment under `sec-L7-policy-boundary`

---

## Group 8 — Resilience (layer 12)

### `pdb-sts-redis`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `PodDisruptionBudget` (`policy/v1`)
- **Class:** Native
- **Purpose:** Prevents voluntary eviction of Redis below its quorum during node drains and upgrades.
- **Why it exists:** Layer 12 requires the state tier to survive maintenance. Without a PDB, a cluster drain
  takes the store down and graceful degradation never engages — it is bypassed.
- **Dependencies:** `sts-redis`
- **Expected relationships:** `edge/non-binding/reference` → `sts-redis` (real blueprint
  `edge-non-binding-reference-xtrmo.json`)

### `pdb-sts-postgres`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `PodDisruptionBudget` (`policy/v1`)
- **Class:** Native
- **Purpose:** Prevents voluntary eviction of PostgreSQL below its quorum.
- **Why it exists:** Same as `pdb-sts-redis`; grounding records must survive maintenance.
- **Dependencies:** `sts-postgres`
- **Expected relationships:** `edge/non-binding/reference` → `sts-postgres`

### `pc-ai-critical`
- **Model:** `kubernetes` v1.37.1 · **Kind:** `PriorityClass` (`scheduling.k8s.io/v1`)
- **Class:** Native
- **Purpose:** Marks control-plane and state workloads as high-priority during contention.
- **Why it exists:** Layer 12 graceful degradation is only meaningful if the surviving tiers win scheduling
  contention. A `PriorityClass` is the one component that expresses "these survive, the rest yield".
- **Dependencies:** none (cluster-scoped)
- **Expected relationships:** `edge/non-binding/reference` → `sts-redis`, `sts-postgres` (real blueprint
  `edge-non-binding-reference-statefulset.json`)

### `degradation-controller`
- **Model:** `meshery-core` 0.7.2 · **Kind:** `GenericNode`
- **Class:** Annotation
- **Purpose:** Defines the behaviour of the platform when tiers 1 and 2 are unavailable.
- **Why it exists:** Layer 12 is a policy about behaviour under failure. Kubernetes can keep the processes
  alive but cannot decide that a request should be answered from a cached response. That is a design intent and
  is recorded as such, with `promrule-platform-slo` supplying the measurable criteria.
- **Dependencies:** `model-router`, `promrule-platform-slo`
- **Expected relationships:** annotation-level `edge/non-binding/reference` → `model-router`;
  → `promrule-platform-slo`; containment under `sec-L12-degradation`

---

## Group 9 — Workload substrate (layer 8)

The layer-8 components are the four `Namespace` entries in Group 1, `deploy-meshery-control` and
`svc-meshery-control` in Group 2, the two `ConfigMap`s and three `Secret`s in Group 3, and the two `StatefulSet`s
in Group 4. There is no additional layer-8 component: no `Pod`, no `ReplicaSet`, no `StorageClass`.

`StorageClass` is deliberately omitted. Dynamic provisioning is a cluster-level facility, not a property of this
platform, and the two PVCs will bind to whatever default class the cluster provides. Adding a `StorageClass`
would assert a storage backend the design has no basis to choose.

`Pod` is omitted because the design declares workloads at the `Deployment`/`StatefulSet` level. This has one
concrete consequence, recorded in `RELATIONSHIP_MATRIX.md` §6.1: the two `NetworkPolicy` blueprints
(`edge-binding-firewall-dynit.json`, `edge-binding-firewall-kllzw.json`) both target `Pod`, so no firewall edge can
be authored.

---

## Group 10 — AI-native core (layers 1–5)

All annotation. All `meshery-core` 0.7.2 `GenericNode` unless stated.

### `mcp-access-gateway` (layer 1)
- **Purpose:** The single entry point through which Model Context Protocol clients reach platform capabilities.
- **Why it exists:** `meshery-mcp-server` contains zero Go, TypeScript, and JavaScript files, no `go.mod`, no
  `package.json`, no manifests, and no image. There is no MCP model and no deployable artifact. A `GenericNode`
  is the only honest representation: it records that the layer is required and what it must do, without claiming
  something exists. Promotion path in `UNSUPPORTED_CONCEPTS.md` §1.
- **Dependencies:** `ingress-ai-platform`, `agent-runtime`
- **Expected relationships:** annotation-level `edge/non-binding/reference` → `agent-runtime`;
  ← `trust-boundary`; containment under `sec-L1-mcp-access`

### `agent-runtime` (layer 2)
- **Purpose:** Executes agent loops — plan, retrieve context, call tools, assemble responses.
- **Why it exists:** No model describes an agent runtime. Its configuration contract is real
  (`cm-agent-runtime`), which is what keeps this node from being content-free.
- **Dependencies:** `cm-agent-runtime`, `context-store`, `model-router`
- **Expected relationships:** annotation-level `edge/non-binding/reference` → `model-router`, `agent-tool-bridge`,
  `context-store`; ← `mcp-access-gateway`; containment under `sec-L2-agent-runtime`

### `agent-tool-bridge` (layer 2)
- **Purpose:** The agent's egress path to external tools and data sources.
- **Why it exists:** Separating tool access from agent logic is what allows `netpol-ai-allowlist` to restrict tool
  egress independently of agent compute, and it is where an MCP client would eventually live.
- **Dependencies:** `mcp-access-gateway`, `context-store`
- **Expected relationships:** annotation-level `edge/non-binding/reference` → `context-store`; ← `agent-runtime`;
  containment under `sec-L2-agent-runtime`

### `model-router` (layer 3)
- **Purpose:** Selects which model tier serves a given request, based on policy, cost, privacy, and capacity.
- **Why it exists:** Layer 3 is the hinge between the AI-native core and the fallback ladder. Naming it as one
  node makes the fallback policy auditable in a single place. Its policy is real (`cm-model-router`).
- **Dependencies:** `cm-model-router`, `tier-cloud-managed`, `tier-local-hosted`, `tier-offline-cached`,
  `grounding-validator`
- **Expected relationships:** annotation-level `edge/non-binding/reference` → the three tier nodes,
  `grounding-validator`, `model-registry`; ← `agent-runtime`; ← `degradation-controller`; containment under
  `sec-L34-routing-fallback`

### `tier-cloud-managed` (layer 4, tier 1)
- **Purpose:** Requests served by externally hosted, managed model endpoints.
- **Why it exists:** Highest capability, but network-dependent, cost-bearing, and a data-egress risk. Its
  existence in the design is what makes the privacy trade-off in `cm-model-router` meaningful.
- **Dependencies:** `registry-credential`
- **Expected relationships:** annotation-level `edge/non-binding/reference` ← `model-router`; containment under
  `sec-L34-routing-fallback`

### `tier-local-hosted` (layer 4, tier 2)
- **Purpose:** Requests served by model endpoints hosted inside the platform trust boundary.
- **Why it exists:** The privacy-preserving tier. Its existence is what allows the design to claim data can be
  kept inside the boundary under some conditions.
- **Dependencies:** `netpol-ai-allowlist`
- **Expected relationships:** annotation-level `edge/non-binding/reference` ← `model-router`; containment under
  `sec-L34-routing-fallback`

### `tier-offline-cached` (layer 4, tier 3)
- **Purpose:** Requests answered from locally cached artefacts with no external call.
- **Why it exists:** The floor of the ladder. This is the tier that keeps the platform answering when the network
  is gone, which is the entire point of layer 12. `ollama` and other local-serving runtimes are **not** used —
  no model exists (see `UNSUPPORTED_CONCEPTS.md` §2) — so the tier is expressed abstractly.
- **Dependencies:** `context-store`
- **Expected relationships:** annotation-level `edge/non-binding/reference` → `context-store`; ← `model-router`;
  containment under `sec-L34-routing-fallback`

### `context-store` (layer 5)
- **Purpose:** Holds assembled, retrievable context for agent grounding.
- **Why it exists:** Grounding needs a substrate. The durable half of that substrate is real
  (`sts-postgres`); this node names the logical concept and its read/write contract.
- **Dependencies:** `sts-postgres`
- **Expected relationships:** annotation-level `edge/non-binding/reference` → `sts-postgres`; → `grounding-validator`;
  ← `agent-runtime`, `agent-tool-bridge`, `tier-offline-cached`; containment under `sec-L5-grounding`

### `model-registry` (layer 5)
- **Purpose:** The authoritative list of model identities the platform may use, with their grounding metadata.
- **Why it exists:** Prevents the router from selecting an unregistered model. It is the registry half of layer 5
  and the reason `registry-credential` and `sec-registry-creds` exist.
- **Dependencies:** `registry-credential`, `sec-registry-creds`
- **Expected relationships:** annotation-level `edge/non-binding/reference` → `registry-credential`,
  `sec-registry-creds`; ← `model-router`, `grounding-validator`; containment under `sec-L5-grounding`

---

## Group 11 — Layer bands and commentary

Eight `Section` components, each a `meshery-core` 0.7.2 `Section` (`isAnnotation: true`, `genealogy: parent`).
Each carries the architectural band it names.

| Name | Band | Contents |
|---|---|---|
| `sec-L1-mcp-access` | Layer 1 — MCP access | `mcp-access-gateway` |
| `sec-L2-agent-runtime` | Layer 2 — Agent runtime | `agent-runtime`, `agent-tool-bridge` |
| `sec-L34-routing-fallback` | Layers 3–4 — Routing and fallback | `model-router`, `tier-cloud-managed`, `tier-local-hosted`, `tier-offline-cached` |
| `sec-L5-grounding` | Layer 5 — Context and registry grounding | `context-store`, `model-registry`, `registry-credential` |
| `sec-L6-control-plane` | Layer 6 — Meshery design and control | `meshery-control-plane`, `meshsync`, `broker` |
| `sec-L7-policy-boundary` | Layer 7 — Validation and policy | `policy-boundary`, `grounding-validator`, `quota-ai-runtime`, `limits-ai-runtime` |
| `sec-L11-security` | Layer 11 — Security boundaries | `trust-boundary`, `netpol-default-deny`, `netpol-ai-allowlist` |
| `sec-L12-degradation` | Layer 12 — Resilience and degradation | `degradation-controller`, `pdb-sts-redis`, `pdb-sts-postgres` |

**Why `Section` and not `Container`.** `Container` has a real upstream blueprint pairing it with `Deployment`
(`hierarchical-parent-alias-iicqa.json`) and with `Pod`. The design has one `Deployment` and no `Pods`, so
`Container` would permit exactly one real grouping edge. `Section` is a rectangle with `genealogy: parent`,
which is a better fit for wide layer bands containing both annotations and native components, and it avoids
implying a workload-containment relationship that does not exist. See ADR-009.

Two `Comment` components carry design rationale in-graph:

| Name | Content |
|---|---|
| `note-annotation-vs-infrastructure` | States that annotation components describe intent and are not deployable; only `isAnnotation: false` components produce cluster resources. |
| `note-deferred-ai-workloads` | Records that layers 1–5 have no native components and must not be given fabricated `Deployment`s until an implementation exists. |

**Why commentary exists at all.** Upstream designs carry `configuration.userMessages` on annotation components
(this was observed in the `3c3439a0-…` reference). Recording the two rules that a reviewer is most likely to
break — "annotations are not infrastructure" and "do not fabricate AI workloads" — inside the design itself
means they travel with the artifact.

---

## Component totals by model

Every component in this document appears in exactly one of these rows, and the row totals sum to 66.

| Model | Native | Annotation | Total |
|---|---|---|---|
| `kubernetes` v1.37.1 | 33 | 0 | 33 |
| `meshery-core` 0.7.2 | 0 | 26 | 26 |
| `meshery-operator` 1.0.70 | 2 | 0 | 2 |
| `kube-prometheus-stack` 89.2.2 | 4 | 0 | 4 |
| `sumologic` 4.18.0 | 1 | 0 | 1 |
| **Total** | **40** | **26** | **66** |

`meshery-core` 26 breaks down as: 1 `Environment`, 14 `GenericNode`, 8 `Section`, 2 `Comment`, 1 `Credential`.

`kubernetes` 33 breaks down as: `Namespace`×4, `ServiceAccount`×2, `Role`×2, `RoleBinding`×2, `Deployment`,
`Service`×3, `Ingress`, `ConfigMap`×2, `Secret`×3, `StatefulSet`×2, `PersistentVolumeClaim`×2,
`NetworkPolicy`×2, `ResourceQuota`, `LimitRange`, `ValidatingAdmissionPolicy`,
`ValidatingAdmissionPolicyBinding`, `PriorityClass`, `PodDisruptionBudget`×2.

### The one deliberate override of an upstream value

`Environment` is defined in `meshery-core` 0.7.2 with `metadata.isAnnotation: false`. This design sets it to
`true`, and it is the only component whose `isAnnotation` differs from its catalog default.

The reason: `Environment` is not a deployable Kubernetes resource — it is a Meshery-level statement about which
environment the design targets. Setting `isAnnotation: true` is what prevents it from being rendered as a
manifest. Every other component takes its catalog value unchanged. The upstream default is recorded here rather
than silently overridden.
