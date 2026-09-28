# Gate 1 report — `generated/design.yml`

Artifact: `../generated/design.yml` (244 KB, 66 components, 111 relationships)
Schema: `meshery/schemas@v1.3.37` — `constructs/v1beta3/design/design.yaml`, **unmodified**
Harness: `tools/gate1.py` (bundles external `$ref`s by filesystem path, strips the flattened
upstream `$id` values **in memory only**, runs Draft-07 validation)

## Verdict

```
total findings               162
  KNOWN_UPSTREAM_SCHEMA_EXCEPTION        162
  UNEXPECTED                             0
relationships w/ patch       81 (expect 81)
relationships w/o patch      30 (expect 30)
GATE 1: PASS
```

`tools/verify.py` adds 28 structural and fidelity checks (Gate 1 assertions 1–12 plus the
offline half of Gates 3, 5 and 6): **28 checks, 0 failed**. Full output in
`structural-verification.txt`.

## Exception notice

Strict Draft-07 validation against the shipped Meshery schema fails
for `patchStrategy='replace'`. This is an upstream schema/catalog
inconsistency. The design preserves the catalog value faithfully.
The exception is narrowly scoped and does not relax any other schema
constraint.

All 162 findings are that one enum violation and nothing else. Evidence that this is
upstream, not authored: `replace` appears **10,135** times across **4,845** blueprint files
and **2,762** times across **150** shipped designs, is the only non-null value any catalog
patch uses, and is absent from the enum in all four schema versions despite being
documented in `PatchSet`.

## Other upstream inconsistencies, and how each was resolved

The catalog and the shipped schema disagree in eleven further places. None of these were
turned into exceptions; each was resolved deterministically, and each is schema-forced data
loss rather than a design choice.

| # | Catalog / blueprint | Shipped schema | Resolution | Affected |
|---|---|---|---|---|
| 1 | `displayName` with spaces (e.g. `API Group`) | `InputString` `^[a-zA-Z_][a-zA-Z0-9_-]*[a-zA-Z0-9_]$` | Emitted the component `kind`. Stripping spaces reproduces `kind` **exactly in all 66 cases**; the generator now *raises* if it ever would not. | 22 |
| 2 | `model.metadata.capabilities: null` | typed as an array | `metadata` omitted from the model block (not required). Same information is carried on each component's `styles`. | 5 models |
| 3 | `model.metadata.shape: "circle"` | not in the 25-value `Shape` enum | same as #2 | 5 models |
| 4 | `model.metadata.svgColor: ""` / no `svgWhite` (sumologic) | both `required`, `minLength: 1` | same as #2 | 1 model |
| 5 | `registrant.deleted_at: null` | typed as a string | Null-valued keys dropped | — |
| 6 | `registrant.sub_type` (sumologic only) | requires `subType`, rejects unknown keys | Spelling normalised | 1 model |
| 7 | `match` blocks with `id: null` | typed as a string | Null keys dropped (`null` and absent mean the same here) | 2 relationships |
| 8 | blueprint `model` block with empty `displayName`/`version` | both `minLength: 1` | Reference rebuilt from the catalog `model.json` the blueprint names | all 76 blueprint-backed edges |
| 9 | `styles.shape` `circle` (25), `shield` (4), `right-rhomboid` (1) | 25-value `Shape` enum | `circle`→`ellipse`, `right-rhomboid`→`rhomboid` (exact suffix match), `shield`→`pentagon`. An unmapped shape now raises instead of silently falling back. | 30 |
| 10 | `styles.svg*` full inline SVG, often >10 KB | `maxLength: 500` | Emitted empty when over the cap, matching the shipped reference-design convention. 36 values that fit are kept verbatim. | 106 fields |
| 11 | `subCategory: "App Definition and Development"` (meshery-operator) | not in the 46-value `SubCategory` enum | The schema's own documented default `Uncategorized` | 2 components |

Items 1, 9 and 10 are cosmetic. Items 2–6, 8 and 11 are metadata plumbing. Item 7 is a
selector field, where `null` and absent are semantically identical.

## Fidelity losses — please review

These are the places where catalog data is **not** reproduced in the artifact, and therefore
the places a reviewer should push back if the loss matters:

- **`capabilities` dropped from all 66 components** (426 catalog items). The schema types it
  as an array; the catalog's own component files do not carry the key, and the corresponding
  nested schema rejects the catalog's own capability descriptors. Largest single reduction.
  If the Meshery UI uses `capabilities` to drive per-kind behaviour, this design will render
  less richly than the catalog components.
- **`component.schema` dropped for 42 components** because the catalog value exceeds the
  `ComponentSchema` `maxLength` of 500 (typical size ~3 KB). The other 24 are empty *in the
  catalog* — they are the hand-authored `meshery-core` kinds (`Section`, `GenericNode`,
  `Environment`, `Credential`). Net: 0 of 66 components carry a schema. This matches shipped
  convention, so it is expected to be harmless, but it is total loss.
- **`model.metadata` dropped from all 5 model blocks** (see #2–#4).
- **`styles.svg*` emptied on 106 fields** (see #10); icons will fall back to the UI default.
- **`meshery-operator` components reclassified to `subCategory: Uncategorized`** (see #11).
  The catalog's real value is not lost from the repo — it is in
  `meshery/models/meshery-operator/1.0.70/v1.0.0/model.json` — but the design does not carry it.
- **`shield` rendered as `pentagon`** on 4 components. Nearest 5-sided form; the enum has no
  shield. Affects cosmetics only.

## Preserved

- `patchStrategy: "replace"` — **never** substituted, omitted or altered. Present on 81
  relationships, 162 fields, all `"replace"`.
- The one documented `isAnnotation` override: `Environment` → `true`. Verified to be the only
  deviation from the catalog.
- `component.version`, `component.kind`, `isNamespaced`, `genealogy` — all 66 verified
  byte-equal to the catalog.
- `env-production` as the single isAnnotation override; no synthesised models, versions,
  relationships, `Pod` components, `StorageClass` components, or firewall edges.
- Every `kind`/`type`/`subType` triple is verified to occur in the upstream catalog.
- Provenance split matches `RELATIONSHIP_MATRIX.md`: B=54, H=21, C=27, A=9.

## Gates not executed here

`meshery`, `metashery` and `kubectl` are not installed and no server is listening on
`:8081`, so these remain **unrun** — they are not passes:

- **Gate 2** Go struct round-trip — needs the Meshery server.
- **Gate 4** schema version consistency — partially covered offline (versions are literal);
  the import-side check needs the server.
- **Gate 7** cluster-level assumptions — needs `kubectl`.
- **Gate 8** server load and render, including the post-import component count and the
  namespace assignment on all 35 namespaced components — needs the server. The count of 35
  is confirmed offline; the assignment itself is not.
- **Gate 9** design-intent review — human review, by definition.

## Reproducing

```sh
cd validation/tools
python3 gen.py ../../generated/design.yml        # regenerate the artifact
python3 gate1.py ../../generated/design.yml ..   # strict + normalized reports
python3 verify.py ../../generated/design.yml      # 28 structural/fidelity checks
```

`gen.py` reads the catalog at the pinned model versions
(`kubernetes` v1.37.1, `meshery-core` 0.7.2, `meshery-operator` 1.0.70,
`kube-prometheus-stack` 89.2.2, `sumologic` 4.18.0) from
`/home/dsk/opensource_new_programs/meshery/models`. Component and relationship ids are
deterministic UUID5 values, so regeneration is byte-stable. The generator is the authority
for the artifact: `design.yml` must not be hand-edited.
