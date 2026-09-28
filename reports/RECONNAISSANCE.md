# Meshery Design — Reconnaissance Report

**Scope:** reconnaissance only. No final Design (YAML/JSON) was produced.
**Date of investigation:** 2026-09-28
**Method:** read-only inspection of upstream sources + one throwaway Go probe in `/tmp/opencode/dsgnprobe` (no repo mutation).

---

## A. Upstream sources and pinned revisions

| Repo | Remote | HEAD | State |
|---|---|---|---|
| Meshery | `https://github.com/meshery/meshery.git` | `90bac8dc4c9ea5d6d915c41fec0bb013adc1b6fe` (`master`) | clean, `0 0` vs `origin/master` |
| Meshery MCP Server | `https://github.com/meshery/meshery-mcp-server.git` | `fe0bfc5413ce6aafc648b50489c945689543b7a6` (`master`) | matches `origin/master` |
| Meshery Schemas (module) | `github.com/meshery/schemas` | `v1.3.37` | read from Go module cache |
| Meshkit (module) | `github.com/meshery/meshkit` | `v1.0.22` | read from Go module cache |

`~/opensource_new_programs/meshery-designs` is **not** a Git repository. Its `spec/*.md` and `docs/README.md` are all **0 bytes** — there is no pre-existing written architecture to reconcile against. Classification below is therefore derived from the stated goal (an AI-native, cloud-native platform) plus upstream evidence.

Note on environment: system `go` is 1.22.2; the Meshery module requires `go 1.26.4`, available as a cached toolchain at
`/home/dsk/go/pkg/mod/golang.org/toolchain@v0.0.1-go1.26.4.linux-amd64/bin/go` (used with `GOTOOLCHAIN=local`).

---

## B. The Design / Pattern document model

Meshery's public "Design" is internally the **`Pattern`** resource, parsed into `design.PatternFile` from
`github.com/meshery/schemas/models/v1beta3/design`.

### B.1 Authoritative JSON Schema

`schemas/constructs/v1beta3/design/design.yaml` (Draft-07), served over `api.yml`:

```yaml
$schema: http://json-schema.org/draft-07/schema#
title: Design Schema
additionalProperties: false          # <-- top-level is CLOSED
required: [id, name, schemaVersion, version, components, relationships]
```

Top-level properties, in `x-order`:

| Key | x-order | Type / $ref | Notes |
|---|---|---|---|
| `id` | 1 | `Uuid` (v1beta2 core) | |
| `name` | 2 | `string`, `minLength: 1`, `maxLength: 255` | |
| `schemaVersion` | 3 | `VersionString` | must be `designs.meshery.io/v1beta3` |
| `version` | 4 | `SemverString`, default `v0.0.1`, `maxLength: 50` | |
| `metadata` | 5 | `object`, `additionalProperties: true` | optional; carries `resolvedAliases` map |
| `components` | 6 | `[]*component.ComponentDefinition` (**v1beta2**) | `minItems: 0`; optional to omit but listed in `required` |
| `preferences` | 7 | `DesignPreferences` (local `api.yml`) | |
| `relationships` | 8 | `[]*relationship.RelationshipDefinition` (**v1beta2**) | |

Key consequence: **`metadata` is open, everything else at top level is closed.** Any scaffold key such as
`layers`, `services`, `type`, or `workspace` is **schema-invalid** at the top level, even though the Go struct
may ignore it during a plain unmarshal.

### B.2 Version constants actually in use

| Object | Canonical | Seen in 361 real catalog designs |
|---|---|---|
| Design | `designs.meshery.io/v1beta3` | `v1beta3`: **1**; `v1beta1`: 180 |
| Component | `components.meshery.io/v1beta2` | `v1beta1`: 1809; blank: 6 |
| Relationship | `relationships.meshery.io/v1beta2` | `v1alpha3`: 6026; blank: 93 |

The single `v1beta3` design in the catalog
(`docs/data/catalog/66ca6523-f21c-4fc1-a247-fa32f0ad753b/0.0.1/design.yml`, `0.0.2`) is **empty** — 0
components, 0 relationships, no `name`. **There is no non-empty v1beta3 reference design upstream.** The
canonical *non-empty* references are all v1beta1.

