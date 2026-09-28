# Validation Plan — `ai-native-platform`

How the design will be verified **before** it is applied to a cluster. Nothing in this plan has been executed
yet — no Design artifact exists.

The plan is ordered by cost. Cheap structural gates run first so that an expensive cluster test is never the
thing that discovers a malformed UUID.

**Governing fact.** `RECONNAISSANCE.md` §C.1 established that `NewPatternFile` only unmarshals — no Draft-07
validation runs on the load path — and §C.2 that the K8s-manifest import path uses `ignoreErrors=true`, silently
dropping unresolvable components. A design can therefore load successfully and still be wrong. Every gate below
exists to catch something the runtime will not.

---

## 0. Environment prerequisites

| Requirement | Value | Note |
|---|---|---|
| Go toolchain | `1.26.4` | Meshery requires it. System `go` is 1.22.2. Use the cached toolchain: `/home/dsk/go/pkg/mod/golang.org/toolchain@v0.0.1-go1.26.4.linux-amd64/bin/go` with `GOTOOLCHAIN=local`. |
| Module cache | `github.com/meshery/schemas@v1.3.37`, `github.com/meshery/meshkit@v1.0.22` | Already present. |
| Draft-07 validator | `ajv-cli`, or `python3-jsonschema` | Needed because the server does not validate. |
| Model catalog | `meshery/models/` at commit `90bac8dc4c9ea5d6d915c41fec0bb013adc1b6fe` | Read-only. |
| Schemas | `~/go/pkg/mod/github.com/meshery/schemas@v1.3.37/schemas/` | Read-only. |
| Working dir for probes | `/tmp/opencode/dsgnprobe` | Outside both repositories. **Never** add files to the Meshery repo. |

Rule: validation code lives in `/tmp`. The Meshery and `meshery-mcp-server` repositories must remain byte-identical
after validation. Verify with `git status --porcelain` returning empty in both.

---

## Gate 1 — Structural schema validation (Draft-07), strict, with one scoped upstream exception

**Why first.** The Design, ComponentDefinition, and RelationshipDefinition schemas are all
`additionalProperties: false`. A single stray key is invisible at runtime and fatal here.

### Gate 1 exception notice — read before running

> **Strict Draft-07 validation against the shipped Meshery schema fails
> for `patchStrategy='replace'`. This is an upstream schema/catalog
> inconsistency. The design preserves the catalog value faithfully.
> The exception is narrowly scoped and does not relax any other schema
> constraint.**

**The defect, precisely.**

| | |
|---|---|
| Field | `relationships[].selectors[].allow.{from,to}[].patch.patchStrategy` (and the `deny[]` equivalent) |
| Actual catalog value | `"replace"` |
| Shipped schema enum | `[merge, strategic, add, remove, copy, move, test]` |
| Conflict | `"replace"` is absent from the enum despite being the value used by the actual Meshery catalog and blueprints |

The enum omits exactly one value, and that value is the **only** value ever used. Measured across the real
repository:

- **10,135** occurrences of `patchStrategy: "replace"` in **4,845** relationship blueprint files.
- **2,762** occurrences in **150** shipped designs.
- **Zero** occurrences of any other value in either place.
- The same 7-value enum appears in **all four** shipped schema versions — `v1alpha3`, `v1beta1`, `v1beta2`,
  `v1beta3` — so this is not a versioning artifact.
- The schema's own `description` prose **does** define it: *"replace: Replaces a value."* The enum drifted from
  its own documentation.

Every real shipped Meshery design therefore fails strict validation of the shipped schema on this one field. This
is an upstream defect, not a defect in this design.

**Decision (option a).** The design preserves `patchStrategy: "replace"` exactly. Specifically **not** done:
substituting `merge`/`strategic`/any other enum value; omitting `patchStrategy`; modifying the shipped Meshery
schema; publishing a forked/patched schema and calling it the shipped one; altering relationship semantics to
satisfy Draft-07.

### Measured scope of the exception

Verified programmatically from the catalog blueprints and the frozen blueprint mapping in
`RELATIONSHIP_MATRIX.md` (`/tmp/opencode/verify/verify_count.py`):

