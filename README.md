# Meshery Designs — AI-Native Platform

Research, architecture, generation, and validation of an AI-native
platform design for Meshery.

## Project

This repository contains the `ai-native-platform` Meshery design,
the architectural research behind it, a deterministic generator,
and reproducible validation reports.

The repository is independent from the upstream Meshery source
repositories.

## Design

The current design contains:

- 66 components
- 40 native components
- 26 annotation components
- 113 relationships
- 226 selector entries
- 166 patch entries
- 31 namespace mutator relationships
- 4 referenced models (`kubernetes`, `meshery-core`, `meshery-operator`, `kube-prometheus-stack`)

The design uses four namespaces:

- `ns-ai-control`
- `ns-ai-runtime`
- `ns-ai-state`
- `ns-ai-observability`

## Repository Structure

```text
generated/     Generated Meshery design artifact
spec/          Architecture, components, relationships and decisions
reports/       Research and reconnaissance
validation/    Validation gates and reproducible tooling
docs/          User-facing documentation
tests/         Reproducibility and harness tests
```

## Tests

Run the comprehensive validation tests:

```bash
bash tests/run_all.sh
```

Or run individual tests:

```bash
for f in tests/test_*.py; do python3 $f; done
```

## Deploy

The design deploys to a live Kubernetes cluster: **40/40 components apply with zero failures** on a
`kind` cluster running the design's native CRDs. See `validation/GATE9-REPORT.md` for the evidence.

```bash
bash deploy.sh
```

`deploy.sh` regenerates the artifact, runs every offline gate, deploys through a local Meshery
server, and asserts the 40/40 result. `docs/QUICKSTART.md` walks through the same flow.

> The component configurations are admission-valid **placeholders** (pause image, default ports,
> 1Gi PVCs, inert policy/rule) so the artifact applies in any cluster. See ADR-015.