### B.3 Component definition (model-catalog form)

`models/kubernetes/v1.37.1/v1.0.0/components/Deployment.json` top-level keys:

```
capabilities, component, configuration, createdAt, deletedAt, description,
displayName, format, id, metadata, model, modelReference, schemaVersion,
status, styles, updatedAt, version
```

- `component`: `{ kind, version, schema }` — e.g. `kind: Deployment`, `version: apps/v1`, `schema` = embedded JSON
  string of the upstream OpenAPI/CRD fragment that drives form rendering.
- `model`: `{ id, name, displayName, version, model: {version}, registrant: {...} }` — the model reference. In the
  registry the `id`/`registrant.id` are the zero UUID; in a saved design they carry the resolved model/registrant.
- `metadata`: `{ genealogy, instanceDetails, isAnnotation, isNamespaced, published, source_uri, styles,
  configurationUISchema }`.
- `id` in the catalog is the zero UUID; **in a design instance, `id` is a fresh per-component UUID.**

### B.4 Component instance shape (as used in real designs)

Verified by direct parse of `3c3439a0-…/0.0.1/design.yml` into the v1beta3 Go struct:

```
[0] id=0c854cd5-… disp="Generic Node"  kind="GenericNode"             compVer="core.meshery.io/v1alpha1" model="meshery-core" ns=false anno=true  cfgKeys=[metadata userMessages]
[2] id=6fb97580-… disp="default"        kind="Namespace"               compVer="v1"                        model="kubernetes"   ns=true  anno=false cfgKeys=[]
[4] id=fc0fa4d6-… disp="prometheus"     kind="ClusterRole"             compVer="rbac.authorization.k8s.io/v1" model="kubernetes" ns=false anno=false cfgKeys=[metadata rules]
[5] id=d9b3fa77-… disp="prometheus"     kind="ClusterRoleBinding"      compVer="rbac.authorization.k8s.io/v1" model="kubernetes" ns=false anno=false cfgKeys=[metadata roleRef subjects]
[6] id=6442fcca-… disp="prometheus-server-conf" kind="ConfigMap"      compVer="v1"                        model="kubernetes"   ns=true  anno=false cfgKeys=[data metadata]
[7] id=0edaf726-… disp="prometheus-ui"  kind="Ingress"                 compVer="networking.k8s.io/v1"      model="kubernetes"   ns=true  anno=false cfgKeys=[metadata spec]
[8] id=9466f34a-… disp="prometheus-secret" kind="Secret"               compVer="v1"                        model="kubernetes"   ns=true  anno=false cfgKeys=[metadata data]
[9] id=b2e2a852-… disp="prometheus-service" kind="Service"             compVer="v1"                        model="kubernetes"   ns=true  anno=false cfgKeys=[metadata spec]
```

Notes:
- Namespaced K8s components commonly carry an **empty** `configuration` — the render form is derived from
  `component.schema` at deploy time.
- Annotation components (`meshery-core`) always carry `configuration.metadata` and often `configuration.userMessages`.
- `component.version` in a design is the **upstream API version** (`apps/v1`, `v1`, `networking.k8s.io/v1`), while
  the component's own `version` is the model-catalog revision (`v1.0.0`).

---

## C. Validation and import path

### C.1 Parse

`server/models/pattern/core/pattern.go` → `NewPatternFile` performs an `encoding.Unmarshal` into
`design.PatternFile`. **No Draft-07 JSON Schema validation is invoked on this path.** Consequence: structurally
wrong-but-unmarshalable documents load successfully; schema-invalid extra keys are silently dropped rather than
rejected.

### C.2 Import dispatch

`server/handlers/design_import.go`:

- Detect via `files.IdentifyFile`.
- `core.MesheryDesign` → parse directly into `PatternFile`, return.
- Otherwise convert, then `NewPatternFileFromK8sManifest(..., ignoreErrors=true, registry)`:
  - **Helm**, **Docker Compose**, **Kubernetes manifests**, **Kustomize** are supported inputs.
  - Unsupported source types return an error.
- `ignoreErrors=true` means components that cannot be resolved against the registry are **dropped without failing
  the import** — a silent-loss hazard for any design relying on exotic kinds.

### C.3 CLI

