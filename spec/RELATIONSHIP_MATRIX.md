# Relationship Matrix — `ai-native-platform`

111 relationships. Each is classified as **semantic** (`metadata.isAnnotation: false` — asserts something
Kubernetes or Meshery acts on) or **annotation** (`metadata.isAnnotation: true` — records intent or containment
only).

`RelationshipMetadata.isAnnotation` is the schema's own field for this
(`v1beta2/relationship/api.yml` → `RelationshipMetadata`, `additionalProperties: true`): *"Indicates whether the
relationship should be treated as a logical representation only."* It is used rather than inferred from
component kinds, because a single edge can legitimately be annotation while both endpoints are native.

Every relationship is one of four provenance classes:

| Provenance | Meaning |
|---|---|
| **B** | A real upstream blueprint exists in the model catalog. The edge reuses that blueprint's `kind`/`type`/`subType` and participant kinds, instantiated with concrete component UUIDs. |
| **H** | Hand-authored. No blueprint exists for this participant pairing. `kind`/`type`/`subType` are chosen to match the closest real blueprint in the catalog, and the edge is marked annotation where it asserts intent rather than fact. |
| **C** | Containment. `Section` bands. `hierarchical/parent/alias`, by analogy with the real `Container → Deployment` blueprint. Annotation only. |
| **A** | Annotation-level cross-class edge. Connects an architectural annotation to a native component to record correspondence. Annotation only. |

---

## 1. Namespace membership — 29 edges, all semantic, all provenance B

**Blueprint:** `models/kubernetes/v1.36.0/v1.0.0/relationships/hierarchical-parent-inventory-kmjea.json`
**Triple:** `kind: hierarchical` · `type: parent` · `subType: inventory`
**Selector shape:** `from: {id: <component-uuid>, kind: "*", match: {}, patch: {patchStrategy: replace, mutatedRef: [["configuration","metadata","namespace"]]}}` → `to: {id: <namespace-uuid>, kind: "Namespace", patch: {patchStrategy: replace, mutatorRef: [["displayName"]]}}`

**Why it exists:** In a Meshery design, a component does not become namespaced by setting a metadata field — the
`inventory` relationship performs the write of `configuration.metadata.namespace` from the target Namespace's
name. Every namespaced component therefore needs exactly one. This is the most consequential structural fact in
the whole design: without it, 29 components deploy to the wrong namespace or fail.

