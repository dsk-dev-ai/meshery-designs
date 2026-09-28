# Architectural Decisions — `ai-native-platform`

Fourteen decisions. Each records the alternatives that were rejected and why, so a later reviewer can tell the
difference between a considered choice and an oversight.

Status of all decisions: **Accepted**. No decision is deferred.

---

## ADR-001 — Author the design at `designs.meshery.io/v1beta3`

**Context.** `RECONNAISSANCE.md` §B.2 established that the catalog holds 180 non-empty designs, all at
`designs.meshery.io/v1beta1` with `components.meshery.io/v1beta1` and `relationships.meshery.io/v1alpha3`. The one
v1beta3 design is empty (0 components, 0 relationships, no `name`). There is no non-empty v1beta3 reference to
copy from.

**Decision.** Author at `designs.meshery.io/v1beta3`, components `components.meshery.io/v1beta2`, relationships
`relationships.meshery.io/v1beta2`.

**Alternatives rejected.**
- *v1beta1, for consistency with the catalog.* Rejected. The catalog is a legacy corpus, not a specification. A
  new design written to a superseded schema acquires debt immediately and will need the version bridge anyway.
- *Defer the choice.* Rejected. The schema determines the required-field set for all 66 components and 111
  relationships. It must be fixed before authoring begins.

**Consequences.** Every component carries 11 required fields and every relationship 7, including several that the
v1beta1 corpus omits. This is stricter than the examples in the catalog but is what the v1beta3 schema actually
requires. Verified by direct read of `constructs/v1beta3/design/design.yaml` and
`constructs/v1beta2/{component,relationship}`.

**Evidence that v1beta1 still loads.** `RECONNAISSANCE.md` Appendix established by execution that a v1beta1
catalog design parses cleanly into the v1beta3 Go structs. So the v1beta3 choice costs compatibility with nothing
and gains forward-consistency.

---

## ADR-002 — Represent AI-native layers as annotations; do not fabricate workloads

**Context.** Target layers 1–5 (MCP access, agent runtime, model router, fallback tiers, grounding) have no
native Meshery model. `meshery-mcp-server` contains zero Go, TypeScript, and JavaScript files, no `go.mod`, no
`package.json`, no manifests, and no container image. No model anywhere in the 477-model catalog describes an
agent, a router, an LLM endpoint, or a context store.

**Decision.** Express all of layers 1–5 with `meshery-core` 0.7.2 `GenericNode` components carrying
`metadata.isAnnotation: true`. Attach no fabricated `Deployment` to them. Give each layer a real configuration
artifact where one is meaningful (`cm-agent-runtime`, `cm-model-router`, `sec-registry-creds`).

**Alternatives rejected.**
- *Add a `Deployment` + `Service` for each conceptual layer, with configuration left to deploy time.* Rejected.
  This is the most tempting option and the most dishonest. A `Deployment` is a real component, so the design would
  be schema-valid — but it would assert that a workload exists at deploy time. Nothing would produce a working
  pod, and the failure would surface as a crash-looping container rather than as an honest "not implemented."
- *Define a custom model for agents and routers.* Rejected and prohibited. It would require registry publication
  and would misrepresent the state of the ecosystem.
- *Omit layers 1–5 entirely and build only the Kubernetes substrate.* Rejected. The request is for an AI-native
  platform; a design containing only namespaces and databases does not answer it.

**Consequences.** Nine annotation components carry the AI-native architecture, and nine components produce no
cluster resources. This is stated explicitly in the design via the `note-annotation-vs-infrastructure` and
`note-deferred-ai-workloads` comments, so a deployer cannot miss it.

**Mitigation.** Each conceptual layer that admits a concrete configuration contract gets one. This is why
`cm-agent-runtime` and `cm-model-router` exist as real `ConfigMap`s: they make the annotation layer reviewable
rather than decorative. Promotion paths are recorded in `UNSUPPORTED_CONCEPTS.md`.

---

## ADR-003 — No service mesh

**Context.** Layer 11 asks for security boundaries. A mesh (`istio-base` 1.16.0, 15 components) is available and
would supply mTLS, authorisation policy, and traffic management.

**Decision.** No service mesh. Security boundaries are expressed with `NetworkPolicy`, `ServiceAccount`, `Role`,
`RoleBinding`, and `ValidatingAdmissionPolicy`.

**Alternatives rejected.**
- *`istio-base`.* Rejected: prohibited by instruction, and independently unjustified. No layer requires mutual mTLS
  between platform services — the only east-west flows are control-plane→stores, collector→workloads, and
  Prometheus→targets, all of which are adequately served by `NetworkPolicy`. It would add 15 components and a
  second networking model to a design whose networking need is three flows.