`mesheryctl design import` obtains available source types from `api/pattern/types`. **No confirmed local Design
schema validation** on the CLI path either.

### C.4 Version bridge

`server/models/pattern/utils/patternfile_version_bridge.go` converts legacy Design/Pattern documents to the
current form. This is the mechanism by which v1beta1 catalog designs and old `services:` fixtures load.

### C.5 Practical validation guidance

Because neither parse nor CLI enforces the JSON Schema, a candidate design must be checked explicitly against
`design.yaml`. Recommended offline gate: validate with a Draft-07 validator (e.g. `ajv`) against
`schemas/constructs/v1beta3/design/design.yaml` **plus** a compile step through the v1beta3 Go structs, and assert
`additionalProperties == false` at the top level.

---

## D. Real design evidence

`docs/data/catalog/` contains **361** designs at `*/0.0.1/design.yml`; **102** have non-empty components.
Aggregate statistics across them:

- Design `schemaVersion`: `v1beta1` 180, `v1beta3` 1.
- Component `schemaVersion`: `components.meshery.io/v1beta1` 1809, blank 6.
- Relationship `schemaVersion`: `relationships.meshery.io/v1alpha3` 6026, blank 93.
- Relationship `kind`: `hierarchical` 6085, `edge` 34.
- Relationship `type`: `sibling` 4706, `parent` 1379, `binding` 32, `non-binding` 2.
- Component `isAnnotation`: `false` 1397, `true` 418.
- Models used: `kubernetes` 1358, `meshery-core` 388, `aws` 13, `digitalocean-icons` 9, `dapr` 7,
  `meshery-shapes` 7, `istio-base` 6.

Worked reference: `docs/data/catalog/3c3439a0-d215-4a71-aa47-13a5f2d007b7/0.0.1/design.yml`
(`prometheus_kubernetes`, 10 components, 50 relationships, `0.0.127`).
Its pattern: 2 `meshery-core` annotation/grouping nodes + 8 real `kubernetes` resources, with
`hierarchical/parent/inventory` for namespace membership and `hierarchical/sibling/matchlabels` for label propagation.

Other references: `e79ebaa2-…/0.0.1/design.yml` (Online Boutique, 49 components), `ui/tests/e2e/assets/GuestBook App.yml`
(minimal legacy, `v1beta1`, empty arrays).

**Fixtures that are NOT Designs** (do not use as templates):
`mesheryctl/tests/e2e/003-design/fixtures/design-import/nginx.yaml` is a raw Kubernetes manifest.

---

## E. Relationship model — blueprint vs instance

This distinction is the single most important structural fact for authoring.

### E.1 Blueprint (in the model catalog) — `models/<model>/<ver>/relationships/*.json`

Selectors identify participants by **kind/model/match**, with `id: null`:

```json
{
  "kind": "hierarchical", "type": "parent", "subType": "inventory",
  "status": "enabled", "schemaVersion": "relationships.meshery.io/v1beta2", "version": "v1.0.0",
  "selectors": [{ "allow": {
      "from": [{ "id": null, "kind": "Container", "match": {},
                 "model": { "name": "meshery-core", "registrant": {"kind": "github"} },
                 "patch": { "patchStrategy": "replace", "mutatorRef": [["configuration","spec","containers","_"]] } }],
      "to":   [{ "id": null, "kind": "Pod", "match": {},
                 "model": { "name": "kubernetes" },
                 "patch": { "patchStrategy": "replace", "mutatedRef": [["configuration","spec","containers","_"]] } }]
    }, "deny": { "from": [], "to": [] } }],
  "evaluationQuery": ""
}
```

File names encode the triple: `edge-binding-mount-cnndn.json` = `edge` / `binding` / `mount`.

### E.2 Instance (in a saved design) — `selectors[].allow.from|to[].id`

`id` is the **concrete component UUID from that design's `components[]`**, and the embedded `model` blob is
fully resolved (registrant included). `kind` may be `"*"` for wildcards. A generic no-op membership relationship
in a real design looks like:

```yaml
selectors:
  - allow:
      from: [{ id: <component-uuid>, kind: "*", patch: { patchStrategy: replace, mutatedRef: [["configuration","metadata","namespace"]] } }]
      to:   [{ id: <namespace-uuid>, kind: Namespace, patch: { patchStrategy: replace, mutatorRef: [["displayName"]] } }]
```

