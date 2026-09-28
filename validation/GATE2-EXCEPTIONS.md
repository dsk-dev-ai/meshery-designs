# Gate 2 exception analysis — upstream defects

Companion to `GATE2-REPORT.md`, which remains the **strict execution record**: it reports
`FAIL` on assertion 6 and is not amended. This document does not reclassify that result. It
records two separately-numbered upstream exceptions, each traced to the shipped Meshery Go
and schema definitions, and assigns each a final classification.

This does **not** widen the Gate 1 `patchStrategy` exception. That exception remains scoped to
`relationships[i].selectors[j].allow.{from,to}[k].patch.patchStrategy == "replace"` and is
counted separately (162 findings, unchanged through the round trip). No finding in this
document is a `patchStrategy` finding.

## Summary

| | Strict schema failure | Classification | Runtime effect |
|---|---|---|---|
| G2-E1 | 396 | known upstream contradiction | none — block is deleted before persist, re-fetched on read |
| G2-E2 | 599 | serialization-only difference | none — every consumer is nil-guarded or has a default |
| Artifact loss | 0 schema findings | `styles.data` on 22 components | cosmetic, value is `{"label": ""}` |
| Gate 1 `patchStrategy` | 162 | known upstream exception (unchanged) | none — preserved verbatim |

Round trip: **995 UNEXPECTED = 396 (G2-E1) + 599 (G2-E2)**.
Artifact under test: `../generated/design.yml`, unmodified.

---

## G2-E1 — `ModelDefinition` schema / Go-struct contradiction

### The four schema-required fields the Go round-trip cannot emit

`component.yaml` `$ref`s `v1beta1/model/model.yaml`, which sets `additionalProperties: false` and
requires 17 fields. Four of them have no faithful Go representation:

| Schema-required field | Required by | Go struct field | Go JSON tag | Emitted? |
|---|---|---|---|---|
| `categoryId` | `model.yaml` `required` | `CategoryId core.Uuid` | `json:"-"` | **no — dropped outright** |
| `registrantId` | `model.yaml` `required` | `RegistrantId core.Uuid` | `json:"connection_id"` | **no — mis-tagged** |
| `componentsCount` | `model.yaml` `required` | `ComponentsCount int` | `json:"components_count"` | no — wrong spelling |
| `relationshipsCount` | `model.yaml` `required` | `RelationshipsCount int` | `json:"relationships_count"` | no — wrong spelling |

`RegistrantId` carrying the tag `json:"connection_id"` is a copy-paste error in
`schemas@v1.3.37/models/v1beta1/model/model.go`. It is a single-token substitution of
`registrant` → `connection`.

### Go-emitted model fields rejected by `additionalProperties: false`

| Go-emitted key | Struct field | Verdict |
|---|---|---|
| `connection_id` | `RegistrantId` | rejected — not in the schema's 19 allowed properties |
| `components_count` | `ComponentsCount` | rejected — schema spells it `componentsCount` |
| `relationships_count` | `RelationshipsCount` | rejected — schema spells it `relationshipsCount` |

`Category.metadata` is a fourth required field with no Go field at all: the schema requires
`model.category.metadata`, and the Go `categoryv1beta1.CategoryDefinition` has no such member.

So the four fields the schema **requires** are exactly the four the runtime **cannot emit**, and
the three the runtime **does** emit under wrong names are exactly the ones the schema
**forbids**. The contradiction is bidirectional, not a one-way omission.

### 396 violations attributed to this contradiction

| Finding | Count |
|---|---|
| `components[N]/model :: 'categoryId' is a required property` | 66 |
| `components[N]/model :: 'registrantId' is a required property` | 66 |
| `components[N]/model :: 'componentsCount' is a required property` | 66 |
| `components[N]/model :: 'relationshipsCount' is a required property` | 66 |
| `components[N]/model :: Additional properties are not allowed ('components_count', 'connection_id', 'relationships_count' …)` | 66 |
| `components[N]/model/category :: 'metadata' is a required property` | 66 |
| **Total** | **396** |

66 components × 6 findings. No finding in this table is attributable to anything this artifact
does or omits; the four required fields are populated correctly in `generated/design.yml` and it
passes Gate 1 with **0 UNEXPECTED**.

### Identical behavior reproduced using a Meshery-shipped design

Control: `meshery/docs/data/catalog/00fadfee-3655-40c7-8a38-6c5cd72ea4da/0.0.1/design.yml`,
a design shipped by the Meshery project, round-tripped through the identical probe:

