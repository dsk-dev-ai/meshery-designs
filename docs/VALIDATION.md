# Validation

The repository uses multiple validation gates to verify the generated Meshery design.

## Gate 1 — Structural Validation

**PASS**

Gate 1 validates the generated artifact against Meshery catalog and schema expectations.

Key checks include:

- 66 components
- 111 relationships
- catalog resolution
- selector integrity
- relationship patch integrity
- known upstream schema exceptions
- unexpected exception detection

Report:

`validation/GATE1-REPORT.md`

## Gate 2 — Strict Revalidation

**FAIL with documented upstream exceptions**

Gate 2 performs deeper round-trip and schema analysis.

The primary issue is an upstream contradiction between the ModelDefinition schema and the corresponding Go serialization structure.

Reports:

- `validation/GATE2-REPORT.md`
- `validation/GATE2-EXCEPTIONS.md`

## Runtime Persistence Integrity

Meshery intentionally dehydrates parts of a pattern before persistence and hydrates registry-backed data during retrieval.

This explains several strict schema findings that do not represent loss of the authored structural design.

## Gate 8 — Live Meshery Verification

Gate 8 was executed against a locally running Meshery server.

Verified:

- live design import
- persistence
- retrieval
- 66/66 component IDs
- 111/111 relationship IDs
- 222/222 selector entries
- 162/162 patch records
- 29/29 namespace mutator entries

Report:

`validation/GATE8-REPORT.md`

## Gate 8 Scope

Gate 8 verifies import, persistence, retrieval, and deep design integrity.

It does **not** claim:

- full Kubernetes cluster deployment
- production rendering
- production runtime behavior
- production observability behavior