`patch.mutatorRef` = path read from the `to` node; `patch.mutatedRef` = path written on the `from` node.

### E.3 Available Kubernetes relationship blueprints (`v1.36.0/v1.0.0`, 102 files)

| kind | type | subType | count | Example file |
|---|---|---|---|---|
| edge | non-binding | reference | 84 | `edge-non-binding-reference-deployment.json` |
| edge | non-binding | network | 4 | `edge-non-binding-network-*.json` |
| edge | binding | mount | 3 | `edge-binding-mount-*.json` |
| edge | binding | reference | 12 | `edge-binding-reference-*.json` |
| edge | non-binding | firewall | 2 | `edge-binding-firewall-*.json` |
| edge | binding | permission | 1 | `edge-binding-permission-homji.json` |
| hierarchical | parent | wallet | 2 | `hierarchical-parent-wallet-*.json` |
| hierarchical | parent | alias | 2 | `hierarchical-parent-alias-iicqa.json` |
| hierarchical | parent | inventory | 5 | `hierarchical-parent-inventory-*.json` |
| hierarchical | sibling | matchlabels | 1 | `sibling-tagsets.json` |

Useful real definitions:
- `sibling-tagsets.json` — `hierarchical/sibling/matchlabels`, `from` and `to` both `kind: "*"`, `model: "*"`,
  `match: {"refs": [["configuration","metadata","labels"]]}`, `patch: null`. This is the generic
  "share labels" primitive.
- `hierarchical-parent-wallet-qimdk.json` — `EndpointSlice -> Service` label write.
- `hierarchical-parent-inventory-dfdpsbf.json` — `meshery-core Container -> kubernetes Pod`.

`meshery-core` ships **no** relationship blueprints; only `components/` and `connections/`.

---

## F. Model catalog inventory

`models/` holds 477 model directories (≈1.4 GB). Structure is
`models/<name>/<modelVersion>/<componentVersion>/{components,relationships,model.json}`.

Latest available for technologies relevant to an AI-native platform:

| Model | Version | Components | Rels |
|---|---|---|---|
| `kubernetes` | **v1.37.1** | 158 | 102 |
| `meshery-core` | 0.7.2 / v1.0.0 | 18 | 0 |
| `kube-prometheus` | 89.2.2 | 10 | 0 |
| `kube-prometheus-stack` | 89.2.2 | 10 | 20 |
| `istio-base` | 1.16.0 | 15 | 3 |
| `nginx-ingress` | 2.7.3 | 12 | 0 |
| `kong` | 3.4.1 | 12 | 0 |
| `apisix-ingress-controller` | 0.8.0 | 5 | 0 |
| `traefik-mesh` | 4.1.1 | 4 | 0 |
| `cert-manager` | v1.21.2 | 6 | 0 |
| `loki` | 18.13.7 | 2 | 0 |
| `kubevault` | 2026.8.7 | 23 | 0 |
| `kubevault-operator` | 0.25.0 | 21 | 0 |
| `keycloak-operator` | 0.0.4 | 2 | 0 |
| `redis-operator` | v0.26.0 | 4 | 0 |
| `pg-operator` | 3.1.0 | 8 | 0 |
| `postgres-with-operator` | 0.1.0 | 1 | 0 |
| `jaegertracing` / `jaeger-operator` | jaeger-3.4.1 | 1 | 0 |
| `kserve` | 1.0.2 | 9 | 0 |
| `kubedl` | v0.5.0 | 14 | 0 |
| `training-operator` | 1.2.2 | 4 | 0 |
| `sumologic` | 4.18.0 | 12 | 0 |
| `dapr` | 0.1.5 | — | — |

`kubernetes` model versions available: `v1.35.0` … `v1.37.1` (incl. `-alpha`/`-beta`/`-rc`). **v1.37.1 is the
newest stable**; earlier notes referencing v1.36.0 (153 components) are one release behind (158 in v1.37.1).

### F.1 Kubernetes components confirmed present in `v1.37.1`

