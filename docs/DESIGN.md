# Design

## AI-Native Platform

The `ai-native-platform` design represents an AI-native platform topology modeled as a Meshery design.

The design is organized into four logical namespaces:

- `ns-ai-control`
- `ns-ai-runtime`
- `ns-ai-state`
- `ns-ai-observability`

## Design Composition

| Element | Count |
|---|---:|
| Components | 66 |
| Native components | 40 |
| Annotation components | 26 |
| Relationships | 111 |
| Selector entries | 222 |
| Patch entries | 162 |
| Namespace mutator relationships | 29 |
| Models | 5 |

## Models

The design references:

- Kubernetes `v1.37.1`
- Meshery Core `0.7.2`
- Meshery Operator `1.0.70`
- kube-prometheus-stack `89.2.2`
- Sumo Logic `4.18.0`

## Namespace Organization

### AI Control

Contains control-plane and orchestration concepts.

### AI Runtime

Contains runtime-oriented AI workloads and supporting services.

### AI State

Contains stateful platform components and persistent storage relationships.

### AI Observability

Contains monitoring and telemetry infrastructure.

## Annotation Components

Some platform concepts do not have directly supported native catalog components.

These are represented using Meshery annotation components rather than inventing unsupported native catalog resources.

Examples include:

- MCP server
- Ollama
- Tempo
- Gateway API
- Grafana

See:

`spec/UNSUPPORTED_CONCEPTS.md`

## Relationships

Relationship provenance is tracked as:

- Blueprint-backed
- Hand-authored
- Containment
- Annotation cross-class

See:

- `spec/RELATIONSHIP_MATRIX.md`

## Design Boundaries

The design deliberately distinguishes between real deployable infrastructure and architectural concepts that
are not currently represented by native Meshery catalog components.

### Represented as annotations

The AI-native concepts in layers 1–5 are represented as `meshery-core` annotations rather than fabricated
Kubernetes workloads. This includes MCP access, the agent runtime, model routing, model tiers, context grounding,
and the model registry.

### Deliberately unsupported or excluded

The design does not claim native support for:

- MCP server implementation
- Ollama or another local LLM runtime
- Tempo trace storage
- Gateway API
- Grafana
- a native AI agent runtime
- a native model router
- a native model-serving endpoint
- request-time grounding enforcement
- automated degradation/fallback execution

These boundaries are documented with evidence and promotion paths in `spec/UNSUPPORTED_CONCEPTS.md`.

### Architectural decisions

Major technology and modeling choices, including the rejection of service meshes, database operators, HPA,
Grafana, Gateway API, and fabricated AI workloads, are recorded in `spec/ARCHITECTURAL_DECISIONS.md`.


## Generated Artifact

The final generated design is:

`generated/design.yml`

The generated artifact should be treated as generated output, not the primary authoring surface.