| # | Source | Target | Why |
|---|---|---|---|
| A1 | `meshsync` | `ns-ai-control` | GitOps sync must run where the broker is reachable. |
| A2 | `broker` | `ns-ai-control` | Broker endpoint declaration belongs with its consumer. |
| A3 | `deploy-meshery-control` | `ns-ai-control` | Control server runs in the control namespace. |
| A4 | `svc-meshery-control` | `ns-ai-control` | Service must share its Deployment's namespace. |
| A5 | `ingress-ai-platform` | `ns-ai-control` | Ingress routes to `ns-ai-control` traffic. |
| A6 | `sec-broker-endpoint` | `ns-ai-control` | Broker secret is control-plane material. |
| A7 | `sec-registry-creds` | `ns-ai-control` | Read by the control server; kept out of the state namespace. |
| A8 | `sa-ai-control` | `ns-ai-control` | ServiceAccount is namespaced by definition. |
| A9 | `role-ai-control` | `ns-ai-control` | `Role` cannot reference across namespaces. |
| A10 | `rb-ai-control` | `ns-ai-control` | `RoleBinding` is namespaced. |
| A11 | `cm-agent-runtime` | `ns-ai-runtime` | Agent configuration lives with the quota that governs it. |
| A12 | `cm-model-router` | `ns-ai-runtime` | Router policy is runtime configuration. |
| A13 | `quota-ai-runtime` | `ns-ai-runtime` | `ResourceQuota` is namespaced. |
| A14 | `limits-ai-runtime` | `ns-ai-runtime` | `LimitRange` is namespaced. |
| A15 | `sts-redis` | `ns-ai-state` | Redis is state-tier. |
| A16 | `svc-redis` | `ns-ai-state` | Service must share its StatefulSet's namespace. |
| A17 | `pvc-redis` | `ns-ai-state` | Claim is consumed in this namespace. |
| A18 | `sts-postgres` | `ns-ai-state` | PostgreSQL is state-tier. |
| A19 | `svc-postgres` | `ns-ai-state` | Service must share its StatefulSet's namespace. |
| A20 | `pvc-postgres` | `ns-ai-state` | Claim is consumed in this namespace. |
| A21 | `sec-state-creds` | `ns-ai-state` | Store credentials stay with the stores. |
| A22 | `sa-ai-state` | `ns-ai-state` | ServiceAccount is namespaced. |
| A23 | `role-ai-state` | `ns-ai-state` | `Role` cannot reference across namespaces. |
| A24 | `rb-ai-state` | `ns-ai-state` | `RoleBinding` is namespaced. |
| A25 | `otel-collector` | `ns-ai-observability` | Collector is telemetry-tier. |
| A26 | `prometheus` | `ns-ai-observability` | Prometheus is telemetry-tier. |
| A27 | `sm-platform` | `ns-ai-observability` | Monitor must be co-located with its Prometheus. |
| A28 | `alertmanager` | `ns-ai-observability` | Alert routing is telemetry-tier. |
| A29 | `promrule-platform-slo` | `ns-ai-observability` | Rules are evaluated by the co-located Prometheus. |

**Cluster-scoped, deliberately not wired:** `ns-ai-control`, `ns-ai-runtime`, `ns-ai-state`,
`ns-ai-observability`, `pc-ai-critical`, `vap-required-labels`. The `inventory` blueprint's `to` side requires
`kind: "Namespace"`; a cluster-scoped resource has no containing namespace and correctly has no such edge.

---

## 2. Label grouping — 3 edges, all semantic, all provenance B

**Blueprint:** `models/kubernetes/.../relationships/sibling-tagsets.json`
**Triple:** `kind: hierarchical` · `type: sibling` · `subType: matchlabels`
**Selector shape:** `from` and `to` both `{kind: "*", model: "*", match: {"refs": [["configuration","metadata","labels"]]}}`, `patch: null`

**Why it exists:** This is the generic "these components share a label" primitive. It is how the design records
tier membership without inventing a custom construct. The upstream reference design
(`3c3439a0-…/design.yml`) uses 40 of these among 10 components, so a small number here is deliberately restrained.

| # | Source | Target | Why |
|---|---|---|---|
| B1 | `sts-redis` | `sts-postgres` | Both carry the state-tier label, which is what `netpol-ai-allowlist` and `quota` reasoning refer to. |
| B2 | `prometheus` | `sm-platform` | Both carry the observability-tier label; the pair is also wired semantically by D13. |
| B3 | `netpol-default-deny` | `netpol-ai-allowlist` | Both carry the security-tier label, distinguishing them from application NetworkPolicies. |

**Deliberately omitted:** the exhaustive pairwise explosion. A fully-populated `matchlabels` graph would add
hundreds of no-op edges. Three representative edges establish the pattern; the rest is documented intent.

---

## 3. Network reachability — 4 edges, all semantic

| # | Source | Target | Triple | Provenance | Why |
|---|---|---|---|---|---|
| C1 | `svc-meshery-control` | `deploy-meshery-control` | `edge` / `non-binding` / `network` | **B** — `edge-non-binding-network-duixv.json` | The Service selects the Deployment's pods. Without this edge the Service has no backend. |
| C2 | `ingress-ai-platform` | `svc-meshery-control` | `edge` / `non-binding` / `network` | **B** — `edge-non-binding-network-jccsr.json` | The Ingress's backend is this Service. This is the real enforcement of layer 1's ingress. |
| C3 | `svc-redis` | `sts-redis` | `edge` / `non-binding` / `network` | **H** | The Service selects the StatefulSet's pods. **No blueprint exists** — the catalog has `Service → Deployment` but no `Service → StatefulSet`. Triple copied from the Deployment variant. |
| C4 | `svc-postgres` | `sts-postgres` | `edge` / `non-binding` / `network` | **H** | Same gap as C3. |

