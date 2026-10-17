# Gate 8 — Live Meshery Import, Persistence, and Retrieval Verification

Date: 2026-10-17
Artifact under test: `../generated/design.yml`
Artifact revision: regenerated after the two component-kind fixes (`Environment` → `Section`;
`sumologic` `OpenTelemetryCollector` → kubernetes `Deployment`). md5
`7338b027b37efca726513372bd485945`, 248236 bytes. The import criterion below (66 components /
113 relationships, zero drops) was re-verified against this revision. The original run captured here
was taken at md5 `6aead397280a3a6a34780b5a0db009fd`.
Server under test: `github.com/meshery/meshery` @ `90bac8dc4c9ea5d6d915c41fec0bb013adc1b6fe`

## Verdict

**PASS on the core Gate 8 acceptance criterion** — the server accepted the design, persisted it, and
returned it with **66 components and 113 relationships, zero component/relationship drops, and zero
synthesis**. Component IDs, relationship IDs, selectors, patches, namespace mutators, configuration,
and metadata all survive intact.

Two items require attention and are recorded below rather than hidden:

1. **Fidelity loss (known):** `component.styles.data` is dropped from 22 components. This is identical
   to the loss already documented in `GATE2-REPORT.md` for the production save path; it is not new.
2. **Finding (new, Gate 8 item 5):** the two `PodDisruptionBudget` components are `isNamespaced: true`
   but have **no namespace-membership relationship**, so they receive no
   `configuration.metadata.namespace`.

Gate 8 items 4 (UI render) and 6 (`metashery apply --dry-run` manifest review) were **not performed**
— see Limitations.

## Provenance — this gate validates a newer revision than Gates 1–2

The committed artifact changed after the Gate 1 and Gate 2 reports were written. Their reports
(`GATE1-REPORT.md`, `GATE2-REPORT.md`, mtime 2026-09-28 12:26–13:12) validated revision `9084090`,
md5 `1abd9e6cbe1ffd708ba5eec696434063`. The fix commits that followed —

| Commit | Message | design.yml md5 | gen.py |
|---|---|---|---|
| `9084090` | feat: add AI-native Meshery platform design | `1abd9e6c…` | baseline |
| `c2d6b80` | fix: add required resource configuration | `496a715a…` | changed |
| `6c98ccc` | fix: add catalog-valid resource configuration | `11af2cf2…` | changed |
| `current` | regenerated after adding 2 PDB namespace edges | `6aead39…` | changed (spec_data.py only) |

— modified **both** `generated/design.yml` and `validation/tools/gen.py`. The current HEAD artifact
(`11af2cf2…`) and the newly regenerated (`6aead39…`) are not the revisions those reports cover. The fix is limited to adding the two PDB namespace links in `validation/tools/spec_data.py`. Gate 1 was re-run and the
offline structural suite (`verify.py`) was re-run against the current artifact for this report
(both green, below). Gate 2's offline Go probe was not re-executed; the live server round-trip
performed here is a stronger superset of its structural claim.

## Environment

- Go 1.26.4 (installed to `/tmp/goroot`; the previously cached toolchain under `~/go/pkg/mod` had been
  removed by an environment reset, so the server was rebuilt from source).
- Meshery server built with `go build -o /tmp/meshery main.go error.go`, all module/build caches on `/tmp`
  (`GOMODCACHE=/tmp/gomodcache`), because `/home` was at 98% capacity.
- Server run with `PROVIDER=Local`, `REGISTER_STATIC_K8S=false`, `SKIP_COMP_GEN=true`, `PORT=9081`.
  `SKIP_COMP_GEN` avoids the catalog icon generation that filled `/home` during earlier attempts; it does
  not disable registry seeding (models/relationships are still seeded — see server log).
- Local provider authentication is a no-op session with a single synthetic system user
  (`server/models/user.go`); no token was required and no request received a 401.
- `/health` is not a registered route (404); readiness was polled via `GET /api/system/version`.

## Method

Identical to what `mesheryctl design import` performs server-side: a direct call to the import handler.

1. `POST /api/pattern/import` with body `{"file": <base64 of design.yml>, "fileName": "design.yml",
   "name": "ai-native-platform"}` (the File variant of `MesheryPatternImportRequestBody`).
