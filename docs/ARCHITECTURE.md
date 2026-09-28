# Architecture — AI-Native Platform

This document presents the architecture of the current `ai-native-platform` Meshery design. The authoritative detailed specification is `spec/FINAL_ARCHITECTURE.md`.

## 1. Authoring contract

| Property | Value | Source |
|---|---|---|
| Design `schemaVersion` | `designs.meshery.io/v1beta3` | `constructs/v1beta3/design/design.yaml` |
| Component `schemaVersion` | `components.meshery.io/v1beta2` | v1beta3 design `$ref`s `v1beta2/component`; default in `component.yaml` |
| Relationship `schemaVersion` | `relationships.meshery.io/v1beta2` | v1beta3 design `$ref`s `v1beta2/relationship` |
| Top-level keys allowed | `id`, `name`, `schemaVersion`, `version`, `metadata`, `components`, `preferences`, `relationships` | `additionalProperties: false` |
| Per-component required keys | `id`, `displayName`, `description`, `schemaVersion`, `format`, `version`, `configuration`, `metadata`, `model`, `modelReference`, `component` (11) | `v1beta2/component/component.yaml`, `additionalProperties: false` |
| Component `metadata` required sub-keys | `genealogy`, `isAnnotation`, `isNamespaced`, `published`, `instanceDetails`, `configurationUISchema` | same file |
| Per-relationship required keys | `id`, `schemaVersion`, `version`, `model`, `kind`, `type`, `subType` (7) | `v1beta2/relationship/relationship.yaml`, `additionalProperties: false` |
| Relationship `kind` enum | `hierarchical`, `edge`, `sibling` | same file |
| Relationship `status` enum | `enabled`, `ignored`, `deleted`, `approved`, `pending` | same file |
| `ModelReference` required keys | `id`, `name`, `version`, `displayName`, `model`, `registrant` | `v1beta1/model/api.yml` |

Three closed objects (`Design`, `ComponentDefinition`, `RelationshipDefinition`) means the design has **no room
for scaffolding keys**. There is no `layers` key, no `services` key. Grouping is expressed with components and
relationships only.

---

## 2. The organising principle

The design is split into two kinds of component, and the split is the whole point:

| Class | Meaning | `metadata.isAnnotation` | Deployable |
|---|---|---|---|
| **Native** | A capability that exists as a real Meshery model component, backed by a real upstream API or CRD | `false` | Yes |
| **Annotation** | An architectural concept that has no native model, expressed with `meshery-core` | `true` | No — descriptive only |

Every annotation in this design states an architectural intent that a human or a future implementation will
satisfy. **No annotation pretends to be infrastructure.** Equally, no native component is included that exists
only to look impressive.

This maps directly onto the upstream signal: of the 180 non-empty catalog designs, 418 components carry
`isAnnotation: true` and 388 come from `meshery-core`. Annotation use is normal practice, not a workaround.

---

## 3. Layer map

Twelve target layers. Each is marked with how it is realised.

| # | Layer | Realisation | Components |
|---|---|---|---|
| 1 | MCP access layer | **Annotation** — no MCP model exists | `mcp-access-gateway` |
| 2 | AI agent runtime | **Annotation** — no agent model exists | `agent-runtime`, `agent-tool-bridge` |
| 3 | Model router | **Annotation** — no router model exists | `model-router` |
| 4 | Cloud/local/offline fallback | **Annotation** — no LLM-serving model is justified | `tier-cloud-managed`, `tier-local-hosted`, `tier-offline-cached` |
| 5 | Context and registry grounding | **Annotation + one real artifact** | `context-store`, `model-registry`, `registry-credential`, `sec-registry-creds`, `cm-model-router` |
| 6 | Meshery design/control layer | **Real** (native CRDs) + annotation for the server | `meshsync`, `broker`, `deploy-meshery-control`, `svc-meshery-control`, `ingress-ai-platform`, `meshery-control-plane` |
| 7 | Validation/policy boundary | **Real** — native admission control, no operator | `vap-required-labels`, `vapb-ai-runtime`, `quota-ai-runtime`, `limits-ai-runtime`, `policy-boundary`, `grounding-validator` |
| 8 | Kubernetes infrastructure | **Real** | 4 `Namespace`, `Deployment`, `Service`, `Ingress`, 2 `ConfigMap`, 3 `Secret` |
| 9 | Redis/PostgreSQL state | **Real** — `StatefulSet`, not operators | `sts-redis`, `sts-postgres`, `svc-redis`, `svc-postgres`, `pvc-redis`, `pvc-postgres`, `sec-state-creds` |
| 10 | OpenTelemetry/Prometheus observability | **Real** | `otel-collector`, `prometheus`, `sm-platform`, `alertmanager`, `promrule-platform-slo` |
| 11 | Security boundaries | **Real** | `netpol-default-deny`, `netpol-ai-allowlist`, `sa-ai-control`, `sa-ai-state`, `role-ai-control`, `role-ai-state`, `rb-ai-control`, `rb-ai-state`, `trust-boundary` |
| 12 | Resilience / graceful degradation | **Real + annotation** | `pdb-sts-redis`, `pdb-sts-postgres`, `pc-ai-critical`, `degradation-controller` |

