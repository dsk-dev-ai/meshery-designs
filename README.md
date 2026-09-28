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
- 111 relationships
- 222 selector entries
- 162 patch entries
- 29 namespace mutator relationships
- 5 referenced models

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
validation/   Validation gates and reproducible tooling
docs/         User-facing documentation