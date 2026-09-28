# Gate 2 report — Go struct round-trip

Artifact under test: `../generated/design.yml` (unmodified; md5 verified before and after)
Probe: `tools/gate2/` — `meshkit/encoding.Unmarshal` → `design.PatternFile` → `encoding.Marshal`
Assertions: `tools/gate2/assertions.py` (14 checks, extends the plan's six)

## Verdict: **FAIL**

13 of 14 assertions pass. **Assertion 6 fails**: the round-tripped document has **995**
`UNEXPECTED` schema violations. The cause is an upstream contradiction between the shipped
v1beta1/v1beta2 JSON Schema and the shipped Go structs, reproduced below on a design shipped
by Meshery itself. It is not caused by, and cannot be fixed in, this artifact.

| # | Assertion | Result |
|---|---|---|
| 1 | `Unmarshal` succeeds | **PASS** — 66 components, 111 relationships recovered |
| 2 | Counts remain 66 / 111 | **PASS** — `components=66 relationships=111` |
| 3a | Every `component.id` survives unchanged | **PASS** — identical set *and* order |
| 3b | Every `relationship.id` survives unchanged | **PASS** — identical set *and* order |
| 3c | No id blanked or zeroed | **PASS** |
| 4 | Every `selectors[].allow.from\|to[].id` resolves | **PASS** — 222/222 resolve, 0 blanked |
| 4b | Selector id+kind pairs identical to authored | **PASS** — 222 vs 222 |
| 5 | `isAnnotation` survives | **PASS** — 26 `true` / 40 `false`, 0 mismatched |
| 5b | 26 annotation / 40 native preserved | **PASS** |
| 5c | `isNamespaced` survives | **PASS** — 35 namespaced (Gate 8 depends on this) |
| 6 | Round-trip re-validates under Gate 1, 0 `UNEXPECTED` | **FAIL** — `UNEXPECTED=995 KNOWN=162` |
| 6b | `patchStrategy` exception count unchanged | **PASS** — 162, not amplified |
| 7 | Namespace `mutatorRef` structure survives verbatim | **PASS** — 29/29 identical |
| 8 | All 162 patch blocks survive with `patchStrategy: "replace"` | **PASS** — 162 vs 162 |

Assertion 4 — the one the plan calls "exactly the failure the runtime would hide" — **passes**.
The semantic content of the design is fully representable in the Go structs. Counts, ids,
selector wiring, patch blocks, namespace mutators and all boolean flags survive with **zero
value changes**.

## Environment: not blocked

`go1.22.2` is on `PATH`, but both dependencies declare `go 1.26.4`:

- `github.com/meshery/meshkit@v1.0.22/go.mod` → `go 1.26.4`
- `github.com/meshery/schemas@v1.3.37/go.mod` → `go 1.26.4`
- `meshery/go.mod` → `go 1.26.4`

`GOTOOLCHAIN=auto` did not switch, and a bare build fails with
`requires go >= 1.26.4 (running go 1.22.2)`. The required toolchain was **already in the module
cache**, so this is satisfied rather than worked around:

```
/home/dsk/go/pkg/mod/golang.org/toolchain@v0.0.1-go1.26.4.linux-amd64/bin/go
```

With it the probe builds and runs fully offline (`GOPROXY=off`, no downloads, no `go.sum`
mutation of any tracked file). No proxy access was needed and none was used.

## Why assertion 6 fails

### Root cause: `ModelDefinition` is not round-trippable

The component schema `$ref`s `v1beta1/model/model.yaml`, which sets
`additionalProperties: false` and requires 17 fields including `categoryId`, `registrantId`,
`componentsCount` and `relationshipsCount`. The shipped Go struct
(`schemas@v1.3.37/models/v1beta1/model/model.go`) disagrees:

| Field | Schema wants | Go struct emits | Effect |
|---|---|---|---|
| `CategoryId` | `categoryId` (required) | **`json:"-"`** | silently dropped |
| `RegistrantId` | `registrantId` (required) | **`json:"connection_id"`** | mis-tagged upstream |
| `ComponentsCount` | `componentsCount` (required) | `components_count` | rejected by `additionalProperties: false` |
| `RelationshipsCount` | `relationshipsCount` (required) | `relationships_count` | rejected by `additionalProperties: false` |
| `Category` | `metadata` (required) | no such field | dropped |

`RegistrantId` carrying the tag `json:"connection_id"` is a copy-paste error in the upstream
struct. The result is that the four fields the schema *requires* are exactly the four the
runtime *cannot emit*, while the three it does emit under wrong names are exactly the ones the
schema *forbids*. **396** of the 995 violations come from this single block (66 components ×
6 findings).

### The other 599 are injected nulls

Go struct fields lacking `omitempty` are re-emitted as explicit `null` on pointers that are nil:

| Injected key | Count | Violation |
|---|---|---|
| `relationships[].evaluationQuery` | 111 | `None is not of type 'string'` |
| `…allow.from[].matchStrategyMatrix` | 111 | `None is not of type 'array'` |
| `…allow.to[].matchStrategyMatrix` | 111 | `None is not of type 'array'` |
| `components[].capabilities` | 66 | `None is not of type 'array'` |
| `components[].model.metadata` | 66 | `None is not of type 'object'` |
| `components[].model.registrant.deleted_at` | 66 | `None is not of type 'string'` |
| `…allow.from[].patch` | 30 | `None is not of type 'object'` |
| `…allow.to[].patch` | 30 | `None is not of type 'object'` |
| `…match.from[].id`, `…match.to[].id` | 4 | `None is not of type 'string'` |

The 60 `patch: null` findings are the 30 no-patch relationships. The Go struct cannot
distinguish "no patch" from "patch is null", and the schema's `patch` is a non-nullable `$ref`.

### Control experiment: this is upstream, not ours

A design **shipped by Meshery** (`meshery/docs/data/catalog/00fadfee-…/0.0.1/design.yml`,
12 components) was round-tripped through the identical probe and produced the identical
`ModelDefinition` findings:

```
UNEXPECTED components/0/model :: 'categoryId' is a required property
UNEXPECTED components/0/model :: 'componentsCount' is a required property
UNEXPECTED components/0/model :: 'registrantId' is a required property
UNEXPECTED components/0/model :: 'relationshipsCount' is a required property
UNEXPECTED components/0/model :: Additional properties are not allowed
        ('components_count', 'connection_id', 'relationships_count' were unexpected)
UNEXPECTED components/0/model/category :: 'metadata' is a required property
```

So assertion 6 is **unsatisfiable for any Meshery design**, including the project's own. The
`patchStrategy` exception documented in Gate 1 is the only defect the plan authorised; this is a
second, larger, and structurally different one, so the gate is reported FAIL rather than
absorbed into the existing exception.

The control also shows a related edge case that does not affect this design: a design with zero
relationships round-trips to `relationships: null`, which is schema-invalid
(`relationships` has no `omitempty` and the schema requires an array). Our 111 relationships
avoid this.

## Information lost during unmarshal/remarshal

```
DROPPED keys (in design.yml, absent after round trip)   352
INJECTED keys (added by the Go structs)                  929
CHANGED values                                             0
```

**Dropped**

| Path | Count | Significance |
|---|---|---|
| `components[].model.categoryId` | 66 | schema-**required**; drives model categorisation |
| `components[].model.registrantId` | 66 | schema-**required**; lost, reappears as `connection_id` |
| `components[].model.componentsCount` | 66 | schema-**required** |
| `components[].model.relationshipsCount` | 66 | schema-**required** |
| `components[].model.category.metadata` | 66 | schema-**required** |
| `components[].styles.data` | 22 | cosmetic; the catalog value is `{"label": ""}` |

**Injected** — 929 keys, 595 of which are schema violations and 334 harmless
(`components[].created_at` and `updated_at`, 132, are permitted by the schema). None of the
injected keys overwrite authored data; they are all absent-in / null-out artefacts.

**Assessment.** Nothing semantically load-bearing was lost. Every id, every one of the 222
selector wirings, all 162 patch blocks including `patchStrategy: "replace"`, all 29 namespace
`mutatorRef` structures, and all `isAnnotation` / `isNamespaced` flags survive byte-identically.
The loss is confined to four schema-required model identity fields per component plus one
cosmetic key — the fields the Go structs cannot represent, which is precisely the schema-permitted-
but-struct-unrepresentable class the gate exists to detect.

## Open question for Gate 8

Whether this matters in production depends on whether the Meshery server persists the
re-marshalled struct or the original request bytes. If it re-serialises `PatternFile`, then
every design with a `model` block loses its `categoryId`/`registrantId` and gains three
schema-forbidden snake_case keys — which would affect the 361 shipped designs equally, and
makes that look like an upstream bug rather than a property of this design. Gate 8 (server load
and render) is the gate that settles it and has not been run: `meshery` and `metashery` are
not installed and nothing is listening on `:8081`.

## Reproducing

```sh
cd validation/tools/gate2
GO=/home/dsk/go/pkg/mod/golang.org/toolchain@v0.0.1-go1.26.4.linux-amd64/bin/go
GOTOOLCHAIN=local GOFLAGS=-mod=mod GOPROXY=off $GO run . \
    ../../generated/design.yml /tmp/roundtrip.json
#   unmarshal OK / components 66 / relationships 111

cd .. && python3 gate1.py /tmp/roundtrip.json /tmp/g2reports   # 995 UNEXPECTED
python3 gate2/assertions.py                                     # 14 assertions
```

`../generated/design.yml` is read-only in this gate; its md5 was verified identical before and
after. `../tools/gen.py` is unmodified. No file in `meshery` or `meshery-mcp-server` was
touched; `meshery` remains clean at `90bac8dc4`.