```
UNEXPECTED components/0/model :: 'categoryId' is a required property
UNEXPECTED components/0/model :: 'componentsCount' is a required property
UNEXPECTED components/0/model :: 'registrantId' is a required property
UNEXPECTED components/0/model :: 'relationshipsCount' is a required property
UNEXPECTED components/0/model :: Additional properties are not allowed
        ('components_count', 'connection_id', 'relationships_count' were unexpected)
UNEXPECTED components/0/model/category :: 'metadata' is a required property
```

**265 UNEXPECTED for 12 components** — the same six findings per component. Assertion 6 is
therefore unsatisfiable for any Meshery design, including the project's own.

Independent corroboration that the mis-spelling is live in the catalog: a shipped design
(`070b4569-2b26-4e13-93f7-9992fdf1e6fd/0.0.332/design.yml`) already carries a model block
serialised in the **Go struct's** spelling — `"connection_id"`, `"components_count": 0`,
`"relationships_count": 0` — not the schema's. The tag bug is pre-existing and observable in
released data.

### Runtime effect: none, and the mechanism is deliberate

`handlePatternPOST` (`meshery/server/handlers/meshery_pattern_handler.go:374-376`) does:

```go
meshkitPatternHelpers.DehydratePattern(&requestPayload.DesignFile)
designFileBytes, err := encoding.Marshal(requestPayload.DesignFile)
…
provider.SaveMesheryPattern(token, &mesheryPatternRecord)   // PatternFile: string(designFileBytes)
```

`meshkit/models/patterns.DehydratePattern` is:

```go
for _, comp := range pattern.Components {
    comp.Component.Schema = ""
    comp.Capabilities = nil
    if comp.Model != nil {
        comp.ModelReference = comp.Model.ToReference()
    }
    comp.Model = nil
}
```

`comp.Model = nil` — the whole block this exception is about is **deleted before it is
persisted**. Simulating the real save path (`Unmarshal → DehydratePattern → Marshal`) confirms
it: G2-E1's 396 findings **drop to 0** in the persisted document, replaced by a single
`components[N]/model :: None is not of type 'object'` per component (66), which is the intended
dehydrated storage form.

The mirror image runs on read. `meshkit.HydratePattern` restores `comp.Model`,
`comp.Component.Schema` and `comp.Capabilities` from the registry
(`server/handlers/design_engine_handler.go:129`, `server/handlers/policy_relationship_handler.go:315`),
keyed on `comp.ModelReference.Name` + `comp.Component.Kind` + `comp.Component.Version` — **not**
on the design's own model block.

Verified: the `modelReference` that `ToReference()` regenerates from our authored model is
**identical** to the one we wrote, for all 66 components. So our model block is consumed
correctly and the persisted reference is unchanged.

**Conclusion.** The v1beta3 design schema describes the **hydrated API** form; Meshery persists
the **dehydrated** form. These are two different documents and no single document satisfies
both. G2-E1 is a genuine strict schema failure and a real upstream contradiction, with no
runtime consequence for this design.

---

## G2-E2 — non-`omitempty` / null fields

Not assumed harmless. Each field was traced through the shipped Go struct, the shipped schema,
and every live read site in `meshery` at commit `90bac8dc4`.

**599 violations** decompose as: the four named fields account for **459**, and three further
null injections riding the same mechanism bring the total to **599**.

| Field | Violations | Struct tag | Consumer | Verdict |
|---|---|---|---|---|
| `relationships[].evaluationQuery` | 111 | `json:"evaluationQuery"` (no `omitempty`) | nil-guarded CLI display | **3 — ignored by the runtime** |
| `…allow.{from,to}[].matchStrategyMatrix` | 222 | `json:"matchStrategyMatrix"` (no `omitempty`) | nil guard → explicit `equal` default | **2 — serialization artifact** |
| `…allow.{from,to}[].patch` | 60 | `json:"patch"` (no `omitempty`) | every read nil-guarded; nil ≡ absent | **2 — serialization artifact** |
| `components[].capabilities` | 66 | `json:"capabilities"` (no `omitempty`) | `DehydratePattern` nils it; `HydratePattern` re-fetches | **2/3 hybrid — intentional dehydration** |
| `components[].model.metadata` | 66 | `json:"metadata"` (no `omitempty`) | inside the G2-E1 block | **2 — serialization artifact** |
| `components[].model.registrant.deleted_at` | 66 | `json:"deleted_at"` (no `omitempty`) | inside the G2-E1 block | **2 — serialization artifact** |
| `…match.{from,to}[].id` | 8 | `json:"id"` (no `omitempty`) | nil-guarded deref | **2 — serialization artifact** |
| **Total** | **599** | | | |