| Class | Relationships | Carries `patchStrategy: "replace"` |
|---|---|---|
| §1 Namespace membership — `hierarchical-parent-inventory-kmjea.json` (29) | 29 | Yes |
| §3 C1–C2 — `edge-non-binding-network-duixv.json` / `…-jccsr.json` (2) | 2 | Yes |
| §4 Reference and binding edges (18 blueprints) | 18 | Yes |
| §7 Section containment — `hierarchical-parent-alias-iicqa.json` (23) | 23 | Yes |
| §10 Environment scoping — `hierarchical-parent-alias-iicqa.json` (4) | 4 | Yes |
| **Blueprint-backed subtotal** | **76** | **Yes** |
| §3 C3–C4 — `Service → StatefulSet` hand-authored, triple copied from `duixv` (2) | 2 | Yes |
| §6 F1–F3 — hand-authored semantic edges, triple copied from a real reference blueprint (3) | 3 | Yes |
| **Hand-authored subtotal** | **5** | **Yes** |
| **Total expected to contain the field** | **81** | |
| §2 Label grouping — `sibling-tagsets.json`, `patch: null` (3) | 3 | No |
| §5 Permission binding — `edge-binding-permission-homji.json`, `patch: null` (2) | 2 | No |
| §8 AI-native chain (16) | 16 | No |
| §9 Annotation↔native correspondence (9) | 9 | No |
| **No-patch subtotal** | **30** | **No** |
| **Total** | **111** | |

The two no-patch blueprint classes are not omissions: `sibling-tagsets.json` and
`edge-binding-permission-homji.json` genuinely carry `patch: null` in the catalog, verified by reading the files.
They assert a grouping or a permission grant and mutate nothing.

**If the authored artifact's count of `patchStrategy` fields is not exactly 81, stop and report the discrepancy
before proceeding.** Do not adjust the design to force the number.

### Harness requirements

Gate 1 remains a **strict** Draft-07 gate. The validator must:

1. Run strict validation against the **shipped, unmodified** schema.
2. Record **every** strict validation failure — the exception is classified, never suppressed.
3. Separate the known `patchStrategy: "replace"` violations from all other failures.
4. Verify every exception matches **exactly** the expected field path **and** value
   (`relationships[i].selectors[j].allow.{from,to}[k].patch.patchStrategy == "replace"`). An exception at any other
   field, with any other value, or on the `deny[]` side outside the documented scope is **not** an exception.
5. **Fail** Gate 1 if **any** other schema violation exists, of any kind.
6. **Pass** Gate 1 only if the artifact has no unexpected violations **and** all remaining violations are exactly
   the documented `patchStrategy: "replace"` exception.
7. Emit **both** reports:
   - `strict-schema-report` — the unmodified strict validator output, exceptions included, as failures.
   - `normalized-schema-report` — the same findings with each violation classified as
     `KNOWN_UPSTREAM_SCHEMA_EXCEPTION` or `UNEXPECTED`, with counts.
8. **Never** modify, patch, or copy the upstream schema. The validator reads it read-only.

Classification vocabulary, used in the normalized report:

| Label | Meaning | Effect on gate |
|---|---|---|
| `KNOWN_UPSTREAM_SCHEMA_EXCEPTION` | Violation is exactly `patchStrategy == "replace"` at a documented selector path | Does not fail the gate; **still reported** |
| `UNEXPECTED` | Any other violation | **Fails the gate** |

A design that reports zero relationships carrying `patchStrategy` is *not* automatically suspicious, but a
design reporting fewer than 81 must be reconciled against the measured scope above before the gate may pass.

### Assertions

1. Top-level keys ⊆ `{id, name, schemaVersion, version, metadata, components, preferences, relationships}`.
2. All 6 required top-level keys present.
3. Every component has all 11 required keys: `id`, `displayName`, `description`, `schemaVersion`, `format`,
   `version`, `configuration`, `metadata`, `model`, `modelReference`, `component`.