`Deployment`, `Service`, `ConfigMap`, `Secret`, `Namespace`, `Ingress`,
`HorizontalPodAutoscaler`, `PodDisruptionBudget`, `NetworkPolicy`,
`PersistentVolumeClaim`, `PersistentVolume`, `StorageClass`, `StatefulSet`, `DaemonSet`,
`Job`, `CronJob`, `ServiceAccount`, `Role`, `RoleBinding`, `ClusterRole`, `ClusterRoleBinding`,
`Endpoints`, `EndpointSlice`, `ReplicaSet`.

### F.2 Confirmed absent from the `kubernetes` model

`Gateway`, `GatewayClass`, `HTTPRoute`, `GRPCRoute`, `ServiceMonitor`, `PodMonitor`, `PrometheusRule`.

- `ServiceMonitor` / `PodMonitor` / `PrometheusRule` / `Probe` / `ScrapeConfig` / `Alertmanager` exist only in the
  **`kube-prometheus-stack`** (and `kube-prometheus`, `sumologic`) models, because they are CRDs from the
  Prometheus Operator, not core Kubernetes.
- Gateway API CRDs are absent from the `kubernetes` model. `HTTPRouteGroup` exists in `traefik-mesh` and
  `MeshHTTPRoute` in `kong-mesh` — mesh-scoped, **not** upstream Gateway API.

---

## G. `meshery-core` — the only sanctioned way to express non-Kubernetes concepts

`meshery-core` 0.7.2/v1.0.0, `schemaVersion: models.meshery.io/v1beta2`, category
`Orchestration & Management` / `Application Definition & Image Build`. 18 components:

`AnchorNode`, `BoundingBox`, `Comment`, `Connection`, `Container`, `Credential`, `Environment`,
`GenericNode`, `ImageNode`, `NodeGroupInventoryWallet`, `Pencil`, `PenConnectorNode`, `Pen`, `PenTerminal`,
`Picture`, `Section`, `TextBox`, `WASMFilter`.

All use `core.meshery.io/v1alpha1` component version.

| Component | `isAnnotation` | Role |
|---|---|---|
| `GenericNode` | true | free-form node for arbitrary/abstract concepts |
| `Container` | true | grouping box; also the `from` side of the Container→Pod inventory blueprint |
| `Section` | true | grouping / layer band |
| `BoundingBox` | true | visual grouping |
| `NodeGroupInventoryWallet` | true | grouping + inventory binding target |
| `TextBox` | true | free text |
| `Comment` | true | annotation text |
| `Connection` | true | explicit edge node |
| `Environment` | **false** | environment scoping |
| `Credential` | true | secret/credential reference |
| `WASMFilter` | true | filter transform |
| `Pen*`, `AnchorNode`, `ImageNode`, `Picture` | true | canvas primitives |

`meshery-core` also ships `connections/`: `ArtifactHubConnection`, `GitHubConnection`, `GrafanaConnection`.

**This is the mechanism for the AI-native layer.** There is no model for an "AI agent", "agent runtime", or
"LLM endpoint". `GenericNode` / `Container` / `Section` + `isAnnotation: true` is the valid encoding of such
concepts. In the 361 real designs, `meshery-core` is the second most-used model (388 occurrences), and 418
components carry `isAnnotation: true` — this is normal, established practice upstream, not a hack.

---

## H. `meshery-mcp-server` status

- **Zero** Go, TypeScript, or JavaScript source files.
- No `go.mod`, no `package.json`, no Kubernetes manifests, no Meshery Design, no Meshery model, no component.
- Contents are scaffolding/docs/build files only.

Therefore Meshery MCP Server is **not** a `REAL_COMPONENT`. Any design element representing it must be either
(a) an `ARCHITECTURAL_CONCEPT` expressed as a `meshery-core` annotation component, or (b) deferred until the
project ships a deployable artifact with a container image — at which point a generic `kubernetes` `Deployment` +
`Service` pair is the honest representation. Neither route may be described as "deploying the real Meshery MCP
Server" today.

---

## I. Technology classification matrix

Legend: **RC** = `REAL_COMPONENT` · **AC** = `ARCHITECTURAL_CONCEPT` (must be encoded via `meshery-core`) ·
**NF** = `NOT_FOUND` (no upstream representation) · **NFI** = `NEEDS_FURTHER_INVESTIGATION`

