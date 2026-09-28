# Unsupported Concepts — `ai-native-platform`

Every concept below is either absent from the Meshery model catalog or is excluded by a recorded decision. For
each: what it is, the upstream evidence, **how this design represents it without falsifying the Meshery model**,
and what would have to change to represent it natively.

The governing rule: *a design may assert that something is required, or that something exists, or that something is
connected. It may not assert that a deployable exists when none does.* Every representation below stays on the
right side of that line.

---

## 1. Model Context Protocol (MCP)

**What it is.** A protocol for exposing tools, resources, and prompts to LLM clients. Target layer 1.

**Upstream status.** `meshery-mcp-server` at `fe0bfc5413ce6aafc648b50489c945689543b7a6` contains **zero** Go,
TypeScript, and JavaScript source files. No `go.mod`, no `package.json`, no Kubernetes manifests, no Meshery
Design, no Meshery model, no component, no container image. There is no `mcp` model in the 477-model catalog.

**Representation.**
- `mcp-access-gateway` — `meshery-core` 0.7.2 `GenericNode`, `metadata.isAnnotation: true`.
- `sec-L1-mcp-access` — `meshery-core` `Section` band containing it.
- Annotation-level `edge`/`non-binding`/`reference` edges: `mcp-access-gateway → agent-runtime`,
  `trust-boundary → mcp-access-gateway`.
- One real counterpart: `ingress-ai-platform`, a `kubernetes` `Ingress`, is the *enforcement point* an MCP
  gateway would sit behind. The Ingress is real and deployable; the gateway behind it is not claimed to exist.

**What this asserts and what it does not.** It asserts that layer 1 is architecturally required, that it sits
behind an ingress, and that agents are downstream of it. It does **not** assert that any MCP server is deployed,
that a Meshery model provides one, or that `meshery-mcp-server` is functional.

**The falsification avoided.** Declaring a `Deployment` named `mcp-server` with a plausible image reference. That
would be schema-valid, would appear in the design as real infrastructure, and would fail at `ImagePullBackOff` —
converting a documented gap into a runtime incident.

**What would change it.** `meshery-mcp-server` shipping a container image and a Kubernetes deployment manifest.
At that point add a real `Deployment` + `Service` and repoint the A-6/A-22 edges at them. The annotation node
stays as the architectural record.

---

## 2. Ollama, and local LLM serving generally

**What it is.** A local LLM runtime and server. Would realise `tier-local-hosted` and possibly
`tier-offline-cached`.

**Upstream status.** Absent. No model, directory, or component matching `ollama` exists anywhere under `models/`.

**Representation.** The fallback ladder is expressed entirely as annotation nodes:
`tier-cloud-managed`, `tier-local-hosted`, `tier-offline-cached` — all `meshery-core` `GenericNode`,
`isAnnotation: true`. Their policy is real and lives in `cm-model-router`, a `ConfigMap` holding tier preference
order, fallback triggers, and cost/privacy ceilings.

**What this asserts and what it does not.** It asserts that a three-tier ladder exists as policy and that the
policy is configurable. It does **not** assert that any specific local inference runtime is installed. Note that
the `meshery-dev-icons` model contains a file named `tempo.json`, which is an **icon**, not a component — and
similarly no icon named `ollama` would constitute a component.