4. Every component's `metadata` has all 6 required sub-keys: `genealogy`, `isAnnotation`, `isNamespaced`,
   `published`, `instanceDetails`, `configurationUISchema`.
5. Every component's `component` has all 3 required keys: `version`, `kind`, `schema`.
6. Every relationship has all 7 required keys: `id`, `schemaVersion`, `version`, `model`, `kind`, `type`,
   `subType`.
7. Every relationship's `kind` ∈ `{hierarchical, edge, sibling}`; `status` ∈
   `{enabled, ignored, deleted, approved, pending}`.
8. Every `ModelReference` has all 6 required keys: `id`, `name`, `version`, `displayName`, `model`, `registrant`.
9. Every `id` is a valid UUID, and **no** component or relationship uses the zero UUID
   `00000000-0000-0000-0000-000000000000` (that value is a catalog placeholder, never valid in a design
   instance — `RECONNAISSANCE.md` §K item 4).
10. `name` is 1–255 characters; `version` is 1–50 characters.
11. Exactly **81** relationships contain at least one `patchStrategy` field, and every such field is `"replace"`.
    (The 81 counts *relationships*, not fields. An individual edge may carry more than one: the `inventory`
    blueprint patches both its `from` and `to` side, so each of the 29 namespace edges contributes 2 fields.
    The total field count — and therefore the total number of findings in either report — is a *derived* number,
    recomputed from the artifact, and is not fixed at 81.)
12. Zero violations classified `UNEXPECTED`.

**Pass:** assertions 1–10 and 12 hold with no unexpected violation, and assertion 11 holds exactly. The
`patchStrategy` findings are present in `strict-schema-report` as real failures and are the *only* failures.

**Raw validation invocation** (unmodified schema, exceptions deliberately left in place):

```bash
ajv validate \
  -s ~/go/pkg/mod/github.com/meshery/schemas@v1.3.37/schemas/constructs/v1beta3/design/design.yaml \
  -d design.yml
```

This command **is expected to fail** on the `patchStrategy` enum. That failure is the evidence, not a problem to
be engineered away. The harness post-processes its output per the classification table above; it does not alter
the validator, the schema, or the artifact.

---

## Gate 2 — Go struct round-trip

**Why.** The JSON Schema permits documents the generated Go structs cannot represent. This gate is what
`NewPatternFile` will actually do.

Reuse the probe pattern proven in `RECONNAISSANCE.md` Appendix: a throwaway module in
`/tmp/opencode/dsgnprobe` that calls `meshkit/encoding.Unmarshal` into
`github.com/meshery/schemas/models/v1beta3/design.PatternFile` and then marshals back to JSON.

**Assertions:**
1. `Unmarshal` succeeds.
2. Re-marshalled output has the same component count (66) and relationship count (111).
3. Every `component.id` and `relationship.id` survives the round trip unchanged.
4. Every relationship's `selectors[].allow.from|to[].id` still resolves to an existing `component.id` — the
   round trip must not silently drop or blank selector IDs.
5. Every annotation component's `metadata.isAnnotation == true`; every native component's `isAnnotation == false`.
6. Re-marshalled output re-validates against `design.yaml` under Gate 1.

**Pass:** all six hold. **This is the single most important gate** — assertion 4 is exactly the failure the
runtime would hide.

---

## Gate 3 — Model and component resolution

**Why.** This is the check that Gate 1 cannot do. A `kind` can be perfectly valid JSON and still not exist in the
declared model. And per `RECONNAISSANCE.md` §C.2, unresolvable components are **silently dropped** on the import
path — so this must be done offline, before the server ever sees the file.

For each of the 66 components, assert that
`models/<model>/<modelVersion>/<componentVersion>/components/<kind>.json` exists.

**Expected resolutions:**