- *Cilium for `CiliumNetworkPolicy`.* Rejected on the same grounds plus an unstated CNI dependency.

**Consequences.** No mTLS between platform services, and no fine-grained L7 authorisation. If those become
requirements, a mesh should be added as a *separate* design rather than retrofitted — the annotation layer is
already positioned to reference it.

---

## ADR-004 — State via `StatefulSet`, not database operators

**Context.** Layer 9 requires Redis and PostgreSQL state. Available models: `redis-operator` v0.26.0
(`Redis`, `RedisCluster`, `RedisReplication`, `RedisSentinel`), `pg-operator` 3.1.0 (`PostgresCluster`,
`PerconaPGCluster`, backups, upgrades, `PGAdmin`), `postgres-with-operator` 0.1.0 (`Kubegres`).

**Decision.** `StatefulSet` + `Service` + `PersistentVolumeClaim` for each store. `sec-state-creds` carries
credentials. No operator.

**Alternatives rejected.**
- *`redis-operator` / `pg-operator`.* Rejected. Both require a controller plus CRDs plus often a CRD-backing
  operator (`Kubegres` needs CloudNativePG; `PerconaPGCluster` needs the Percona operator). For a design whose
  state needs are two stores with one writer and one reader, that is a control loop in exchange for nothing. It
  also contradicts the brief's instruction not to include unsupported operators for complexity — these are
  supported, but they are complexity without function.
- *Managed cloud databases.* Rejected: would be a cloud model, and no cloud model is needed elsewhere in the
  design.

**Consequences.** The design does not express failover, backup scheduling, or connection-pool management. Those
are legitimate gaps, stated here rather than papered over. If the platform later needs them, the promotion is
local: add the operator model and swap the two `StatefulSet`s for its CRs.

**Cost accepted.** Two `Service → StatefulSet` edges and two `Secret → StatefulSet` edges have no upstream
blueprint and must be hand-authored (`RELATIONSHIP_MATRIX.md` §3, §6).

---

## ADR-005 — Network security with native `NetworkPolicy`

**Context.** Layer 11 requires isolation between control, runtime, state, and observability namespaces.

**Decision.** `netpol-default-deny` (deny-all baseline) and `netpol-ai-allowlist` (explicit east-west
permissions), both native `kubernetes` v1.37.1 `NetworkPolicy`.

**Alternatives rejected.**
- *Gatekeeper / Kyverno / OPA.* Rejected: each adds an operator, a CRD family, and a failure mode. Also out of
  scope — they are policy engines, not network controls.
- *Omit NetworkPolicy and rely on namespace separation.* Rejected. Namespace separation alone is not isolation;
  without a deny baseline, any pod in any namespace can reach any other.

**Consequences.** Isolation depends on a CNI that enforces `NetworkPolicy`. The design does not assert which CNI
is installed, because that is a cluster property rather than a platform one. This assumption should be confirmed
during validation (`VALIDATION_PLAN.md` §7).

**Known gap.** Both firewall blueprints in the catalog target `Pod`, and the design declares no `Pod`
components, so no firewall `edge` can be authored. Recorded in `RELATIONSHIP_MATRIX.md` §6.1.

---

## ADR-006 — Policy boundary via `ValidatingAdmissionPolicy`

**Context.** Layer 7 requires a validation/policy boundary. This is the design's only opportunity for a *real*
enforcement point, because the rest of layer 7 is conceptual.

**Decision.** `vap-required-labels` (a `ValidatingAdmissionPolicy`) bound by `vapb-ai-runtime` (a
`ValidatingAdmissionPolicyBinding`) to the runtime and state namespaces. Additionally `quota-ai-runtime`
(`ResourceQuota`) and `limits-ai-runtime` (`LimitRange`).

**Alternatives rejected.**
- *Gatekeeper / Kyverno.* Rejected: operator plus CRD family for a policy that fits in one native object. The
  native policy is evaluated in-process by the API server — no webhook, no extra latency, no extra failure mode.
- *`ValidatingWebhookConfiguration` (also available in the model).* Rejected: requires deploying and maintaining a
  webhook server, which is a real workload with a real availability requirement. The native policy has none.
- *Cordon via `ResourceQuota` only.* Rejected: quota caps totals but cannot require a specific label or field.
  Layer 7 is about grounding metadata, so it needs a field-level policy.