**Counts:** 40 native components, 26 annotation components, 66 total. See `COMPONENT_INVENTORY.md` for the
authoritative per-component list.

The AI-native core (layers 1–5) is **entirely annotation**. That is the honest outcome of the reconnaissance:
`meshery-mcp-server` has zero source files, and no Meshery model describes an agent, a router, an LLM endpoint,
or a context store. Fabricating native components for them would violate the design's own evidence standard.
The promotion path for each is recorded in `UNSUPPORTED_CONCEPTS.md`.

---

## 4. The five-tier request path

The central architectural claim, expressed as an annotation-level chain:

```
mcp-access-gateway → agent-runtime → model-router → tier-cloud-managed
                                              ↓   (policy, cost, privacy)
                                        tier-local-hosted
                                              ↓   (capacity, egress)
                                        tier-offline-cached
```

- `agent-runtime` reads assembled context from `context-store` and permitted model identities from
  `model-registry`, which is bound to `registry-credential`.
- Before any tier is selected, `grounding-validator` inside `policy-boundary` checks the request. This is the
  single choke point where a design-time policy becomes a runtime gate.
- `degradation-controller` sits above `model-router` and defines what happens when tiers 1 and 2 are unavailable.
- Every edge in this chain is `edge/non-binding/reference` with `metadata.isAnnotation: true`. None of it is
  enforced by Kubernetes; it is a specification for an implementation that does not yet exist.

The only real enforcement in the entire design is `vap-required-labels` + `vapb-ai-runtime`, which requires
labelled workloads. See ADR-006.

---

## 5. Native infrastructure topology

Four namespaces, each a separate trust and quota domain:

| Namespace | Holds | Why separate |
|---|---|---|
| `ns-ai-control` | `meshsync`, `broker`, `deploy-meshery-control`, `svc-meshery-control`, `ingress-ai-platform`, control `ConfigMap`/`Secret` | Control plane is the highest-value target. Isolating it means a runtime compromise does not reach the control plane's RBAC. |
| `ns-ai-runtime` | `cm-agent-runtime`, `cm-model-router`, `quota-ai-runtime`, `limits-ai-runtime` | Configuration and quota live apart from control and state, so quota changes never touch control RBAC. |
| `ns-ai-state` | `sts-redis`, `sts-postgres`, `svc-redis`, `svc-postgres`, `pvc-redis`, `pvc-postgres`, `sec-state-creds`, state `ServiceAccount`/`Role`/`RoleBinding` | State is the crown jewel. `netpol-default-deny` applies here first. |
| `ns-ai-observability` | `otel-collector`, `prometheus`, `sm-platform`, `alertmanager`, `promrule-platform-slo` | Telemetry must be able to read everything, so it must not be reachable from everything. |

State stores are `StatefulSet` + `Service` + `PersistentVolumeClaim`, not operators. See ADR-004.

---

## 6. Observability path

`otel-collector` (`sumologic` 4.18.0, kind `OpenTelemetryCollector`, `opentelemetry.io/v1alpha1`) is the only real
OpenTelemetry Collector component available upstream — there is no dedicated OTel model. `kube-prometheus-stack`
89.2.2 supplies the Prometheus Operator CRDs.

```
workloads → otel-collector → prometheus
                              ↑ via sm-platform (selects svc-meshery-control, svc-redis, svc-postgres)
                              → alertmanager
                              ← promrule-platform-slo (degradation SLOs)
```

The `otel-collector → prometheus` edge has **no upstream blueprint**; `sumologic` ships no relationship
definitions. It is hand-authored as `edge/non-binding/reference` with `metadata.isAnnotation: true`, because the
OTel-Collector CRD's actual output path is a configuration concern, not something Meshery can verify. The
`prometheus → sm-platform` and `sm-platform → service` edges **do** have real blueprints.

Grafana is deliberately absent. See `UNSUPPORTED_CONCEPTS.md` §5 and ADR-007.

---

## 7. Security model

Three real mechanisms, no policy operator:

1. **Network segmentation** — `netpol-default-deny` (deny-all baseline per namespace) and
   `netpol-ai-allowlist` (explicit east-west permissions). Both are native `kubernetes` components. No Gatekeeper,
   no Cilium, no Calico. See ADR-005.
2. **Workload identity** — `sa-ai-control` and `sa-ai-state` with least-privilege `Role`s bound via
   `RoleBinding`. Both pairings have real blueprints (`Role → ServiceAccount` via
   `edge/binding/permission`; `RoleBinding → Role` via `edge/non-binding/reference`).
3. **Admission control** — `vap-required-labels` with `vapb-ai-runtime`, using Kubernetes' native
   `ValidatingAdmissionPolicy` (GA, no webhook, no operator). Real blueprints exist in both directions.

`trust-boundary` is an annotation that names where the untrusted zone (MCP ingress) meets the trusted zone. It
documents intent; `netpol-ai-allowlist` and the admission policy are what actually enforce.

---

## 8. Resilience and graceful degradation

| Mechanism | Component | Real? |
|---|---|---|
| Voluntary-disruption protection | `pdb-sts-redis`, `pdb-sts-postgres` | Yes, native |
| Scheduling priority | `pc-ai-critical` | Yes, native |
| Resource containment | `quota-ai-runtime`, `limits-ai-runtime` | Yes, native |
| Degradation *policy* | `degradation-controller` | Annotation — behaviour is a design intent |

Degradation tiers are defined by the annotation chain in §4, not by Kubernetes. The real contribution of the
infrastructure layer is that the control plane and the observability path survive independently of the
AI-native layer, because nothing in layers 1–5 has a native component to break.

**Not included:** `HorizontalPodAutoscaler`. It is a confirmed real component, but it needs a scalable workload,
and the only real workloads here are one `Deployment` and two `StatefulSet`s — none of which is a sensible
autoscaling target. Adding it would be decoration. See ADR-008.

---

## 9. What is deliberately excluded

| Excluded | Reason |
|---|---|
| `istio-base` | A service mesh is not required by any of the 12 layers. Adds 15 components and a second networking model for no stated requirement. Prohibited by instruction. |
| `kserve`, `kubedl` | LLM-serving operators. Layers 3–4 are annotations; pulling in a KubeFlow-dependent operator would misstate the design's maturity. |
| `kubevault`, `keycloak-operator` | Secret management and SSO are not required by any of the 12 layers. Kubernetes `Secret` plus `netpol-default-deny` covers the stated security need. |
| `redis-operator`, `pg-operator`, `postgres-with-operator` | Operators for state stores. `StatefulSet` is sufficient and honest. ADR-004. |
| Gateway API (`Gateway`, `GatewayClass`, `HTTPRoute`) | Absent from the `kubernetes` model. `Ingress` is used instead. |
| Grafana | No clean model. ADR-007. |
| Ollama, Tempo | Not present upstream in any form. |
| Loki, Jaeger, cert-manager, `nginx-ingress`, Kong, APISIX, Traefik, Dapr | Available and real, but not required by any of the 12 layers. Adding them would be adding technology for its own sake. |

---

## 10. Composition summary

Grouped exactly as `COMPONENT_INVENTORY.md`, so the two documents reconcile. Each component appears in exactly one
row and the rows sum to the totals.

| Group | Native | Annotation | Total |
|---|---|---|---|
| Namespaces and scoping | 4 | 1 `Environment` | 5 |
| Control plane (layer 6) | 5 | 1 `meshery-control-plane` | 6 |
| Configuration and secrets | 5 | 1 `Credential` | 6 |
| State (layer 9) | 6 | 0 | 6 |
| Observability (layer 10) | 5 | 0 | 5 |
| Security (layer 11) | 8 | 1 `trust-boundary` | 9 |
| Policy (layer 7) | 4 | 2 | 6 |
| Resilience (layer 12) | 3 | 1 `degradation-controller` | 4 |
| AI-native core (layers 1–5) | 0 | 9 | 9 |
| Layer bands and commentary | 0 | 10 | 10 |
| **Total** | **40** | **26** | **66** |

The 10 layer-band and commentary components are 8 `Section` bands and 2 `Comment` nodes. The 26 annotation
components are 1 `Environment`, 14 `GenericNode`, 1 `Credential`, 8 `Section`, and 2 `Comment`.

Layer 8 has no row of its own: its components — the `Deployment`, the three `Service`s, two `ConfigMap`s, three
`Secret`s, and two `StatefulSet`s — are counted in the functional groups above. See `COMPONENT_INVENTORY.md`
Group 9.

---