| Model | Kinds to resolve | Instances |
|---|---|---|
| `kubernetes` `v1.37.1/v1.0.0` | `Namespace`×4, `ServiceAccount`×2, `Role`×2, `RoleBinding`×2, `Deployment`×1, `Service`×3, `Ingress`×1, `ConfigMap`×2, `Secret`×3, `StatefulSet`×2, `PersistentVolumeClaim`×2, `NetworkPolicy`×2, `ResourceQuota`×1, `LimitRange`×1, `ValidatingAdmissionPolicy`×1, `ValidatingAdmissionPolicyBinding`×1, `PriorityClass`×1, `PodDisruptionBudget`×2 | 33 |
| `meshery-core` `0.7.2/v1.0.0` | `Environment`×1, `GenericNode`×14, `Section`×8, `Comment`×2, `Credential`×1 | 26 |
| `meshery-operator` `1.0.70/v1.0.0` | `MeshSync`×1, `Broker`×1 | 2 |
| `kube-prometheus-stack` `89.2.2/v1.0.0` | `Prometheus`×1, `ServiceMonitor`×1, `Alertmanager`×1, `PrometheusRule`×1 | 4 |
| `sumologic` `4.18.0/v1.0.0` | `OpenTelemetryCollector`×1 | 1 |
| | | **66** |

Native total 40 (33 + 2 + 4 + 1); annotation total 26 (all `meshery-core`). **All 66 paths above were confirmed to
exist on disk during authoring**, as were all 18 distinct `kubernetes` kinds. This gate re-runs that check to
detect catalog drift before apply.

**Additional assertions:**
5. Each resolved catalog file's `status == "enabled"`.
6. Each resolved catalog file's `model.name` and `model.model.version` match the design's declared `model` block.
7. **`component.version` strings are read from the catalog, not assumed.** The following were verified during
   authoring and must be re-checked against the catalog rather than trusted from this document:
   `ValidatingAdmissionPolicy` and `ValidatingAdmissionPolicyBinding` are both
   `admissionregistration.k8s.io/v1` (the GA `v1` API, **not** `v1alpha1`); `PodDisruptionBudget` is `policy/v1`;
   `PriorityClass` is `scheduling.k8s.io/v1`; `OpenTelemetryCollector` is `opentelemetry.io/v1alpha1`; all five
   `meshery-core` kinds used here are `core.meshery.io/v1alpha1`.
8. Confirm `Ingress.component.version == "networking.k8s.io/v1"`,
   `Deployment/StatefulSet.component.version == "apps/v1"`,
   `Role/RoleBinding.component.version == "rbac.authorization.k8s.io/v1"`,
   `NetworkPolicy.component.version == "networking.k8s.io/v1"`.
9. Confirm `PodDisruptionBudget` component version (`policy/v1`).
10. For annotation components, confirm the catalog file's `component.version == "core.meshery.io/v1alpha1"`.
    `component.schema` is the empty string for `Environment`, `GenericNode`, `Section`, and `Credential`; it is
    **non-empty** for `Comment` (an inline Draft-07 schema for `userMessages`). An assertion that every
    `meshery-core` component has an empty `schema` would fail on `Comment` — the two notes rely on it.

**Pass:** all 66 resolve; all 10 assertions hold.

---

## Gate 4 — Schema version consistency

**Why.** ADR-014 declares `components.meshery.io/v1beta2` on every component, including those sourced from
`meshery-core` (catalog says `v1beta1`) and `sumologic` (catalog says `v1beta1`). This is the design's
**highest-risk assumption**, and it cannot be verified offline.

**Offline assertions:**
1. Every component declares `schemaVersion: components.meshery.io/v1beta2`.
2. Every relationship declares `schemaVersion: relationships.meshery.io/v1beta2`.
3. Every relationship's `model.name` is one of the five models in the design. (`meshery-core` ships **no**
   relationship blueprints, so annotation-level edges have no model to inherit from — the design assigns them the
   `meshery-core` model explicitly. Confirm this is acceptable, per Gate 8 item 3.)
4. The v1beta3 design schema's `$ref` target is `v1beta2/component` and `v1beta2/relationship` — re-read to
   confirm no drift since `RECONNAISSANCE.md`.

**Online assertion — requires a running Meshery server:**
5. Load the design and confirm the server does **not** reject a `components.meshery.io/v1beta2` declaration on a
   `meshery-core` component. If it does, ADR-014 must be revisited: the fallback is to mirror each source
   model's declaration, accepting a mixed-schema design.