**Consequences.** One real, operator-free enforcement point exists in the design. It checks labelling and
metadata presence, which is a genuine subset of the layer-7 intent. Request-time policy remains conceptual
(`policy-boundary`, `grounding-validator`) because no native construct can express it.

**Verified at authoring time.** The exact `component.version` strings were read from the catalog rather than
assumed, as this ADR originally required. Both are `admissionregistration.k8s.io/v1` — the GA `v1` API, not the
alpha `v1alpha1` that an earlier draft of this document assumed. Confirmed in
`models/kubernetes/v1.37.1/v1.0.0/components/ValidatingAdmissionPolicy.json` and
`…/ValidatingAdmissionPolicyBinding.json`, both `status: enabled`, `isAnnotation: false`. The remaining live
requirement is the cluster version, which must be ≥ 1.30 for the `v1` API — see `VALIDATION_PLAN.md` §7.

---

## ADR-007 — Exclude Grafana

**Context.** Layer 10 requires OpenTelemetry/Prometheus observability. Grafana is the conventional visualisation
layer. `RECONNAISSANCE.md` §I found no `grafana` model.

**Decision.** No Grafana component. Visualisation is out of scope for this design.

**Alternatives rejected.**
- *`fmtok8s-conference-chart` 0.1.4, which contains a real `Grafana` component.* Rejected: it is an unrelated
  community conference-sponsorship chart. Depending on it would couple the platform's observability to a
  third-party chart's release cadence, version numbering, and maintainers, purely to obtain one component.
- *`grafana-ui-server` 2022.6.14.* Rejected: it exposes only `GrafanaDashboard` — dashboards, not a running
  Grafana. It cannot serve as the visualisation tier.
- *`kube-grafana-dashboards`.* Rejected: dashboards without a Grafana to render them. Pointless on its own.

**Consequences.** The telemetry chain terminates at `alertmanager` and `promrule-platform-slo`. Consumers query
`prometheus` directly or render externally. This is a real functional gap, recorded rather than concealed.

**If Grafana becomes required.** The options are (a) contribute a `Grafana` component to a new `grafana` model
upstream, or (b) deploy Grafana outside Meshery's model system. Neither is a design-time decision.

---

## ADR-008 — Exclude `HorizontalPodAutoscaler`

**Context.** `HorizontalPodAutoscaler` is a confirmed real component in `kubernetes` v1.37.1. Layer 8 is
"Kubernetes infrastructure" and layer 12 is resilience; autoscaling is the reflexive choice for both.

**Decision.** No HPA.

**Alternatives rejected.**
- *HPA on `deploy-meshery-control`.* Rejected: a single control-plane Deployment is not a workload with variable
  load, and scaling it horizontally would break the `MeshSync`/`Broker` singleton assumption. An HPA here would be
  decorative and actively misleading.
- *HPA on `sts-redis` / `sts-postgres`.* Rejected: horizontally scaling a stateful store requires sharding
  behaviour the design has no mechanism to express. Attaching an HPA would imply a capability the design lacks.
- *HPA for the sake of layer coverage.* Rejected as a category. This is the clearest example in the design of
  "every component must have a reason" being decisive.

**Consequences.** Capacity scaling is left to cluster-level autoscaling of the nodes themselves, which is
independent of this design. `pc-ai-critical`, the two PDBs, `quota-ai-runtime`, and `limits-ai-runtime` carry the
resilience and resource-containment story on their own.

---

## ADR-009 — `Section` for layer bands, not `Container`

**Context.** The design needs visual/logical bands so a reader can see the 12 layers.
`meshery-core` offers `Container`, `Section`, and `BoundingBox`, all `isAnnotation: true`.

**Decision.** `Section` for the eight layer bands. `hierarchical` / `parent` / `alias` for containment, with
`metadata.isAnnotation: true`.

Verified in the catalog: `Section` is `meshery-core` 0.7.2 `Section`, `component.version
core.meshery.io/v1alpha1`, `isAnnotation: true`, `status: enabled` — so the declared annotation value matches
upstream rather than overriding it.

**Alternatives rejected.**
- *`Container`.* Rejected. `Container` has a real upstream blueprint pairing it with `Deployment`
  (`hierarchical-parent-alias-iicqa.json`). Using it would authorise exactly one real grouping edge
  (`deploy-meshery-control`), because the design has one `Deployment` and no `Pods`. Beyond that it would imply
  workload containment that does not exist, and would put a second, similar-looking primitive alongside `Section`
  for no functional gain. `Section` also has `genealogy: parent` and a rectangle shape, which suits a wide band
  spanning both annotations and native components.