| Technology | Class | Evidence / representation |
|---|---|---|
| Kubernetes workloads (`Deployment`, `StatefulSet`, `Job`, `CronJob`, `DaemonSet`) | **RC** | `kubernetes` v1.37.1 |
| Kubernetes networking (`Service`, `Ingress`, `NetworkPolicy`, `EndpointSlice`) | **RC** | `kubernetes` v1.37.1 |
| Kubernetes config/identity (`ConfigMap`, `Secret`, `ServiceAccount`, `Role`, `RoleBinding`, `ClusterRole`, `ClusterRoleBinding`) | **RC** | `kubernetes` v1.37.1 |
| Kubernetes storage (`PVC`, `PV`, `StorageClass`) | **RC** | `kubernetes` v1.37.1 |
| Kubernetes reliability (`HPA`, `PodDisruptionBudget`) | **RC** | `kubernetes` v1.37.1 |
| Namespacing (`Namespace`) | **RC** | `kubernetes` v1.37.1 |
| Prometheus (CRD `Prometheus`) | **RC** | `kube-prometheus-stack` 89.2.2 |
| Prometheus Operator CRDs (`ServiceMonitor`, `PodMonitor`, `PrometheusRule`, `Probe`, `ScrapeConfig`, `Alertmanager`, `ThanosRuler`, `TargetAllocator`) | **RC** | `kube-prometheus-stack` / `kube-prometheus` / `sumologic` |
| Grafana | **NFI** | **No `grafana` model.** `grafana-ui-server` 2022.6.14 exposes only `GrafanaDashboard`. A full `Grafana` component exists only inside `fmtok8s-conference-chart` 0.1.4 (`Grafana`, `GrafanaDashboard`, `GrafanaDataSource`, `GrafanaNotificationChannel`) — an unrelated community chart; embedding it couples the design to a third-party chart. Recommend `GenericNode` + `kube-grafana-dashboards`, or revisit. |
| Loki | **RC** | `loki` 18.13.7 (2 components) |
| Jaeger | **RC** | `jaegertracing` / `jaeger-operator` jaeger-3.4.1 |
| Tempo | **NF** | Only `meshery-dev-icons/0.7.2/…/tempo.json` — an **icon**, not a component. No Tempo model exists. |
| OpenTelemetry Collector | **RC** | `sumologic` 4.18.0 → `OpenTelemetryCollector` (`kind: OpenTelemetryCollector`, `version: opentelemetry.io/v1alpha1`, `isNamespaced: true`, `status: enabled`). Also `MeshOpenTelemetryBackend` in `kuma`/`kong-mesh`; `AWS Distro for OpenTelemetry` in `aws`. |
| Gateway API (`Gateway`, `GatewayClass`, `HTTPRoute`) | **NF** | Absent from `kubernetes` v1.37.1. Only `HTTPRouteGroup` (`traefik-mesh`) and `MeshHTTPRoute` (`kong-mesh`) exist — mesh-specific, not upstream Gateway API. Use `kubernetes` `Ingress`, or `nginx-ingress` / `kong` / `apisix-ingress-controller` / `traefik-mesh` as the ingress layer. |
| Ingress controllers | **RC** | `nginx-ingress` 2.7.3, `kong` 3.4.1, `apisix-ingress-controller` 0.8.0, `traefik-mesh` 4.1.1 |
| Service mesh | **RC** | `istio-base` 1.16.0 (15 comps, 3 rels). Also `kuma`, `linkerd`, `kiali-operator` |
| Postgres | **RC** | `pg-operator` 3.1.0 (8 comps) or `postgres-with-operator` 0.1.0 (1 comp). Also `cloudnative-pg`, `cnpg-sandbox`, `kubedb` |
| Redis | **RC (operator form only)** | `redis-operator` v0.26.0 (4 comps), `redis-db-assignment-operator`. **No plain standalone Redis component**; the design deploys the operator + CR, not a bare Redis pod. |
| Keycloak | **RC** | `keycloak-operator` 0.0.4 (2 comps) |
| Vault | **RC** | `kubevault` 2026.8.7 (23 comps), `kubevault-operator` 0.25.0 (21 comps) |
| cert-manager | **RC** | `cert-manager` v1.21.2 (6 comps) |
| LLM inference / model serving | **RC (but heavyweight)** | `kserve` 1.0.2 (`InferenceService`, `Predictor`, `ServingRuntime`, `TrainedModel`, `ClusterServingRuntime`), `kubedl` v0.5.0 (`Inference`, `Model`, `ModelVersion`). Both assume KubeFlow/operator CRDs. |
| Training jobs | **RC (off-scope)** | `training-operator` 1.2.2 (`PyTorchJob`, `TFJob`, `MXJob`, `XGBoostJob`) |
| Ollama | **NF** | No model, no component anywhere in `models/`. |
| "AI agent" / "agent runtime" | **AC** | No model. Encode as `meshery-core` `GenericNode` (or `Container` for a group) with `isAnnotation: true`. |
| Agent↔tool MCP links | **AC** | `meshery-core` `Connection` component, or a `Container`→X `edge/non-binding` relationship. `meshery-mcp-server` has no deployable artifact (see H). |
| External LLM / cloud model endpoint | **AC** | No model. `meshery-core` `GenericNode` + `Connection`. |
| Environment scoping | **RC** | `meshery-core` `Environment` (`isAnnotation: false`) |
| Credential references | **RC** | `meshery-core` `Credential` |
| Grouping / canvas structure | **RC** | `meshery-core` `Container`, `Section`, `BoundingBox`, `NodeGroupInventoryWallet` |
| `digitalocean-icons`, `meshery-shapes`, `meshery-dev-icons`, `meshery-flowchart` | **RC (decorative only)** | Icon/shape models. `meshery-dev-icons/tempo.json` proves these are presentation assets, not components. |