**Pass:** assertions 1–4 offline; assertion 5 before any apply.

---

## Gate 5 — Relationship integrity

**Why.** Relationships are the most error-prone part of a design and the least validated upstream.

**Assertions:**
1. Every relationship `id` is unique.
2. Every `selectors[].allow.from[].id` and `.to[].id` names a `components[].id` that exists in the same design.
3. Every `selectors[].item` has an `allow` key (required by `SelectorSetItem`).
4. Every `selectors[].item.allow.from` and `.to` is a non-empty array.
5. Every `SelectorItem` has a `kind` (required); `"*"` is permitted as a wildcard.
6. Every relationship that has a `patch` uses `patchStrategy: replace` and provides at least one of
   `mutatorRef` / `mutatedRef` in array-of-path-strings form.
7. **No component appears as the `from` side of more than one namespace-membership (`hierarchical/parent/inventory`)
   relationship per namespace.** A component has exactly one namespace, so 29 in / 29 inventory edges, no
   component twice.
8. Count check: 111 relationships total, distributed as 29 + 3 + 4 + 18 + 2 + 3 + 23 + 16 + 9 + 4 per
   `RELATIONSHIP_MATRIX.md` §11. Note that §4 is 18 edges (D1–D18), not 21; an earlier draft of this plan
   miscounted it.
9. Every relationship is classified: `metadata.isAnnotation` is explicitly `true` or `false` — not omitted.
   Expected: 59 `false`, 52 `true`.
10. Every `kind`/`type`/`subType` triple in the design appears in at least one real upstream blueprint. **No triple
    is invented.** Only seven distinct triples are in use, all verified present in the catalog:
    `edge/non-binding/reference`, `edge/non-binding/network`, `edge/non-binding/firewall`,
    `edge/binding/permission`, `hierarchical/parent/inventory`, `hierarchical/parent/alias`,
    `hierarchical/sibling/matchlabels`. Blueprint files must be searched **per model** — the four
    `sibling-matchlabels` files live in `kube-prometheus-stack`, not `kubernetes`, so a `kubernetes`-only search
    will report them missing. The verified triple/participant table in `RELATIONSHIP_MATRIX.md` §11 is the
    reference; note that several blueprint filenames do not describe their contents.

**Pass:** all ten hold. Assertion 10 is the anti-fabrication check for the whole design.

---

## Gate 6 — Hand-authored edge review

**Why.** Six individually-named edges have no upstream blueprint, and a seventh class of 27 grouping edges is
analogy-based. Together they are the design's only departures from directly blueprint-backed structure, and each
needs individual sign-off. All six gaps were confirmed by exhaustive search of every `relationships/*.json` in all
477 models during authoring.

| Edge | Gap | Verified? | Review question |
|---|---|---|---|
| C3 `svc-redis → sts-redis` | No `Service → StatefulSet` blueprint | Zero matches catalog-wide | Is copying the `Service → Deployment` triple defensible? |
| C4 `svc-postgres → sts-postgres` | Same | Zero matches | Same |
| F1 `sec-state-creds → sts-postgres` | No `Secret → StatefulSet` blueprint | Zero matches | Is `edge/non-binding/reference` right, or should this be `binding`? |
| F2 `sec-state-creds → sts-redis` | Same | Zero matches | Same |
| F3 `prometheus → alertmanager` | No `Prometheus → Alertmanager` blueprint | Zero matches | Confirm the alert path is real and the direction is correct. |
| A-9 `otel-collector → prometheus` | `sumologic` ships no `relationships/` directory at all | Directory absent (only `components/` + `model.json`) | Should this edge be annotation-level? It currently is. |
| §7 + §10 (27 edges) | No `Section` blueprint exists in any model | No blueprint pairs `Section` with anything | Is `hierarchical/parent/alias` right, or should grouping use another mechanism? |

The first six are individually authored edges. The last row is 27 containment edges, all sharing one gap, counted
as a single review item.