### 1. Required runtime information — **none**

No field in G2-E2 is required by the runtime. The schema types `evaluationQuery`,
`matchStrategyMatrix` and `patch` as non-nullable, but the Go types are all pointers, and every
consumer either nil-checks or supplies a default. The schema's non-nullable typing reflects the
*hydrated* form; the runtime operates on the pointer form and handles nil throughout.

### 2. `evaluationQuery` — 3, ignored by the runtime

Every read site in `meshery`:

- `mesheryctl/internal/cli/root/relationships/view.go:122` — the only live consumer:
  `if _rel.EvaluationQuery != nil { evaluationQuery = *_rel.EvaluationQuery }`. Explicitly
  nil-guarded, and display-only.
- `server/models/pattern/utils/relationship_version_bridge.go:22,47` — copies the pointer
  through unchanged (`EvaluationQuery: src.EvaluationQuery`); nil propagates as nil, no
  dereference.
- `server/handlers/policy_relationship_handler.go:910-920` — the only *enforcing* consumer, and
  **every line is commented out**. Nothing reads it at runtime.

There is no `GetDefaultEvaluationQuery` on the v1beta2 type (it exists only on
`models/v1alpha3/relationship/relationship_helper.go:82`), so no default is silently applied —
the value is simply unused. Our design never sets `evaluationQuery` (0 occurrences in
`design.yml`), so nothing is lost. Shipped designs carry `"evaluationQuery": null` for exactly
this reason.

### 3. `matchStrategyMatrix` — 2, serialization artifact

One read site, `server/policies/eval_rules.go:507`:

```go
func getMatchStrategyForSelector(sel relationship.SelectorItem) [][]string {
    if sel.MatchStrategyMatrix == nil {
        return nil
    }
    return *sel.MatchStrategyMatrix
}
```

The nil case is handled explicitly and its consumer supplies a documented default
(`eval_rules.go:514-520`):

```go
func getStrategyForValueAt(strategies [][]string, index int) []string {
    if index < len(strategies) && strategies[index] != nil {
        return strategies[index]
    }
    return []string{"equal"}
}
```

With `strategies == nil`, `len(strategies) == 0`, so every index falls through to
`[]string{"equal"}`. nil is a defined, supported state with a fixed semantic — not lost
information.

### 4. `patch` — 2, serialization artifact

`RelationshipDefinitionSelectorsPatch *RelationshipDefinitionSelectorsPatch` is a pointer, so
`"patch": null` and an absent `patch` are **the same value in Go** — there is no third state and
no code can distinguish them. Every read site nil-checks first, e.g.
`server/policies/eval_rules.go:476` (`if fromClause…Patch == nil || toClause…Patch == nil { return false }`),
`policy_inventory.go:119`, `policy_alias.go:95,113,229`.

The 60 injected nulls are the 30 no-patch relationships. The gate confirms all **162** real
patch blocks, with `patchStrategy: "replace"`, survive the round trip byte-identically
(`GATE2-REPORT.md` assertion 8). Nothing is lost; the null only makes the wire form disagree
with the schema.

### 5. `capabilities` — intentional dehydration, re-hydrated

`ComponentDefinition.Capabilities` lacks `omitempty` (unlike the relationship-level field, which
has it), so nil re-emits as `null`. But the value is deliberately discarded:
`DehydratePattern` sets `comp.Capabilities = nil` on every save, and `HydratePattern` restores it
from the registry on read. The server also overwrites it on the manifest path
(`meshery_pattern_handler.go:2050-2052`):

```go
comp.Capabilities = wc.Capabilities
if comp.Capabilities == nil {
    comp.Capabilities = models.K8sMeshModelMetadata.Capabilities
}
```

So `capabilities` in a design is a cache the server replaces unconditionally. This also
independently vindicates the Gate 1 fidelity reduction: the 426 catalog capability items omitted
from `generated/design.yml` are exactly what Meshery itself discards on save.

### 6. `model.metadata` and `model.registrant.deleted_at` — 2

Both sit inside the `model` block that `DehydratePattern` deletes, so neither reaches the
persisted document. In the intermediate round trip they are plain null-injections from missing
`omitempty`. Note the server has one **unguarded** dereference,
`meshery_pattern_handler.go:2047` (`comp.Model.Metadata.SvgComplete != nil`), but it operates on
`wc.Model.Metadata` — the registry's model, assigned at line 2035 — not on the design's block.
The guarded site, `server/helpers/utils/utils.go:243` (`if comp.Model.Metadata != nil`), is the
one that reads design-supplied metadata. Omitting `model.metadata`, as Gate 1 required, is
therefore safe on both paths.