---

## J. Smallest valid advanced design (recommendation only — no artifact produced)

The smallest design that is simultaneously (a) schema-valid at v1beta3, (b) fully backed by real
`REAL_COMPONENT`s, and (c) recognisably "AI-native" is:

**Layer 1 — Real, deployable (all RC, all `kubernetes` v1.37.1):**
`Namespace` (ai-platform), plus a `ConfigMap`, `Secret`, and one `Deployment` + `Service` per stateless AI
service. If an ingress is needed: `Ingress` (or `nginx-ingress` components). Wire every namespaced component to
the namespace with `hierarchical/parent/inventory` (`mutatedRef: [["configuration","metadata","namespace"]]`),
and group by labels with `hierarchical/sibling/matchlabels`.

**Layer 2 — Observability, real but only if wanted:**
`kube-prometheus-stack` `Prometheus` + `ServiceMonitor`, optionally `loki` and `jaegertracing`. `sumologic`'s
`OpenTelemetryCollector` gives a genuine OTel component without inventing one. `Grafana` is **not** cleanly
available — keep it as a `GenericNode` rather than coupling to `fmtok8s-conference-chart`.

**Layer 3 — AI-native abstraction, all AC via `meshery-core`:**
`GenericNode` for each agent / model endpoint / MCP tool server, wrapped in `Container` groups, joined by
`Connection` components, scoped by an `Environment`. This is the upstream-sanctioned encoding and matches the
388 existing `meshery-core` usages in the catalog.

**Explicitly excluded as unrepresentable today:** Ollama, Tempo, and upstream Gateway API CRDs.

Deliberately **not** recommended for a *smallest* design: `istio-base`, `kserve`, `kubevault`,
`keycloak-operator`, `pg-operator`, `redis-operator`. Each is individually valid but each drags in operator CRDs,
and `istio-base` + `kserve` + `kubevault` together would dominate the design. They belong in an expanded variant.

---

## K. Risks and gotchas

1. **No runtime schema validation.** `NewPatternFile` only unmarshals. Extra top-level keys are silently dropped,
   not rejected, and `additionalProperties: false` means they are invalid. Validate offline against `design.yaml`.
2. **Silent component loss on import.** `NewPatternFileFromK8sManifest(..., ignoreErrors=true, registry)` drops
   unresolvable components. A design built by import may quietly contain fewer components than intended.
3. **Legacy is the only populated reference.** All 180 non-empty catalog designs are v1beta1 with
   `v1beta1` components and `v1alpha3` relationships. Copying them forward textually is *not* the same as
   authoring at v1beta3, even though both parse.