- *`BoundingBox`.* Rejected: it is a drawing aid with no grouping semantics. A band that a reader cannot
  programmatically associate with its members is not a band.
- *`NodeGroupInventoryWallet`.* Rejected: its semantics are inventory binding, which is not what a layer band is.

**Consequences.** Section containment is provenance C (analogy with the real `Container` blueprint), not
provenance B. No blueprint pairs `Section` with anything. This is disclosed in
`RELATIONSHIP_MATRIX.md` §7 and is the one place where the design's grouping edges are not directly
blueprint-backed.

---

## ADR-010 — Use `sumologic`'s `OpenTelemetryCollector`, with provenance disclosed

**Context.** Layer 10 requires OpenTelemetry. A search of all 477 models found real
`OpenTelemetryCollector` components in exactly one place: `sumologic` 4.18.0. Also available:
`MeshOpenTelemetryBackend` (`kuma`, `kong-mesh` — mesh-scoped, not a collector) and
`AWS Distro for OpenTelemetry` (`aws` — cloud-specific). `istio-base` and `kiae` have a `Telemetry` component
that is an Istio/Kiali tracing config, not a collector.

**Decision.** Use `sumologic` 4.18.0 `OpenTelemetryCollector`
(`kind: OpenTelemetryCollector`, `component.version: opentelemetry.io/v1alpha1`, `isNamespaced: true`,
`status: enabled`). Disclose the model provenance in `COMPONENT_INVENTORY.md` and in the component's
`description`.

**Alternatives rejected.**
- *A dedicated OTel model.* Rejected: none exists. Creating one is out of scope and would be inventing a model.
- *`MeshOpenTelemetryBackend` from `kuma`.* Rejected: it is a Kuma mesh resource describing where a mesh sends
  traces. It is not a collector and cannot receive, process, or export telemetry. Using it would be a category
  error.
- *A bare `kubernetes` `Deployment` running a collector.* Rejected: that would assert a workload with no
  upstream CRD, which is the fabrication ADR-002 prohibits. The CRD is preferable because it is real and
  declared in its own right.
- *Drop OpenTelemetry and keep only Prometheus.* Rejected: layer 10 explicitly requires OpenTelemetry, and
  `OpenTelemetryCollector` is genuinely available.

**Consequences.** The design's telemetry model is tied to a model published by an observability vendor. This is
acceptable because the component is the upstream `opentelemetry.io` CRD and is vendor-neutral in substance. It
must be disclosed, not hidden — hence the `description` on the component and the ADR.

**Consequence for relationships.** `sumologic` ships no `relationships/` directory — verified: the model contains
only `components/` and `model.json` — so the `otel-collector → prometheus` edge has no blueprint. Hand-authored as
A-9. For the provenance tally it is counted once, as class **A** (annotation-to-native correspondence), with its
hand-authored nature recorded alongside rather than double-counted. See `RELATIONSHIP_MATRIX.md` §9 and §11.

---

## ADR-011 — Include `deploy-meshery-control` as a generic `Deployment`

**Context.** Layer 6 needs a control layer. `meshery-operator` 1.0.70 provides real `MeshSync` and `Broker` CRDs
but no server component. An `Ingress` also needs a backend to be meaningful.

**Decision.** Declare `deploy-meshery-control` as a `kubernetes` v1.37.1 `Deployment` (`apps/v1`) with minimal
`configuration`, plus `svc-meshery-control` and `ingress-ai-platform`.

**Alternatives rejected.**
- *No Deployment; leave the Ingress dangling.* Rejected: an `Ingress` with no backend is a broken declaration, and
  it would leave layer 1 without a real entry point.
- *Reuse ADR-002's reasoning to omit the control plane too.* Rejected: the difference is material. Meshery's
  control plane and its CRDs genuinely exist and are published in the model catalog. A generic `Deployment` here
  asserts a workload slot for a real, publicly available server — not for something imaginary. The
  conceptual layers in ADR-002 have no such referent.
- *Model the server as a `GenericNode` instead.* Rejected: the control plane *is* the one part of layers 1–5
  that has real components. Reducing it to an annotation would misrepresent it downward.

**Consequences.** This is the single `Deployment` in the design, and it is the load-bearing backend for
`ingress-ai-platform`, `svc-meshery-control`, and `sm-platform` (via D15). Its `configuration` is left minimal
and image selection happens at deploy time — matching the upstream convention observed in the catalog reference
design, where namespaced components carry empty `configuration`.