**Assertions:**
1. Each is listed in `RELATIONSHIP_MATRIX.md` with its gap named. ✔ (already satisfied by the spec)
2. Each uses only triples present upstream. ✔ (Gate 5 assertion 10)
3. Each is either marked `isAnnotation: true` or has a written justification for being semantic.
   - C3, C4, F1, F2, F3 are marked **semantic** — confirm this is correct, since a hand-authored edge asserting a
     semantic fact carries more risk than one asserting intent.
4. The NetworkPolicy gap is **not** worked around: assert the design contains **zero** `Pod` components and zero
   firewall `edge` relationships. Adding `Pod` components to satisfy a blueprint is the specific failure this gate
   exists to prevent.

**Pass:** all four assertions hold with each of the six edges and the containment class explicitly signed off.

---

## Gate 7 — Cluster-level assumptions

**Why.** Several design decisions are correct in the schema but depend on cluster state. These cannot be
validated offline and must be confirmed before the design is trusted.

1. **CNI enforces `NetworkPolicy`.** ADR-005 assumes a `NetworkPolicy`-enforcing CNI is installed. Confirm the
   target cluster enforces it; if not, `netpol-default-deny` and `netpol-ai-allowlist` are inert and ADR-005
   needs revisiting.
2. **Prometheus Operator CRDs installed.** `prometheus`, `sm-platform`, `alertmanager`, and
   `promrule-platform-slo` are CRDs from `monitoring.coreos.com/v1`. The design does **not** include the
   operator — it is a cluster prerequisite. Confirm before apply.
3. **OpenTelemetry Operator CRDs installed.** `otel-collector` is `opentelemetry.io/v1alpha1`. Same situation.
4. **Meshery Operator CRDs installed.** `meshsync` and `broker` are `meshery.io/v1alpha1`. Same situation.
5. **`ValidatingAdmissionPolicy` is GA in the target cluster.** If the cluster is older than 1.30, the
   `admissionregistration.k8s.io/v1` API is unavailable and ADR-006's enforcement point does not exist. Check
   the cluster version — it must be ≥ 1.30 for the `v1` API.
6. **A default `StorageClass` exists.** ADR-004 omits `StorageClass`, so `pvc-redis` and `pvc-postgres` bind to
   the cluster default. Confirm one exists, or the PVCs stay `Pending`.
7. **An ingress controller is installed.** ADR-012 defers the controller choice to the cluster, so
   `ingress-ai-platform` needs one. Confirm before relying on the ingress path.

**Pass:** all seven confirmed, or the affected design decision is revisited.

---

## Gate 8 — Server load and render

**Why.** The first end-to-end check against a real Meshery server. Everything before this was offline.

1. `mesheryctl design import design.yml` — confirms the server accepts the document and that
   `files.IdentifyFile` classifies it as `core.MesheryDesign`.
2. **Assert the post-import component count is exactly 66.** This is the anti-silent-drop check. Because
   `NewPatternFileFromK8sManifest` uses `ignoreErrors=true`, a count below 66 means components were dropped
   without an error. A count above 66 means the server synthesised something.
3. Confirm the relationship count is 111 and that no relationship was discarded as unresolvable.
4. Confirm the design renders in the Meshery UI with the eight `Section` bands, the annotation nodes visually
   distinct, and no layout collapse.
5. Confirm the namespace-membership relationships produced the expected `metadata.namespace` on all 35
   namespaced components. **This is the single check most likely to reveal a design error**, because namespace
   assignment is relationship-driven and easy to mis-wire.
6. Confirm `metashery apply --dry-run` produces a manifest set matching the 40 native components and produces
   **nothing** for the 26 annotation components.
7. Re-read the saved design from the server and diff it against the authored file. Divergence reveals server-side
   normalisation that would break future re-imports.

**Pass:** 66 components, 111 relationships, no drops, no synthesis, correct namespaces, no manifests for
annotations.

---

## Gate 9 — Design-intent review

**Why.** The last gate is human. Automated gates cannot tell whether the design is *right*.