4. **`id` must be a real UUID.** Catalog files use the zero UUID; design instances need unique per-component
   UUIDs, and relationship selectors must reference exactly those.
5. **Namespace membership is a relationship, not metadata.** `metadata.namespace` alone is not what makes a
   component namespaced in a design; the `hierarchical/parent/inventory` selector performs the write.
6. **CRDs are not in the `kubernetes` model.** ServiceMonitor/PrometheusRule live in `kube-prometheus-stack`.
   Looking for them under `kubernetes` wastes time and yields a false "not found".
7. **Most models ship zero relationship blueprints.** Only `kubernetes` (102), `kube-prometheus-stack` (20), and
   `istio-base` (3) have any. Elsewhere, relationships must be authored in the design as instance selectors
   rather than referenced by blueprint id.
8. **`meshery-core` has no relationships at all.** Cross-model edges from annotation nodes must be hand-authored.
9. **Do not treat icon models as components.** `meshery-dev-icons/tempo.json` looks like a Tempo component but is
   an icon; a `meshery-shapes` entry is a shape.
10. **`meshery-mcp-server` is empty.** Any claim of deploying it in a design would be false today.
11. **Toolchain.** Meshery requires Go 1.26.4; system `go` is 1.22.2. Use the cached 1.26.4 toolchain explicitly.
12. **Empty workspace specs.** `spec/*.md` and `docs/README.md` in `meshery-designs` are 0 bytes; there is no
    written source of truth to validate a design against.

---

## L. Open questions / next steps

1. **Grafana** — is depending on `fmtok8s-conference-chart`'s `Grafana` component acceptable, or should Grafana
   remain a `GenericNode`? This is the only `RC`-vs-`AC` judgement call with real trade-offs.
2. **Mesh necessity** — is `istio-base` justified for the AI-native platform, or is plain `Ingress` +
   `nginx-ingress` sufficient? Drives whether the design is "smallest valid" or "expanded".
3. **MCP representation** — confirm `meshery-core` `Connection` for agent↔tool links, versus deferring the MCP
   server entirely until `meshery-mcp-server` ships a deployable artifact.
4. **LLM serving** — `kserve` `InferenceService` vs `kubedl` `Inference` vs a plain `Deployment` + `Service`.
   Only the last is small; the first two assume operator CRDs.
5. **Redis form** — accept the operator-only reality, or represent a plain Redis as `Deployment` + `Service`?
6. **Persistence layer** — none of the workspace spec files are populated, so Postgres/Redis/Keycloak/Vault
   inclusion is currently unconstrained by any written requirement.
7. **Authoring target version** — confirm the design should be authored at `designs.meshery.io/v1beta3` with
   `components.meshery.io/v1beta2` / `relationships.meshery.io/v1beta2`, given that no non-empty v1beta3
   upstream reference exists.
8. **Validation harness** — before any design is written, add a repeatable gate: Draft-07 validation against
   `design.yaml` plus a compile/unmarshal through `github.com/meshery/schemas/models/v1beta3/design`, with an
   explicit `additionalProperties` check.

---

## Appendix — how the empirical claims were verified

The 361-design statistics, the v1beta3 `required`/`additionalProperties` values, the component/relationship field
shapes, and the "v1beta1 parses cleanly into v1beta3" claim were each read or executed directly:

- Schema facts: `~/go/pkg/mod/github.com/meshery/schemas@v1.3.37/schemas/constructs/v1beta3/design/design.yaml`.
- Catalog statistics: aggregated with `json`/`glob` over `meshery/docs/data/catalog/*/0.0.1/design.yml`.
- Model inventories: directory listings of `meshery/models/**/{components,relationships}`.
- Parse behaviour: `go run` of a throwaway probe at `/tmp/opencode/dsgnprobe/main.go` that calls
  `encoding.Unmarshal` into `github.com/meshery/schemas/models/v1beta3/design.PatternFile` for
  `3c3439a0-…/design.yml` and prints every component and relationship selector. Result: parse succeeded,
  10 components and 50 relationships recovered with UUID-joined selectors intact.

No file in `meshery`, `meshery-mcp-server`, or `meshery-designs` was modified. This report is the only file
created.