**Consistency check.** ADR-002 is not violated: the same rule that forbids `Deployment`s for the agent runtime
forbids nothing here, because the control plane has a real referent and the agent runtime does not.

---

## ADR-012 — `Ingress`, not Gateway API

**Context.** Layer 1 needs an entry point. Gateway API (`Gateway`, `GatewayClass`, `HTTPRoute`) is the modern
answer.

**Decision.** `kubernetes` v1.37.1 `Ingress` (`networking.k8s.io/v1`).

**Alternatives rejected.**
- *Gateway API.* Rejected: `Gateway`, `GatewayClass`, `HTTPRoute`, and `GRPCRoute` are **absent** from the
  `kubernetes` model. Using them would mean declaring kinds that do not exist in the model — the exact failure
  mode the reconnaissance was commissioned to prevent.
- *`traefik-mesh` `HTTPRouteGroup` or `kong-mesh` `MeshHTTPRoute`.* Rejected: these are mesh-scoped CRDs from
  specific projects. They are not upstream Gateway API, and adopting them would import a mesh dependency
  (contradicting ADR-003) to reach an abstraction we do not need.
- *`nginx-ingress` / `kong` / `apisix-ingress-controller`.* Rejected: these are the controller *and* its
  configuration. A design that includes an ingress controller must also model its `IngressClass`, TLS, and
  controller deployment — a second subsystem with no stated requirement. `Ingress` defers the controller choice
  to the cluster, which is the right boundary for a platform design.

**Consequences.** North-south traffic management uses the `networking.k8s.io/v1` API. If Gateway API adoption
becomes a requirement, the correct action is to contribute `Gateway`/`HTTPRoute` components upstream to the
`kubernetes` model, not to substitute a mesh resource.

---

## ADR-013 — Three `matchlabels` edges, not hundreds

**Context.** `hierarchical` / `sibling` / `matchlabels` (`sibling-tagsets.json`) matches on shared labels. The
upstream reference design `3c3439a0-…/design.yml` uses 40 of these among 10 components; the Online Boutique
design has 1217 relationships among 49 components.

**Decision.** Three `matchlabels` edges, one representative pair per tier (state, observability, security).

**Alternatives rejected.**
- *Full pairwise `matchlabels` for every same-tier pair.* Rejected: the resulting graph is almost entirely no-op
  edges that add visual noise, inflate the file, and make real relationships harder to find. 40 edges among 10
  components in the reference design is a symptom of automated generation, not a standard to copy.
- *No `matchlabels` at all.* Rejected: label membership is the design's only tier-grouping mechanism, and
  `netpol-ai-allowlist` and quota reasoning refer to those labels. Three edges establish the pattern; the rest is
  documented intent.

**Consequences.** Tier membership is under-expressed in graph form. A reader must consult the component
descriptions. Accepted as the better trade: explicit and short beats exhaustive and unreadable.

---

## ADR-014 — Declare `components.meshery.io/v1beta2` uniformly

**Context.** The catalog is internally inconsistent. Measured across four models:
`kubernetes` v1.37.1 → all 158 components declare `components.meshery.io/v1beta2`;
`kube-prometheus-stack` 89.2.2 → all 10 declare `v1beta2`; but `meshery-core` 0.7.2 → all 18 declare `v1beta1`;
`sumologic` 4.18.0 → all 12 declare `v1beta1`. Meanwhile all 180 non-empty catalog designs declare `v1beta1`
components.

**Decision.** Declare `components.meshery.io/v1beta2` on every component in the design, including those sourced
from `meshery-core` and `sumologic`, whose catalog files say `v1beta1`.

**Alternatives rejected.**
- *Mirror each source model's declaration.* Rejected: it would produce a design where the component schema version
  varies by which model a concept came from, for no semantic reason. `meshery-core` and `sumologic` are simply
  stale relative to `kubernetes`.
- *Use `v1beta1` throughout to match the catalog corpus.* Rejected: the v1beta3 design schema `$ref`s
  `v1beta2/component` and `component.yaml` sets `default: components.meshery.io/v1beta2`. Declaring `v1beta1`
  against a v1beta2 `$ref` is a self-inconsistency.

**Consequences.** Component entries diverge from their source catalog file in two models. `schemaVersion` is a
free `VersionString` in the schema (not an enum), so both values validate, and the v1beta3 design references the
v1beta2 construct regardless. Uniform v1beta2 is forward-consistent.

**Verification requirement.** Confirm the server does not reject a `v1beta2` declaration for a `meshery-core`
component at load time — see `VALIDATION_PLAN.md` §4. This is the single highest-risk assumption in the design.
