# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Use the real, publicly pullable workload images (Meshery, OpenTelemetry Collector, Redis,
  PostgreSQL) instead of the `pause` placeholder, and a real PrometheusRule expression. The stack now
  **runs** — all four workload pods reach `1/1` — not just applies. See ADR-015.

## [1.0.0] - 2026-10-18

First release. The `ai-native-platform` Meshery design: 66 components and 113 relationships across
four namespaces, generated deterministically and verified offline, through a live Meshery server, and
against a live Kubernetes cluster.

### Added

- `ai-native-platform` design: 66 components (40 native, 26 annotation), 113 relationships
  (61 hierarchical, 52 edge), 226 selector entries, 166 patch entries, 31 namespace-membership
  relationships, over 4 referenced models.
- Deterministic generator (`validation/tools/gen.py`); reruns produce a byte-identical artifact.
- Validation tooling and gates:
  - `verify.py` — offline structural and catalog-fidelity checks (28 checks).
  - `gate1.py` — strict Draft-07 schema gate against the shipped Meshery schema.
  - `tests/run_all.sh` — full harness.
- `deploy.sh` — regenerate, validate, deploy to a live cluster, and assert 40/40.
- CI (`.github/workflows/ci.yml`): an artifact-integrity job and a reproduce-from-pinned-catalog job.
- Documentation: `README.md`, `docs/`, `spec/`, and validation reports `GATE1`, `GATE2`, `GATE8`,
  `GATE9`.
- `LICENSE` (Apache-2.0) and `NOTICE`.

### Changed

- Model the OpenTelemetry Collector as a `kubernetes` `Deployment` (was `sumologic`
  `OpenTelemetryCollector`, which the registry does not ship). See ADR-010.
- Use the registered `Section` annotation for environment grouping (was meshery-core `Environment`,
  which the registry never registers).
- `displayName` carries the instance name (the resource `metadata.name`), not the component kind.
- Emit the resolved `configuration.metadata.namespace` on each namespaced component.

### Fixed

- Every component now carries the minimum configuration the Kubernetes API server accepts
  (container images, Service ports, PVC storage, Ingress rules, admission-policy and rule fields), so
  the design deploys **40/40 with zero failures** (was 34/40). See ADR-015 and `GATE9-REPORT.md`.
- Added the missing namespace-membership links for the two `PodDisruptionBudget`s.
- Corrected the `styles.svg*` fidelity figure in `GATE1-REPORT.md` (109 fields, not 106).

### Known limitations

- Sizing and policy values (ports, PVC storage, the Postgres password, alert thresholds) are
  placeholders; replace them for a production deploy.
- The two `NetworkPolicy` objects land in `default` (the catalog marks `NetworkPolicy`
  `isNamespaced: false`).
- The Meshery Playground sandbox cannot deploy (shared read-only service account); deploy to your own
  cluster instead.

[1.0.0]: https://github.com/dsk-dev-ai/meshery-designs/releases/tag/v1.0.0