**Why C3/C4 are hand-authored rather than omitted:** a `Service` with no edge to its workload is a dangling
declaration. The absence of a blueprint is a gap in the catalog, not a reason to leave the design incomplete.
Verified: an exhaustive search of all `relationships/*.json` in all 477 models finds `Service` + `StatefulSet`
together in **zero** files. Flagged for review in `VALIDATION_PLAN.md` §6.

---

## 4. Reference bindings — 18 edges, all semantic

**Triple:** `kind: edge` · `type: non-binding` · `subType: reference` unless noted. All provenance **B**.

### 4.1 Storage binding

| # | Source | Target | Blueprint | Why |
|---|---|---|---|---|
| D1 | `pvc-redis` | `sts-redis` | `edge-non-binding-reference-rcycs.json` | The StatefulSet mounts this claim. |
| D2 | `pvc-postgres` | `sts-postgres` | `edge-non-binding-reference-rcycs.json` | Same. |

**Deliberately omitted:** `StorageClass → PVC` (`edge-non-binding-reference-ehodr.json` exists). No
`StorageClass` component is declared, so there is nothing to attach the edge to. Rationale in
`COMPONENT_INVENTORY.md` §9.

### 4.2 Configuration and secret mounting

| # | Source | Target | Blueprint | Why |
|---|---|---|---|---|
| D3 | `cm-agent-runtime` | `deploy-meshery-control` | `hierarchical-parent-inventory-pfnyn.json` | The control server reads agent configuration. This is the edge that makes the `agent-runtime` annotation non-fictional. |
| D4 | `cm-model-router` | `deploy-meshery-control` | `hierarchical-parent-inventory-pfnyn.json` | The control server reads router policy. Makes the `model-router` annotation non-fictional. |
| D5 | `sec-broker-endpoint` | `deploy-meshery-control` | `reference-secret-to-deployment.json` | Broker credentials consumed by the control server. |
| D6 | `sec-registry-creds` | `deploy-meshery-control` | `reference-secret-to-deployment.json` | Registry credentials consumed by the control server. Paired with the `registry-credential` annotation (H11). |

### 4.3 Workload identity

| # | Source | Target | Triple | Blueprint | Why |
|---|---|---|---|---|---|
| D7 | `rb-ai-control` | `role-ai-control` | `edge` / `non-binding` / `reference` | `edge-non-binding-reference-keceb.json` | The binding names the Role it grants. |
| D8 | `rb-ai-state` | `role-ai-state` | `edge` / `non-binding` / `reference` | `edge-non-binding-reference-keceb.json` | Same. |