**What would change it.** A Meshery model for Ollama, or for a generic local inference server. The realistic
alternatives were also rejected: `kserve` 1.0.2 `InferenceService` and `kubedl` v0.5.0 `Inference` are real but
assume KubeFlow/operator CRDs that this design has no reason to install (see ADR-002's reasoning applied to
layer 3/4, and `ARCHITECTURAL_DECISIONS.md` ADR-002's consequence list). A generic `Deployment` would be the
ADR-002 fabrication.

---

## 3. Tempo

**What it is.** Grafana Tempo, a distributed tracing backend. Would be the trace store paired with the
OpenTelemetry Collector.

**Upstream status.** **No Tempo model exists.** The only file matching the name is
`models/meshery-dev-icons/0.7.2/v1.0.0/components/tempo.json`, which is an **icon** in a decorative icon model —
not a deployable component. This is the single most likely false positive in the whole catalog and the reason
icon models are called out in `RECONNAISSANCE.md` §K item 9.

**Representation.** Traces are ingested by `otel-collector` (real, `sumologic` 4.18.0) and forwarded. The design
asserts an ingest path, not a trace store. `prometheus` handles metrics; trace storage is unspecified.

**What this asserts and what it does not.** It asserts that traces are collected and exported. It does **not**
assert that traces are stored, retained, or queryable.

**Alternatives rejected.** `loki` 18.13.7 (2 components) and `jaegertracing` / `jaeger-operator` jaeger-3.4.1
(1 component each) are real. Neither was added: layer 10 names OpenTelemetry and Prometheus, not log or trace
backends, and adding a tracing backend would be adding technology for its own sake. If a trace backend is later
required, `jaegertracing` is the smallest real option.

---

## 4. Gateway API

**What it is.** The successor to `Ingress` — `Gateway`, `GatewayClass`, `HTTPRoute`, `GRPCRoute`. Would be the
north-south routing layer.

**Upstream status.** All four kinds are **absent** from `models/kubernetes/v1.37.1/v1.0.0/components/`, which
holds 158 components. Verified by direct directory listing and by exhaustive name search. Near neighbours exist
but are not substitutes: `traefik-mesh` 4.1.1 `HTTPRouteGroup`, `kong-mesh` `MeshHTTPRoute` — both mesh-scoped
project CRDs.

**Representation.** `ingress-ai-platform` — `kubernetes` `Ingress`, `networking.k8s.io/v1`, with a real blueprint
`edge-non-binding-network-jccsr.json` connecting it to `svc-meshery-control`.

**What this asserts and what it does not.** It asserts a real, deployable ingress exists. It does not claim
Gateway API semantics, L7 routing, or mesh-derived routing.

**The falsification avoided.** Declaring `kind: Gateway` because it is the "right" modern abstraction. The
component does not exist in the model; a design naming it would fail resolution, and on the import path
`NewPatternFileFromK8sManifest(..., ignoreErrors=true, registry)` would **silently drop it** — the failure would
be an invisible missing component, not an error.

**What would change it.** Contributing `Gateway`/`GatewayClass`/`HTTPRoute` components to the upstream
`kubernetes` model. That is an upstream contribution, not a design decision. See ADR-012.

---

## 5. Grafana

**What it is.** The conventional visualisation layer for Prometheus metrics.

**Upstream status.** No `grafana` model exists. Precisely:
- `grafana-ui-server` 2022.6.14 → only `GrafanaDashboard`. Dashboards, not a server.
- `fmtok8s-conference-chart` 0.1.4 → a real `Grafana` component, but inside an unrelated community
  conference-sponsorship chart.
- `kubedb-grafana-dashboards`, `kube-grafana-dashboards`, `stash-grafana-dashboards` → dashboards only.
- `grafana-agent-operator`, `dapr`, `dnation-kubernetes-monitoring-stack` → `GrafanaAgent` / `GrafanaDashboard`,
  not a Grafana server.

**Representation.** None. The telemetry chain terminates at `prometheus`, `alertmanager`, and
`promrule-platform-slo`. `alertmanager` provides the human-facing surface for this design.

**What this asserts and what it does not.** It asserts that metrics are collected, stored, evaluated, and alerted
on — all real. It does **not** assert any dashboard or visualisation capability.

**The falsification avoided.** Depending on `fmtok8s-conference-chart` for its `Grafana` component. It would be
technically real, and it would silently couple the platform's observability to a third-party chart's version
cadence. See ADR-007 for the full rejection.

**What would change it.** A `grafana` model published upstream, or Grafana deployed outside Meshery's model
system. Neither is a design-time change.

---

## 6. AI agent runtime

**What it is.** The execution plane for agent loops. Target layer 2.

**Upstream status.** No model describes an agent, an agent runtime, an orchestrator, or a ReAct/planning loop. The
adjacent models are all something else: `kserve` `InferenceService` (model serving), `kubedl` `Inference`
(KubeFlow serving), `training-operator` jobs (training), `dapr` (application runtime primitives).

**Representation.**
- `agent-runtime` — `meshery-core` `GenericNode`, `isAnnotation: true`.
- `agent-tool-bridge` — `meshery-core` `GenericNode`, `isAnnotation: true`, representing the agent's tool egress
  as a separate concern so network policy can restrict it independently of agent compute.
- **Real configuration:** `cm-agent-runtime`, a `kubernetes` `ConfigMap` in `ns-ai-runtime`, holding timeouts,
  concurrency limits, and grounding requirements. This is the part that makes the annotation substantive.

**What this asserts and what it does not.** It asserts that an agent runtime is architecturally required, that it
has a defined configuration contract, and that it mediates model access. It does **not** assert that any agent
process runs.

**What would change it.** An implementation of the agent runtime, after which `cm-agent-runtime` becomes its
input and a `Deployment` + `Service` becomes its real counterpart.

---

## 7. Model router

**What it is.** The component that selects which model tier serves a request. Target layer 3. It is the design's
central safety property — no caller reaches a model tier without passing through it.

**Upstream status.** No model describes a router, a policy engine for model selection, or a gateway for LLM
traffic. (Note: `dask-gateway`, `dapr`, `gotway`, `kong`, and `traefik-mesh` are all *HTTP* gateways, not model
routers; using one would be a category error.)

**Representation.**
- `model-router` — `meshery-core` `GenericNode`, `isAnnotation: true`.
- **Real configuration:** `cm-model-router`, a `kubernetes` `ConfigMap` holding the full fallback policy — tier
  preference order, fallback triggers, cost ceilings, privacy ceilings. The policy is real; the router is not
  claimed to exist.
- Annotation edges: `model-router` → each of the three tier nodes, → `model-registry`, → `grounding-validator`;
  ← `agent-runtime`, ← `degradation-controller`.

**What this asserts and what it does not.** It asserts that routing is a mandatory mediation point and that its
policy is configurable and reviewable. It does not assert that a router process exists.

**The falsification avoided.** Using `kong` 3.4.1 or `nginx-ingress` 2.7.3 and labelling the result "model
router". Both are real HTTP ingress components. Neither performs model selection, and presenting one as a model
router would misrepresent a working component as a missing one — a more dangerous error than an honest gap.

---

## 8. Cloud / local / offline model endpoints

**What it is.** The three destinations the router selects between. Target layer 4.

**Upstream status.** No model describes a hosted model API or an offline inference cache. `kserve` and `kubedl`
describe *self-hosted* serving; neither is an external provider, and neither is a cache.

**Representation.** Three `meshery-core` `GenericNode` annotations: `tier-cloud-managed`, `tier-local-hosted`,
`tier-offline-cached`. Tier behaviour is specified in `cm-model-router`. `tier-offline-cached` additionally has an
annotation edge to `context-store`, because a cache tier has no external source — this is what makes layer 12
coherent: the floor of the ladder is backed by durable state.

**What this asserts and what it does not.** It asserts a three-tier fallback policy with a defined order and
defined triggers. It does not assert that any endpoint exists at any tier.

**What would change it.** Real endpoints, plus a real router. Until then the ladder is a specification, and the
design is clear about that.

---

## 9. Context store and grounding substrate

**What it is.** Durable, retrievable context that grounds agent answers. Target layer 5. In practice this is
usually a vector store, a document store, or a hybrid.

**Upstream status.** No vector-database or context-store model exists. The nearest real components are generic
`StatefulSet` and `PersistentVolumeClaim` in the `kubernetes` model — which is exactly why the design uses them.

**Representation.**
- `context-store` — `meshery-core` `GenericNode`, `isAnnotation: true` (the logical concept).
- `sts-postgres` + `pvc-postgres` + `svc-postgres` — real `kubernetes` components (the durable substrate).
- Annotation-level cross-class edge A-4: `context-store → sts-postgres`, making the correspondence explicit.

**What this asserts and what it does not.** It asserts that grounding is backed by durable, queryable state in
`ns-ai-state`. It does **not** assert vector similarity search, an embedding index, or any specific retrieval
algorithm. Those are implementation choices for a future design.

**What would change it.** A vector-database model (for example Milvus, Qdrant, or pgvector via a CRD) would let
the context store become a native component.

---

## 10. Model registry

**What it is.** The authoritative catalogue of model identities the platform may use, with grounding metadata.
Target layer 5.

**Upstream status.** `meshery-core` ships a `connections/` directory containing `ArtifactHubConnection`,
`GitHubConnection`, and `GrafanaConnection` — these are *Meshery's* connections to its own registries, not a
model registry for LLMs. There is no component that models a registry of AI models.

**Representation.**
- `model-registry` — `meshery-core` `GenericNode`, `isAnnotation: true`.
- `registry-credential` — `meshery-core` `Credential`, a **real** `meshery-core` component purpose-built for
  "this needs a secret". This is the correct annotation primitive, and it is a real model component rather than a
  `GenericNode` stand-in.
- `sec-registry-creds` — real `kubernetes` `Secret`, the concrete counterpart.
- Edges: `model-registry → registry-credential` (H10), `model-registry → sec-registry-creds` (A-5),
  `registry-credential → sec-registry-creds` (H11).

**What this asserts and what it does not.** It asserts that model access is credential-gated and that an
authoritative registry governs selection. It does not assert that a registry service exists.

**Note on `Credential`.** Because it is a real `meshery-core` component, this is one of the few places where the
concept *is* natively representable — just not as a running service.

---

## 11. Request-time policy and grounding validation

**What it is.** The layer-7 choke point where a request is checked before any model tier is contacted. Target
layer 7.

**Upstream status.** No model expresses request-time policy. The closest real constructs are all
*admission*-time, not request-time: `ValidatingAdmissionPolicy` (`kubernetes` v1.37.1), and the
`open policy agent (opa)`, `gatekeeper`, and `kyverno` models — all of which are admission-policy engines, none of
which inspect live model requests.

**Representation.**
- **Real enforcement:** `vap-required-labels` + `vapb-ai-runtime` — native `ValidatingAdmissionPolicy`, no
  operator, evaluated in-process by the API server. This genuinely enforces that runtime and state workloads carry
  required labels and grounding metadata at admission time. See ADR-006.
- **Real containment:** `quota-ai-runtime`, `limits-ai-runtime`.
- **Conceptual remainder:** `policy-boundary` and `grounding-validator` — `meshery-core` `GenericNode`,
  `isAnnotation: true`, with annotation edge A-7 connecting `policy-boundary` to `vap-required-labels` so the
  partial enforcement is not overstated.

**What this asserts and what it does not.** It asserts that admission-time labelling is enforced for real, and
that request-time grounding validation is a required architectural position that is **not yet implemented**. The
distinction between these two is the point of having both the annotation and the real policy.

**What would change it.** An admission policy can never express this. It needs either a service-mesh or
sidecar-based authorisation layer (excluded by ADR-003) or a real policy service. Both are larger than this design.

---

## 12. Degradation behaviour

**What it is.** What the platform does when tiers 1 and 2 are unavailable. Target layer 12.

**Upstream status.** No model expresses runtime behaviour under failure. Kubernetes primitives can keep processes
alive but cannot decide that a request should be answered from cache.

**Representation.**
- `degradation-controller` — `meshery-core` `GenericNode`, `isAnnotation: true`.
- **Real detection:** `promrule-platform-slo` — a real `kube-prometheus-stack` `PrometheusRule` supplying the
  measurable criteria for "this tier is degraded". Annotation edge A-8 connects the controller to the rules.
- **Real protection:** `pdb-sts-redis`, `pdb-sts-postgres`, `pc-ai-critical`, `quota-ai-runtime`.

**What this asserts and what it does not.** It asserts that degradation is *detectable* (real: the SLO rules) and
*protected against self-inflicted outage* (real: PDBs and priority). It does **not** assert that any automated
fallback action is taken.

---

## 13. Relationship gaps (not concepts, but same failure mode)

Five participant pairings this design needs have no upstream blueprint — four are hand-authored with the nearest
real triple, and the fifth is deliberately left un-authored. They are flagged, rather than either dropped or
invented. All four gaps were confirmed by exhaustive search of every `relationships/*.json` in all 477 models.

| Gap | Catalog has | Design needs | Handling |
|---|---|---|---|
| Service → workload | `Service → Deployment` (`edge-non-binding-network-duixv.json`) | `Service → StatefulSet` | Hand-authored, C3–C4. Triple copied from the Deployment variant. Zero catalog matches for the pair. |
| Secret → workload | `Secret → Pod`, `Secret → Deployment` | `Secret → StatefulSet` | Hand-authored, F1–F2. Zero catalog matches for the pair. |
| Prometheus → Alertmanager | `Alertmanager → AlertmanagerConfig` | `Prometheus → Alertmanager` | Hand-authored, F3. Zero catalog matches for the pair. |
| OTel → Prometheus | `sumologic` ships **no** `relationships/` directory at all | `OpenTelemetryCollector → Prometheus` | Hand-authored, A-9. |
| NetworkPolicy → workload | `NetworkPolicy → Pod`, `Pod → Pod` (both firewall blueprints) | No `Pod` components exist to target | **No edge authored.** Containment recorded by the `sec-L11-security` band instead. Recorded in `RELATIONSHIP_MATRIX.md` §6.1. |

A sixth, related gap: no blueprint pairs `Section` with anything, so the 27 containment edges in
`RELATIONSHIP_MATRIX.md` §7 and §10 are provenance C — analogy with the real `Container → Deployment` alias
blueprint, not a direct match.

**The governing principle for all five.** An absent blueprint is a gap in the model catalog, not a licence to
invent a `kind`/`type`/`subType`. Every hand-authored edge reuses a triple that genuinely exists upstream, and
every one is disclosed. In the NetworkPolicy case the correct action was to author *no* edge rather than
fabricate `Pod` components to satisfy one.

---

## 14. Summary

| Concept | Classification | Design representation | Fabricated anything? |
|---|---|---|---|
| MCP access layer | `NOT_FOUND` (no model, no image) | `GenericNode` + real `Ingress` counterpart | No |
| Ollama / local serving | `NOT_FOUND` | Tier annotation + real `ConfigMap` policy | No |
| Tempo | `NOT_FOUND` (icon only) | OTel ingest asserted; no trace store | No |
| Gateway API | `NOT_FOUND` (absent from `kubernetes` model) | Real `Ingress` | No |
| Grafana | `NOT_FOUND` (no `grafana` model) | Absent; chain ends at Alertmanager | No |
| AI agent runtime | `NOT_FOUND` | `GenericNode` ×2 + real `ConfigMap` | No |
| Model router | `NOT_FOUND` | `GenericNode` + real `ConfigMap` policy | No |
| Model endpoints (3 tiers) | `NOT_FOUND` | `GenericNode` ×3 | No |
| Context store | `NOT_FOUND` | `GenericNode` + real `StatefulSet` | No |
| Model registry | `NOT_FOUND` | `GenericNode` + real `Credential` + real `Secret` | No |
| Request-time policy | `NOT_FOUND` (admission ≠ request) | Annotation + real `ValidatingAdmissionPolicy` | No |
| Degradation behaviour | `NOT_FOUND` | Annotation + real `PrometheusRule` | No |
| 5 relationship pairings | Catalog gap | Hand-authored with disclosed real triples | No |

**Nothing in this design asserts a Meshery model, component, or deployable workload that does not exist.** Where
a concept is real, it is a real component. Where it is not, it is an annotation with `isAnnotation: true` and,
where meaningful, a real configuration artifact that makes the requirement reviewable.