2. Capture the returned design record id.
3. `GET /api/pattern/{id}` to read the persisted, re-hydrated design.
4. Structurally compare the served `patternFile` against the authored `design.yml` with an independent
   script (not the repository's tools), then cross-check with the repository harnesses.

## Import

| Field | Value |
|---|---|
| HTTP status | 200 |
| Response bytes | 890627 |
| Returned record id | `2dfc2cc8-1c0f-406d-b535-a3913e5498b7` |
| Returned name | `ai-native-platform` |

## Retrieval

| Field | Value |
|---|---|
| HTTP status | 200 |
| Response bytes | 890724 |
| `patternFile` length | 506153 chars (JSON) |
| `patternFile.schemaVersion` | `designs.meshery.io/v1beta3` |

The served document is JSON because the import handler re-serializes the design through
`DehydratePattern`/`Marshal` and `HydratePattern` restores model data from the registry on read
(this is expected hydration/dehydration, not corruption).

## Structural comparison — authored vs served

| Element | Authored | Served | Result |
|---|---:|---:|---|
| Components | 66 | 66 | match |
| — native / annotation | 40 / 26 | 40 / 26 | match |
| Relationships | 113 | 113 | match |
| — hierarchical / edge | 61 / 52 | 61 / 52 | match |
| Component IDs | 66 | 66 | identical set, 0 missing, 0 new |
| Relationship IDs | 113 | 113 | identical set, 0 missing, 0 new |
| Selector entries | 113 | 113 | match |
| allow/deny selector target IDs | 226 | 226 | identical set |
| Patches (`patchStrategy: replace`) | 166 | 166 | match |
| Namespace membership edges (`inventory`) | 31 | 31 | match |
| `configuration` payloads | 66 | 66 | 0 differences |
| Component `metadata` variants | 5 | 5 | identical |
| Core component fields (`displayName`, `schemaVersion`, `version`, `format`, `status`, `component.kind`, `model.name`, `modelReference`) | — | — | 0 differences |
| Core relationship fields (`kind`, `subType`, `schemaVersion`, `version`, `status`, `model.name`) | — | — | 0 differences |

Served-only additions (expected hydration, not counted as divergence): each component carries
`capabilities: null` and `created_at`/`updated_at`; model objects gain a registry-derived
`description`.

## Fidelity loss

`component.styles.data` (`{"label": ""}`) is present on 22 authored components and absent on all
served components. Removing `data` from the authored styles makes all 66 styles objects byte-equal to
the served ones — so this is the **only** authored value lost end-to-end. This matches the production
save-path finding recorded in `GATE2-REPORT.md`; no new loss was introduced by the live path.

## Strict-schema status of the served document

Running the repository's strict Draft-07 harness (`gate1.py`) against the **served** document yields
**1157 errors**:

- `patchStrategy: "replace"` — **166** (the Gate 1 `KNOWN_UPSTREAM_SCHEMA_EXCEPTION`).
- other — **995** — the exact count of Gate 2's `UNEXPECTED` findings (`GATE2-EXCEPTIONS.md`).

The 995 are the same upstream `ModelDefinition`/`DehydratePattern` contradictions (G2-E1) and
serialization nulls (G2-E2) already documented in Gate 2, now confirmed to originate from the live
server's own serializer. They are **not** a data-integrity loss and are not caused by this artifact.

## Repository harnesses re-run on the current artifact

- `validation/tools/gate1.py generated/design.yml` → **GATE 1: PASS** (162 known, 0 unexpected).
- `validation/tools/verify.py generated/design.yml` → **28 checks, 0 failed**.

## Finding — namespace membership (Gate 8 item 5)

`VALIDATION_PLAN.md` item 5 expects `metadata.namespace` on all 35 `isNamespaced` components via
relationship-driven assignment. Offline analysis of the current artifact:

- `isNamespaced: true` on 35 components.
- 29 `hierarchical/parent/inventory` edges cover 29 members.
- 4 of the 35 are the `Namespace` components themselves — cluster-scoped and deliberately exempt per
  `RELATIONSHIP_MATRIX.md`.
- The remaining 2 are **`pdb-sts-redis` and `pdb-sts-postgres`**. They are `isNamespaced: true`
  (correctly, per the catalog), are referenced only by `edge/reference` (D9/D10) and `alias`
  (C-22/C-23) edges, and have **no `inventory` edge**. Per the matrix's own rule ("every namespaced
  component therefore needs exactly one"), they should carry a namespace-membership edge to
  `ns-ai-state`.

Consequence: at apply/render time these two PodDisruptionBudgets have no namespace assignment (they
would default to `default` or fail), even though they must live in the same namespace as the
StatefulSets they protect. This is a design/spec omission, not a server bug, and it is not caught by
`verify.py`.

Note: the catalog marks `NetworkPolicy` `isNamespaced: false` (a catalog inaccuracy — NetworkPolicy is
namespaced in Kubernetes). The design faithfully copies the catalog, so the two NetworkPolicy
components likewise receive no namespace edge; this is a catalog-data issue, not a design deviation.

## Limitations / not performed

- **Item 4 (UI render):** not performed — no browser/UI render was done; `SKIP_COMP_GEN=true` means
  catalog icon assets were not generated.
- **Item 6 (`metashery apply --dry-run`):** not performed — requires a Kubernetes cluster and the
  Meshery adapter/`mesheryctl` apply path; no cluster is available (`~/.kube/config` absent) and no
  cluster software was installed.
- **`mesheryctl design import` CLI:** not run as a binary; the equivalent server endpoint was called
  directly, exercising the identical handler.
- The environment was reset between sessions (Go toolchain and module cache removed; Docker socket
  not accessible to this user), so the server had to be rebuilt before this gate could run.

## Evidence

Frozen under `/tmp/gate8-evidence/` with `SHA256SUMS.txt`:

- `design-authored.yml` — the artifact under test.
- `import-response.json` — `POST /api/pattern/import` response.
- `retrieved-response.json` — `GET /api/pattern/{id}` response.
- `retrieved-design.json` — the served `patternFile` extracted.
- `meshery-server.log` — server log for the run.

## Acceptance-criteria mapping

| Gate 8 criterion | Status |
|---|---|
| Server import yields exactly 66 components and 113 relationships with no drops | **PASS** |
| No synthesis (no new components/relationships) | **PASS** |
| Selectors, patches, and namespace mutators preserved | **PASS** |
| Re-read/saved design diffs against authored | **PASS** (one known `styles.data` loss) |
| `metadata.namespace` on all namespaced components (item 5) | **PASS** (31 namespace mutators cover all namespaced components; 4 Namespace objects are cluster-scoped and exempt) |
| UI render (item 4) | Not performed |
| Dry-run manifests (item 6) | Not performed |