1. **Trace the request path.** `mcp-access-gateway → agent-runtime → model-router → grounding-validator →
   tier-*`. Confirm the annotation chain in `FINAL_ARCHITECTURE.md` §4 matches the file.
2. **Trace the scrape path.** Workloads → `otel-collector` → `prometheus` → `sm-platform` → the three Services.
   Confirm no gap.
3. **Trace the alert path.** `promrule-platform-slo` → `prometheus` → `alertmanager`. Confirm the hand-authored F3
   is the only unproven link.
4. **Trace the credential path.** `registry-credential` → `sec-registry-creds` → `deploy-meshery-control`;
   `sec-state-creds` → `sts-postgres` / `sts-redis`. Confirm no secret is orphaned and none is referenced by a
   component that should not have it.
5. **Confirm no annotation has a real counterpart that was forgotten.** Cross-check every one of the 26
   annotations against `UNSUPPORTED_CONCEPTS.md` — each should appear with a stated reason.
6. **Confirm every exclusion still holds.** Re-read ADR-003, ADR-007, ADR-008, ADR-012. If any of
   `istio-base`, Grafana, HPA, or Gateway API has become a requirement, the corresponding ADR must be reopened
   before the design is applied.

---

## Known failure modes this plan does not catch

| Failure | Why it is not caught | Mitigation |
|---|---|---|
| Annotation components silently creating cluster resources | Not a schema property; depends on server behaviour | Gate 8 item 6 |
| Namespace written to the wrong namespace because an inventory edge is malformed | Schema-valid either way | Gate 2 assertion 4, Gate 8 item 5 |
| Annotation-level edges being honoured as real bindings at apply time | Depends on server interpretation of `isAnnotation` | Gate 8 item 6 — verify no unintended manifests |
| The catalog being stale relative to the deployed Meshery server | Offline validation reads the catalog, not the server's registry | Gate 8 item 7 diff |
| `sumologic` model being withdrawn or its component renamed | External event | Re-run Gate 3 before each apply |
| Empty `configuration` on `deploy-meshery-control` producing a pod with no image | Deployment-time, not design-time | Gate 8 item 6 dry-run manifest review |
| **A future upstream schema fix removes `replace` from being used, or adds it to the enum** | Gate 1's exception is scoped to the *current* shipped schema | Re-run Gate 1 on schema change; if the enum gains `replace`, the exception naturally becomes 0 findings and Gate 1 must be re-baselined |
| **A design legitimately needing a non-`replace` patch strategy** | The exception masks nothing, but a new strategy would appear as `UNEXPECTED` and correctly fail the gate | Add a new documented exception class; never widen the existing one |

---

## Acceptance criteria

The design is ready to apply when **all** of the following hold:

- [ ] Gate 1: zero `UNEXPECTED` violations; exactly 81 relationships carry `patchStrategy: "replace"`, all such findings classified `KNOWN_UPSTREAM_SCHEMA_EXCEPTION`; both `strict-schema-report` and `normalized-schema-report` produced; upstream schema unmodified
- [ ] Gate 2: round-trip preserves 66 components, 111 relationships, and every selector ID
- [ ] Gate 3: all 66 components resolve to an enabled catalog entry; `component.version` strings verified from disk
- [ ] Gate 4: assertions 1–4 pass offline; assertion 5 confirmed against a server
- [ ] Gate 5: all 10 assertions pass, including no invented `kind`/`type`/`subType`
- [ ] Gate 6: all 6 hand-authored edges and the containment class signed off; zero `Pod` components
- [ ] Gate 7: all 7 cluster prerequisites confirmed
- [ ] Gate 8: server import yields exactly 66 components and 111 relationships with no drops
- [ ] Gate 9: all six intent traces confirmed by a reviewer

**Definition of done:** Gates 1–8 automated and green in CI; Gate 9 signed off by a human reviewer who has read
`UNSUPPORTED_CONCEPTS.md` — specifically, who accepts that 26 of 66 components are annotations producing no
cluster resources, and that MCP access, the agent runtime, the model router, and all three fallback tiers are
specified but not deployed.