### 7. `match[].id` — 2, serialization artifact

`MatchSelectorItem.ID *core.Uuid` is tagged `json:"id"` without `omitempty`, so the 8 stripped
nulls (the 2 `permission` relationships' `match` blocks) return as `"id": null`. This is
required: `id` is a required string in the schema, so an explicit `null` is the only way the Go
struct can express "matches any component". No consumer dereferences it unguarded.

---

## Final classification

### Strict schema failure

**G2-E1: 396 findings.** The round-tripped document fails Draft-07 validation on four required
model fields the Go structs cannot emit, and on three struct-emitted names the schema forbids.
Real, reproducible, and upstream. Persisted-document impact: 0 findings from the contradiction
itself, 66 from the intended dehydrated form.

**G2-E2: 599 findings.** The round-tripped document fails on nil values injected by Go fields
without `omitempty`. Real and reproducible, but a representation mismatch, not a content defect.

Both are genuine strict schema failures. `GATE2-REPORT.md` reports `FAIL` and is not amended.

### Known upstream contradiction

G2-E1 only. The bidirectional schema/struct disagreement in `ModelDefinition`, including the
`RegistrantId` → `json:"connection_id"` tag error, reproduced on a Meshery-shipped design and
visible in already-released catalog data.

### Artifact data / topology loss

**One item, cosmetic.** `component.styles.data` on 22 components. The Go `ComponentStyles` struct
has no `data` field, so it is dropped. The catalog value is `{"label": ""}` — an empty UI label
override with no content. This is the **only** authored content lost across
`Unmarshal → DehydratePattern → Marshal`.

Everything else survives identically, verified field by field on the persisted document:

```
PASS counts 66/111                    PASS metadata.isAnnotation identical (26/40)
PASS all 66 component ids present     PASS metadata.isNamespaced identical (35)
PASS component order identical        PASS metadata.published identical
PASS displayName/description          PASS component.styles identical except data (22)
PASS schemaVersion/format/version     PASS modelReference identical (regenerated by ToReference)
PASS status                           PASS all 222 selector id/kind/patch triples identical
PASS 162 patch blocks, patchStrategy=replace
PASS 29 namespace mutatorRef structures
```

**No topology loss.** No component, relationship, selector, patch, namespace assignment, or
metadata flag is lost, reordered, or blanked.

### Serialization-only difference

G2-E2 (599), plus 132 harmless injected keys (`created_at`, `updated_at`) that the schema permits.
These differ between the authored YAML and the re-marshalled JSON purely because of pointer
`omitempty` tags. None carries information.

---

## Notes for the reviewer

1. **Assertion 6 cannot be made to pass** without changing the artifact in a way Gate 1 forbids,
   or changing the upstream schema. It fails for every Meshery design.
2. **G2-E1 and G2-E2 are different in kind.** G2-E1 is a schema/struct contract disagreement; G2-E2
   is pointer-tag laxity. They are numbered separately for that reason and should be filed
   separately upstream.
3. **The schema validates the hydrated form, storage holds the dehydrated form.** This is the
   single upstream issue underlying both, and it is the one worth reporting to the Meshery
   maintainers: applying `design.yaml` to a persisted design is validating the wrong document.
4. Gate 8 remains the gate that settles end-to-end behaviour. It is unrun — `meshery` and
   `metashery` are not installed and nothing listens on `:8081`.

## Reproducing

```sh
cd validation/tools/gate2
GO=/home/dsk/go/pkg/mod/golang.org/toolchain@v0.0.1-go1.26.4.linux-amd64/bin/go

# strict probe (Gate 2 report) — 995 UNEXPECTED
GOTOOLCHAIN=local GOFLAGS=-mod=mod GOPROXY=off $GO run . \
    ../../generated/design.yml /tmp/roundtrip.json
python3 ../gate1.py /tmp/roundtrip.json /tmp/g2reports
python3 assertions.py

# production save path (this document) — G2-E1 falls to 0, G2-E2 persists at 533
GOTOOLCHAIN=local GOFLAGS=-mod=mod $GO run ./persist \
    ../../generated/design.yml /tmp/persisted.json
python3 ../gate1.py /tmp/persisted.json /tmp/persistedreports
```

`../generated/design.yml` and `../tools/gen.py` are unmodified (md5-verified). No file in
`meshery` or `meshery-mcp-server` was written; `meshery` remains clean at `90bac8dc4`.