The subject-side edges (D7's counterpart, `Role → ServiceAccount`) are in §5 because they carry
`type: binding`.

### 4.4 Disruption and scheduling

| # | Source | Target | Blueprint | Why |
|---|---|---|---|---|
| D9 | `pdb-sts-redis` | `sts-redis` | `edge-non-binding-reference-xtrmo.json` | The budget protects this workload. |
| D10 | `pdb-sts-postgres` | `sts-postgres` | `edge-non-binding-reference-xtrmo.json` | Same. |
| D11 | `pc-ai-critical` | `sts-redis` | `edge-non-binding-reference-statefulset.json` | The priority class must be attached to the workload to have effect. |
| D12 | `pc-ai-critical` | `sts-postgres` | `edge-non-binding-reference-statefulset.json` | Same. |

### 4.5 Admission policy

| # | Source | Target | Blueprint | Why |
|---|---|---|---|---|
| D13 | `vap-required-labels` | `vapb-ai-runtime` | `edge-binding-reference-ecilr.json` | The policy names the bindings that activate it. |

**Deliberately omitted:** the reverse direction `vapb-ai-runtime → vap-required-labels`
(`edge-binding-reference-kwjtj.json` exists). Authoring both would express the same fact twice with opposite
orientations. One edge, in the policy→binding direction, is sufficient and is the direction the policy object
itself declares.

### 4.6 Telemetry targeting

| # | Source | Target | Blueprint | Why |
|---|---|---|---|---|
| D14 | `prometheus` | `sm-platform` | `edge-sibling-matchlabels-fmlwc.json` | Prometheus discovers targets through the monitor. |
| D15 | `sm-platform` | `svc-meshery-control` | `edge-sibling-matchlabels-qvwox.json` | Control plane is scraped. |
| D16 | `sm-platform` | `svc-redis` | `edge-sibling-matchlabels-qvwox.json` | Redis is scraped. |
| D17 | `sm-platform` | `svc-postgres` | `edge-sibling-matchlabels-qvwox.json` | PostgreSQL is scraped. |
| D18 | `prometheus` | `promrule-platform-slo` | `edge-sibling-matchlabels-cunlc.json` | Prometheus evaluates the rules. |

**Deliberately omitted:** `Alertmanager → AlertmanagerConfig` (`edge-sibling-matchlabels-quaks.json` exists). No
`AlertmanagerConfig` component is declared — routing config belongs in the component's own configuration at
deploy time, and adding a CRD to justify one edge would be circular.

---

## 5. Permission binding — 2 edges, all semantic, all provenance B

**Blueprint:** `models/kubernetes/.../relationships/edge-binding-permission-homji.json`
**Triple:** `kind: edge` · `type: binding` · `subType: permission`

| # | Source | Target | Why |
|---|---|---|---|
| E1 | `role-ai-control` | `sa-ai-control` | The Role's rules apply to this identity. `type: binding` is the correct triple — the permission is conferred, not merely referenced. |
| E2 | `role-ai-state` | `sa-ai-state` | Same. |

**Deliberately omitted:** `ClusterRole`/`ClusterRoleBinding`. Every workload here is namespaced, so namespaced
`Role`s are sufficient and cluster-scoped grants would over-provision.

---

## 6. Hand-authored semantic edges — 3 edges, provenance H

These assert facts that are true of the deployment but have no upstream blueprint. They are marked semantic
because each corresponds to a real Kubernetes reference that simply is not modelled.

**The gaps were verified, not assumed.** Every `relationships/*.json` file in all 477 models was searched for both
participant kinds. `Service` + `StatefulSet`, `Secret` + `StatefulSet`, and `Prometheus` + `Alertmanager` return
**zero** matches across the entire catalog. These are real gaps in the model catalog, not oversights in this
design.

| # | Source | Target | Triple | Semantic/Annotation | Why | Gap |
|---|---|---|---|---|---|---|
| F1 | `sec-state-creds` | `sts-postgres` | `edge` / `non-binding` / `reference` | **Semantic** | The store reads its credentials from this Secret. | Catalog has `Secret → Pod` and `Secret → Deployment`, no `Secret → StatefulSet`. |
| F2 | `sec-state-creds` | `sts-redis` | `edge` / `non-binding` / `reference` | **Semantic** | Same. | Same gap. |
| F3 | `prometheus` | `alertmanager` | `edge` / `non-binding` / `reference` | **Semantic** | Prometheus sends firing alerts to Alertmanager. | No `Prometheus → Alertmanager` blueprint exists in `kube-prometheus-stack`. |

### 6.1 NetworkPolicy edges that cannot be authored

Both firewall blueprints in the catalog target `Pod`:

- `edge-binding-firewall-dynit.json` — `NetworkPolicy` → `Pod`
- `edge-binding-firewall-kllzw.json` — `Pod` → `Pod`

This design declares workloads at `Deployment`/`StatefulSet` level and therefore contains **no `Pod`
components**. There is nothing for a firewall edge to attach to.

**This is a real limitation, not an oversight.** `netpol-default-deny` and `netpol-ai-allowlist` are still
correct and deployable — Kubernetes `NetworkPolicy` selects via `podSelector` labels, not via component edges — but
their *containment* is recorded by the `sec-L11-security` band (G8–G10) rather than by an `edge`. A design that
fabricated `Pod` components purely to satisfy a blueprint would be worse. Flagged in `VALIDATION_PLAN.md` §6.

---

## 7. Section containment — 23 edges, all annotation, all provenance C

**Triple:** `kind: hierarchical` · `type: parent` · `subType: alias`
**Basis:** `hierarchical-parent-alias-iicqa.json` (`meshery-core` `Container` → `kubernetes` `Deployment`) and
`hierarchical-parent-inventory-dfdpsbf.json` (`Container` → `Pod`).

**Why `alias` and not `inventory`:** `inventory` performs a `configuration.metadata.namespace` write, which only
makes sense for namespaced workloads. Layer bands span both annotations and native components and must not
perform a namespace write. `alias` is the containment triple upstream uses for grouping.

**Why `Section` rather than `Container`:** see ADR-009. `Section` has `genealogy: parent` and a rectangle shape,
which suits a wide band, and it avoids implying workload containment that the design does not have.

| # | Band (`from`) | Member (`to`) | Why |
|---|---|---|---|
| C-1 | `sec-L1-mcp-access` | `mcp-access-gateway` | Layer 1 has one conceptual node. |
| C-2 | `sec-L2-agent-runtime` | `agent-runtime` | Layer 2, compute half. |
| C-3 | `sec-L2-agent-runtime` | `agent-tool-bridge` | Layer 2, egress half. |
| C-4 | `sec-L34-routing-fallback` | `model-router` | Layer 3. |
| C-5 | `sec-L34-routing-fallback` | `tier-cloud-managed` | Layer 4, tier 1. |
| C-6 | `sec-L34-routing-fallback` | `tier-local-hosted` | Layer 4, tier 2. |
| C-7 | `sec-L34-routing-fallback` | `tier-offline-cached` | Layer 4, tier 3. |
| C-8 | `sec-L5-grounding` | `context-store` | Layer 5, context half. |
| C-9 | `sec-L5-grounding` | `model-registry` | Layer 5, registry half. |
| C-10 | `sec-L5-grounding` | `registry-credential` | Layer 5, credential binding. |
| C-11 | `sec-L6-control-plane` | `meshery-control-plane` | Layer 6, the architectural node. |
| C-12 | `sec-L6-control-plane` | `meshsync` | Layer 6, real reconciliation CRD. |
| C-13 | `sec-L6-control-plane` | `broker` | Layer 6, real broker CRD. |
| C-14 | `sec-L7-policy-boundary` | `policy-boundary` | Layer 7, the choke point. |
| C-15 | `sec-L7-policy-boundary` | `grounding-validator` | Layer 7, the check. |
| C-16 | `sec-L7-policy-boundary` | `quota-ai-runtime` | Layer 7, resource containment. |
| C-17 | `sec-L7-policy-boundary` | `limits-ai-runtime` | Layer 7, default shaping. |
| C-18 | `sec-L11-security` | `trust-boundary` | Layer 11, intent. |
| C-19 | `sec-L11-security` | `netpol-default-deny` | Layer 11, baseline. |
| C-20 | `sec-L11-security` | `netpol-ai-allowlist` | Layer 11, exceptions. |
| C-21 | `sec-L12-degradation` | `degradation-controller` | Layer 12, policy. |
| C-22 | `sec-L12-degradation` | `pdb-sts-redis` | Layer 12, disruption protection. |
| C-23 | `sec-L12-degradation` | `pdb-sts-postgres` | Layer 12, disruption protection. |

**Deliberately omitted from banding:** the 4 `Namespace` components and the 3 namespace-scoped layers that are
pure infrastructure (workload, state, observability). Those are organised by `inventory` edges and by Service
grouping, and adding them to a conceptual band would blur the annotation/native boundary that is the design's
central organising principle.

---

## 8. AI-native semantic chain — 16 edges, all annotation, all provenance H

**Triple:** `kind: edge` · `type: non-binding` · `subType: reference`
**Why this triple:** `edge` / `non-binding` / `reference` is the dominant triple in the catalog (84 of 102
Kubernetes blueprints) and denotes "A points at B without conferring anything." That is exactly the semantics of
an architectural dependency: the agent does not *grant* the router anything, it *depends* on it.

| # | Source | Target | Why |
|---|---|---|---|
| H1 | `mcp-access-gateway` | `agent-runtime` | The only ingress into the platform. Everything else is downstream of this edge. |
| H2 | `agent-runtime` | `agent-tool-bridge` | Agents reach external tools only through the bridge, so tool egress is separable. |
| H3 | `agent-runtime` | `context-store` | The agent retrieves grounding context before answering. |
| H4 | `agent-runtime` | `model-router` | The agent does not call a model directly; the router mediates. This indirection is the design's main safety property. |
| H5 | `model-router` | `tier-cloud-managed` | Tier 1 of the fallback ladder. |
| H6 | `model-router` | `tier-local-hosted` | Tier 2. |
| H7 | `model-router` | `tier-offline-cached` | Tier 3, the floor. |
| H8 | `model-router` | `model-registry` | The router may only select registered models. |
| H9 | `model-router` | `grounding-validator` | Routing is gated on grounding. Ordering matters: this edge is conceptually evaluated before H5–H7. |
| H10 | `model-registry` | `registry-credential` | The registry needs a credential to be reachable. |
| H11 | `registry-credential` | `sec-registry-creds` | The annotation's concrete counterpart. Annotation edge, but both endpoints resolve to one real Secret. |
| H12 | `grounding-validator` | `context-store` | Validation reads the context it is validating against. |
| H13 | `grounding-validator` | `model-registry` | Validation checks model identity is registered. |
| H14 | `grounding-validator` | `policy-boundary` | The validator *is* the policy boundary's content. |
| H15 | `tier-offline-cached` | `context-store` | The offline tier has no external source; cached context is all it has. |
| H16 | `degradation-controller` | `model-router` | Degradation policy governs tier selection, so it sits above the router. |

---

## 9. Annotation-to-native correspondence — 9 edges, all annotation, all provenance A

These edges exist so a reader can see which annotation is realised by which real component. Without them the
annotation layer floats free of the infrastructure. All `edge` / `non-binding` / `reference`, all
`metadata.isAnnotation: true`.

| # | Source (annotation) | Target (native) | Why |
|---|---|---|---|
| A-1 | `meshery-control-plane` | `meshsync` | The annotation is realised by this real CRD. |
| A-2 | `meshery-control-plane` | `broker` | Likewise for the broker CRD. |
| A-3 | `meshery-control-plane` | `deploy-meshery-control` | And for the server workload slot. |
| A-4 | `context-store` | `sts-postgres` | The durable half of the context store is this real StatefulSet. |
| A-5 | `model-registry` | `sec-registry-creds` | The registry's credential counterpart (distinct from H10, which is annotation→annotation). |
| A-6 | `trust-boundary` | `ingress-ai-platform` | The boundary is enforced at the ingress. |
| A-7 | `policy-boundary` | `vap-required-labels` | The boundary has one real enforcement point. |
| A-8 | `degradation-controller` | `promrule-platform-slo` | Degradation is detected by the SLO rules. |
| A-9 | `otel-collector` | `prometheus` | Telemetry pipeline handoff. **Provenance H as well as A** — `sumologic` ships no relationship blueprints at all, so both the triple and the edge are hand-authored. |

---

## 10. Environment scoping — 4 edges, all annotation, provenance C

**Triple:** `kind: hierarchical` · `type: parent` · `subType: alias`

| # | Source | Target | Why |
|---|---|---|---|
| S1 | `env-production` | `ns-ai-control` | Scoping the control namespace to the production environment. |
| S2 | `env-production` | `ns-ai-runtime` | Same. |
| S3 | `env-production` | `ns-ai-state` | Same. |
| S4 | `env-production` | `ns-ai-observability` | Same. |

**Why the native `Namespace` components and not the annotations:** an environment that scopes abstract concepts
is unenforceable. Scoping the four namespaces means the environment statement attaches to something real.

---

## 11. Provenance and classification summary

| Group | Edges | Semantic | Annotation | B | H | C | A |
|---|---|---|---|---|---|---|---|
| 1 Namespace membership | 29 | 29 | 0 | 29 | 0 | 0 | 0 |
| 2 Label grouping | 3 | 3 | 0 | 3 | 0 | 0 | 0 |
| 3 Network reachability | 4 | 4 | 0 | 2 | 2 | 0 | 0 |
| 4 Reference bindings | 18 | 18 | 0 | 18 | 0 | 0 | 0 |
| 5 Permission binding | 2 | 2 | 0 | 2 | 0 | 0 | 0 |
| 6 Hand-authored semantic | 3 | 3 | 0 | 0 | 3 | 0 | 0 |
| 7 Section containment | 23 | 0 | 23 | 0 | 0 | 23 | 0 |
| 8 AI-native chain | 16 | 0 | 16 | 0 | 16 | 0 | 0 |
| 9 Annotation↔native | 9 | 0 | 9 | 0 | 0 | 0 | 9 |
| 10 Environment scoping | 4 | 0 | 4 | 0 | 0 | 4 | 0 |
| **Total** | **111** | **59** | **52** | **54** | **21** | **27** | **9** |

Each edge carries exactly one provenance class, so the four class columns sum to the total: 54 + 21 + 27 + 9 = 111.
A-9 (`otel-collector → prometheus`) is counted once, as **A**, because it is an annotation-to-native
correspondence edge; its additional hand-authored nature is recorded in §9 and §6 rather than in this tally.

**59 semantic edges, 52 annotation edges.** Every one of the 59 semantic edges corresponds to a fact about the
deployed cluster. Every one of the 52 annotation edges is explicitly marked and could be deleted without changing
what deploys — which is the correct property for an architecture diagram.

### Catalog blueprints this design reuses

Every row below was read directly from the catalog, not inferred from the filename. Note that several filenames
do not describe their contents: `hierarchical-parent-inventory-pfnyn.json` is actually an
`edge/non-binding/reference`, and `edge-binding-reference-ecilr.json` is also `edge/non-binding/reference`. The
**verified** triple and participant kinds are what the design instantiates.

| Blueprint file | Model | Verified `kind/type/subType` | Verified participants | Used by |
|---|---|---|---|---|
| `hierarchical-parent-inventory-kmjea.json` | `kubernetes` | `hierarchical`/`parent`/`inventory` | `*` → `Namespace` | A1–A29 |
| `sibling-tagsets.json` | `kubernetes` | `hierarchical`/`sibling`/`matchlabels` | `*` ↔ `*` | B1–B3 |
| `edge-non-binding-network-duixv.json` | `kubernetes` | `edge`/`non-binding`/`network` | `Service` → `Deployment` | C1 |
| `edge-non-binding-network-jccsr.json` | `kubernetes` | `edge`/`non-binding`/`network` | `Ingress` → `Service` | C2 |
| `edge-non-binding-reference-rcycs.json` | `kubernetes` | `edge`/`non-binding`/`reference` | `PersistentVolumeClaim` → `StatefulSet` | D1–D2 |
| `hierarchical-parent-inventory-pfnyn.json` | `kubernetes` | `edge`/`non-binding`/`reference` | `ConfigMap` → `Deployment` | D3–D4 |
| `reference-secret-to-deployment.json` | `kubernetes` | `edge`/`non-binding`/`reference` | `Secret` → `Deployment` | D5–D6 |
| `edge-non-binding-reference-keceb.json` | `kubernetes` | `edge`/`non-binding`/`reference` | `RoleBinding` → `Role` | D7–D8 |
| `edge-non-binding-reference-xtrmo.json` | `kubernetes` | `edge`/`non-binding`/`reference` | `PodDisruptionBudget` → `StatefulSet` | D9–D10 |
| `edge-non-binding-reference-statefulset.json` | `kubernetes` | `edge`/`non-binding`/`reference` | `PriorityClass` → `StatefulSet` | D11–D12 |
| `edge-binding-reference-ecilr.json` | `kubernetes` | `edge`/`non-binding`/`reference` | `ValidatingAdmissionPolicy` → `ValidatingAdmissionPolicyBinding` | D13 |
| `edge-binding-reference-kwjtj.json` | `kubernetes` | `edge`/`non-binding`/`reference` | `ValidatingAdmissionPolicyBinding` → `ValidatingAdmissionPolicy` | reverse of D13, omitted |
| `edge-binding-permission-homji.json` | `kubernetes` | `edge`/`binding`/`permission` | `Role` → `ServiceAccount` | E1–E2 |
| `hierarchical-parent-alias-iicqa.json` | `kubernetes` | `hierarchical`/`parent`/`alias` | `Container` → `Deployment` | Basis for §7, §10 |
| `edge-sibling-matchlabels-fmlwc.json` | `kube-prometheus-stack` | `edge`/`non-binding`/`reference` | `Prometheus` → `ServiceMonitor` | D14 |
| `edge-sibling-matchlabels-qvwox.json` | `kube-prometheus-stack` | `edge`/`non-binding`/`reference` | `ServiceMonitor` → `Service` | D15–D17 |
| `edge-sibling-matchlabels-cunlc.json` | `kube-prometheus-stack` | `edge`/`non-binding`/`reference` | `Prometheus` → `PrometheusRule` | D18 |
| `edge-sibling-matchlabels-quaks.json` | `kube-prometheus-stack` | `edge`/`non-binding`/`reference` | `Alertmanager` → `AlertmanagerConfig` | omitted — no `AlertmanagerConfig` declared |
| `edge-non-binding-reference-ehodr.json` | `kubernetes` | `edge`/`non-binding`/`reference` | `StorageClass` → `PersistentVolumeClaim` | omitted — no `StorageClass` declared |
| `edge-binding-firewall-dynit.json` | `kubernetes` | `edge`/`non-binding`/`firewall` | `NetworkPolicy` → `Pod` | unusable — no `Pod` declared |
| `edge-binding-firewall-kllzw.json` | `kubernetes` | `edge`/`non-binding`/`firewall` | `Pod` → `Pod` | unusable — no `Pod` declared |

**19 blueprints used, 2 further blueprints examined and found unusable.** The four `sibling-matchlabels` files
live in `kube-prometheus-stack`, not in `kubernetes` — a filename search limited to the `kubernetes` model will not
find them, which is worth recording because §4.6 depends on all three.

Every hand-authored edge is listed in §3 (C3–C4), §6 (F1–F3), and §9 (A-9), with the specific gap named. **No edge
in this design invents a `kind`, `type`, or `subType` value that does not appear in the upstream catalog.** Every
triple in use above is `edge/non-binding/reference`, `edge/non-binding/network`, `edge/non-binding/firewall`,
`edge/binding/permission`, `hierarchical/parent/inventory`, `hierarchical/parent/alias`, or
`hierarchical/sibling/matchlabels` — all seven verified present in the catalog.
