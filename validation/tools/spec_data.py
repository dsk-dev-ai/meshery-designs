"""Authoritative tables transcribed from the six frozen specifications.

Sources:
  COMPONENT_INVENTORY.md  -> COMPONENTS
  RELATIONSHIP_MATRIX.md  -> EDGES
  ARCHITECTURAL_DECISIONS.md / UNSUPPORTED_CONCEPTS.md -> DESCRIPTIONS

Nothing here is invented: every (model, kind) pair is the catalog pair named in
COMPONENT_INVENTORY.md, and every edge is a row of RELATIONSHIP_MATRIX.md.
"""

# (name, model_dir, kind, isAnnotation, description)
# isAnnotation True/False is the value the design uses. Only `env-production`
# differs from its catalog default (documented override in COMPONENT_INVENTORY.md
# "The one deliberate override of an upstream value").

K8S = "kubernetes"
CORE = "meshery-core"
OPER = "meshery-operator"
PROM = "kube-prometheus-stack"
SUMO = "sumologic"

_N = False
_A = True

COMPONENTS = [
    # ---- Group 1: namespaces and scoping
    ("ns-ai-control", K8S, "Namespace", _N,
     "Isolated namespace holding the Meshery control plane, its broker, its GitOps sync, and its ingress."),
    ("ns-ai-runtime", K8S, "Namespace", _N,
     "Holds the runtime configuration contract and the quota and limit objects that govern runtime workloads."),
    ("ns-ai-state", K8S, "Namespace", _N,
     "Holds both stateful stores, their Services, their PersistentVolumeClaims, and their credentials."),
    ("ns-ai-observability", K8S, "Namespace", _N,
     "Holds the OpenTelemetry Collector and the full Prometheus Operator CRD set."),
    ("env-production", CORE, "Environment", _A,
     "Declares the target environment for the whole design. The only component whose isAnnotation "
     "differs from its catalog default (catalog says false; this design sets true because an Environment "
     "is a Meshery-level statement, not a deployable resource)."),
    # ---- Group 2: control plane (layer 6)
    ("meshsync", OPER, "MeshSync", _N,
     "GitOps synchronisation resource - reconciles desired design state against the cluster."),
    ("broker", OPER, "Broker", _N,
     "Declares the message-broker endpoint the operator components talk to."),
    ("deploy-meshery-control", K8S, "Deployment", _N,
     "The workload slot for the Meshery control-plane server. Configuration is deliberately minimal; "
     "image selection happens at deploy time."),
    ("svc-meshery-control", K8S, "Service", _N,
     "Cluster-internal endpoint for the control-plane server."),
    ("ingress-ai-platform", K8S, "Ingress", _N,
     "North-south entry point terminating external access to the control plane."),
    ("meshery-control-plane", CORE, "GenericNode", _A,
     "Architectural node naming the Meshery design-and-control layer as a whole. Annotation: the Meshery "
     "server itself has no model in the catalog."),
    # ---- Group 3: configuration and secrets (layers 5, 8)
    ("cm-agent-runtime", K8S, "ConfigMap", _N,
     "Non-sensitive configuration contract for the agent runtime: timeouts, concurrency limits, grounding "
     "requirements. This is what keeps the agent-runtime annotation from being content-free."),
    ("cm-model-router", K8S, "ConfigMap", _N,
     "Non-sensitive routing policy: tier preference order, fallback triggers, cost and privacy ceilings."),
    ("sec-broker-endpoint", K8S, "Secret", _N,
     "Broker connection credentials for meshsync and broker."),
    ("sec-registry-creds", K8S, "Secret", _N,
     "Credentials for the model registry referenced by layer 5 grounding."),
    ("sec-state-creds", K8S, "Secret", _N,
     "PostgreSQL and Redis credentials, kept in the state namespace so they sit inside the default-deny posture."),
    ("registry-credential", CORE, "Credential", _A,
     "Names the credential that the model registry requires, from the design's point of view. Pairs with the "
     "real sec-registry-creds."),
    # ---- Group 4: state (layer 9)
    ("sts-redis", K8S, "StatefulSet", _N,
     "Session, cache, and agent short-term memory store."),
    ("svc-redis", K8S, "Service", _N,
     "Cluster-internal endpoint for the Redis store."),
    ("pvc-redis", K8S, "PersistentVolumeClaim", _N,
     "Durable volume claim for the Redis store, so session state survives pod replacement."),
    ("sts-postgres", K8S, "StatefulSet", _N,
     "Durable store for grounding artefacts: model registry entries, context records, policy versions."),
    ("svc-postgres", K8S, "Service", _N,
     "Cluster-internal endpoint for the PostgreSQL store."),
    ("pvc-postgres", K8S, "PersistentVolumeClaim", _N,
     "Durable volume claim for the PostgreSQL store, so grounding records survive pod replacement."),
    # ---- Group 5: observability (layer 10)
    ("otel-collector", SUMO, "OpenTelemetryCollector", _N,
     "Receives, processes, and exports traces and metrics from every namespace. Sourced from the sumologic "
     "model, which is the only catalog model providing a real OpenTelemetryCollector."),
    ("prometheus", PROM, "Prometheus", _N,
     "Metrics store and evaluation engine for the platform."),
    ("sm-platform", PROM, "ServiceMonitor", _N,
     "Declares the scrape targets for the control plane and both state stores."),
    ("alertmanager", PROM, "Alertmanager", _N,
     "Routes alerts raised by promrule-platform-slo."),
    ("promrule-platform-slo", PROM, "PrometheusRule", _N,
     "Alerting rules covering fallback-tier exhaustion, store unavailability, and control-plane health."),
    # ---- Group 6: security (layer 11)
    ("sa-ai-control", K8S, "ServiceAccount", _N,
     "Workload identity for the control-plane server, so the pod does not run as the namespace-wide default."),
    ("role-ai-control", K8S, "Role", _N,
     "Least-privilege permissions for the control-plane identity: read designs, read broker config."),
    ("rb-ai-control", K8S, "RoleBinding", _N,
     "Binds role-ai-control to sa-ai-control."),
    ("sa-ai-state", K8S, "ServiceAccount", _N,
     "Workload identity for both stateful stores; the stores must not run as default."),
    ("role-ai-state", K8S, "Role", _N,
     "Least-privilege permissions for the state identity: read only its own Secrets and PVCs."),
    ("rb-ai-state", K8S, "RoleBinding", _N,
     "Binds role-ai-state to sa-ai-state."),
    ("netpol-default-deny", K8S, "NetworkPolicy", _N,
     "Deny-all ingress/egress baseline for the state and control namespaces. The two catalog firewall "
     "blueprints both target Pod, and this design declares no Pod components, so no edge is authored."),
    ("netpol-ai-allowlist", K8S, "NetworkPolicy", _N,
     "Explicit east-west permissions: control plane to stores, collector to workloads, Prometheus to scrape "
     "targets. Without allow-rules, default-deny leaves the platform uncommunicable."),
    ("trust-boundary", CORE, "GenericNode", _A,
     "Names the boundary between the untrusted MCP ingress zone and the trusted platform zone."),
    # ---- Group 7: policy (layer 7)
    ("vap-required-labels", K8S, "ValidatingAdmissionPolicy", _N,
     "Admission policy requiring platform labels on workload resources. Evaluated in-process by the API "
     "server: no webhook, no operator, no external dependency."),
    ("vapb-ai-runtime", K8S, "ValidatingAdmissionPolicyBinding", _N,
     "Binds vap-required-labels to the runtime and state namespaces, leaving the control plane exempt."),
    ("quota-ai-runtime", K8S, "ResourceQuota", _N,
     "Caps total CPU, memory, and pod count in the runtime namespace, so a runaway agent loop cannot "
     "exhaust the cluster."),
    ("limits-ai-runtime", K8S, "LimitRange", _N,
     "Supplies default CPU/memory requests and limits for containers lacking them, so pods are shaped "
     "before quota judges them."),
    ("policy-boundary", CORE, "GenericNode", _A,
     "The architectural choke point where a request is checked before any model tier is contacted."),
    ("grounding-validator", CORE, "GenericNode", _A,
     "Checks that a request is answerable from registered, permitted context before it reaches a tier, so the "
     "fallback ladder cannot become an accidental bypass."),
    # ---- Group 8: resilience (layer 12)
    ("pdb-sts-redis", K8S, "PodDisruptionBudget", _N,
     "Prevents voluntary eviction of Redis below its quorum during node drains and upgrades."),
    ("pdb-sts-postgres", K8S, "PodDisruptionBudget", _N,
     "Prevents voluntary eviction of PostgreSQL below its quorum."),
    ("pc-ai-critical", K8S, "PriorityClass", _N,
     "Marks control-plane and state workloads as high-priority during contention, so graceful degradation is "
     "meaningful: the surviving tiers win scheduling."),
    ("degradation-controller", CORE, "GenericNode", _A,
     "Defines the behaviour of the platform when tiers 1 and 2 are unavailable. This is a policy about "
     "behaviour under failure, which Kubernetes primitives cannot express."),
    # ---- Group 10: AI-native core (layers 1-5), all annotation
    ("mcp-access-gateway", CORE, "GenericNode", _A,
     "The single entry point through which Model Context Protocol clients reach platform capabilities. "
     "meshery-mcp-server contains no source, no go.mod, no manifests and no image, so no deployable artifact "
     "is claimed here."),
    ("agent-runtime", CORE, "GenericNode", _A,
     "Executes agent loops: plan, retrieve context, call tools, assemble responses. Its configuration "
     "contract is real (cm-agent-runtime)."),
    ("agent-tool-bridge", CORE, "GenericNode", _A,
     "The agent's egress path to external tools and data sources, kept separate so tool egress can be "
     "restricted independently of agent compute."),
    ("model-router", CORE, "GenericNode", _A,
     "Selects which model tier serves a given request, based on policy, cost, privacy, and capacity. Its "
     "policy is real (cm-model-router)."),
    ("tier-cloud-managed", CORE, "GenericNode", _A,
     "Requests served by externally hosted, managed model endpoints. Highest capability, but network-dependent, "
     "cost-bearing, and a data-egress risk."),
    ("tier-local-hosted", CORE, "GenericNode", _A,
     "Requests served by model endpoints hosted inside the platform trust boundary. The privacy-preserving "
     "tier."),
    ("tier-offline-cached", CORE, "GenericNode", _A,
     "Requests answered from locally cached artefacts with no external call. The floor of the ladder: this is "
     "the tier that keeps the platform answering when the network is gone."),
    ("context-store", CORE, "GenericNode", _A,
     "Holds assembled, retrievable context for agent grounding. The durable half is real (sts-postgres)."),
    ("model-registry", CORE, "GenericNode", _A,
     "The authoritative list of model identities the platform may use, with their grounding metadata. Prevents "
     "the router from selecting an unregistered model."),
    # ---- Group 11: layer bands and commentary
    ("sec-L1-mcp-access", CORE, "Section", _A,
     "Layer 1 band - MCP access. Contains mcp-access-gateway."),
    ("sec-L2-agent-runtime", CORE, "Section", _A,
     "Layer 2 band - agent runtime. Contains agent-runtime and agent-tool-bridge."),
    ("sec-L34-routing-fallback", CORE, "Section", _A,
     "Layers 3-4 band - routing and fallback. Contains model-router and the three fallback tiers."),
    ("sec-L5-grounding", CORE, "Section", _A,
     "Layer 5 band - context and registry grounding. Contains context-store, model-registry, registry-credential."),
    ("sec-L6-control-plane", CORE, "Section", _A,
     "Layer 6 band - Meshery design and control. Contains meshery-control-plane, meshsync, broker."),
    ("sec-L7-policy-boundary", CORE, "Section", _A,
     "Layer 7 band - validation and policy. Contains policy-boundary, grounding-validator, quota-ai-runtime, "
     "limits-ai-runtime."),
    ("sec-L11-security", CORE, "Section", _A,
     "Layer 11 band - security boundaries. Contains trust-boundary, netpol-default-deny, netpol-ai-allowlist."),
    ("sec-L12-degradation", CORE, "Section", _A,
     "Layer 12 band - resilience and degradation. Contains degradation-controller, pdb-sts-redis, "
     "pdb-sts-postgres."),
    ("note-annotation-vs-infrastructure", CORE, "Comment", _A,
     "Annotation components describe intent and are not deployable. Only components with "
     "metadata.isAnnotation=false produce cluster resources."),
    ("note-deferred-ai-workloads", CORE, "Comment", _A,
     "Layers 1-5 have no native components and must not be given fabricated Deployments until an "
     "implementation exists. Do not invent a workload to make a layer look deployed."),
]

# ---------------------------------------------------------------------------
# Relationship blueprints, resolved at the pinned model versions.
# `basis` is the real catalog file the edge is instantiated from. For the five
# hand-authored edges, `basis` is the closest real blueprint whose selector shape
# is copied (RELATIONSHIP_MATRIX.md sections 3 and 6).
# ---------------------------------------------------------------------------
BLUEPRINTS = {
    "kmjea":     "kubernetes/v1.37.1/v1.0.0/relationships/hierarchical-parent-inventory-kmjea.json",
    "tagsets":   "kubernetes/v1.37.1/v1.0.0/relationships/sibling-tagsets.json",
    "duixv":     "kubernetes/v1.37.1/v1.0.0/relationships/edge-non-binding-network-duixv.json",
    "jccsr":     "kubernetes/v1.37.1/v1.0.0/relationships/edge-non-binding-network-jccsr.json",
    "rcycs":     "kubernetes/v1.37.1/v1.0.0/relationships/edge-non-binding-reference-rcycs.json",
    "pfnyn":     "kubernetes/v1.37.1/v1.0.0/relationships/hierarchical-parent-inventory-pfnyn.json",
    "secretdep": "kubernetes/v1.37.1/v1.0.0/relationships/reference-secret-to-deployment.json",
    "keceb":     "kubernetes/v1.37.1/v1.0.0/relationships/edge-non-binding-reference-keceb.json",
    "xtrmo":     "kubernetes/v1.37.1/v1.0.0/relationships/edge-non-binding-reference-xtrmo.json",
    "stsp":      "kubernetes/v1.37.1/v1.0.0/relationships/edge-non-binding-reference-statefulset.json",
    "ecilr":     "kubernetes/v1.37.1/v1.0.0/relationships/edge-binding-reference-ecilr.json",
    "homji":     "kubernetes/v1.37.1/v1.0.0/relationships/edge-binding-permission-homji.json",
    "iicqa":     "kubernetes/v1.37.1/v1.0.0/relationships/hierarchical-parent-alias-iicqa.json",
    "fmlwc":     "kube-prometheus-stack/89.2.2/v1.0.0/relationships/edge-sibling-matchlabels-fmlwc.json",
    "qvwox":     "kube-prometheus-stack/89.2.2/v1.0.0/relationships/edge-sibling-matchlabels-qvwox.json",
    "cunlc":     "kube-prometheus-stack/89.2.2/v1.0.0/relationships/edge-sibling-matchlabels-cunlc.json",
}

# (src, dst, basis, isAnnotation, provenance, spec_ref)
EDGES = []


def _e(src, dst, basis, ann, prov, ref):
    EDGES.append((src, dst, basis, ann, prov, ref))


# ---- Section 1: namespace membership, 29 edges, provenance B
_INV = "ns-ai-control"
for _s in ["meshsync", "broker", "deploy-meshery-control", "svc-meshery-control",
           "ingress-ai-platform", "sec-broker-endpoint", "sec-registry-creds",
           "sa-ai-control", "role-ai-control", "rb-ai-control"]:
    _e(_s, _INV, "kmjea", False, "B", "RELATIONSHIP_MATRIX.md#1")
for _s in ["cm-agent-runtime", "cm-model-router", "quota-ai-runtime", "limits-ai-runtime"]:
    _e(_s, "ns-ai-runtime", "kmjea", False, "B", "RELATIONSHIP_MATRIX.md#1")
for _s in ["sts-redis", "svc-redis", "pvc-redis", "sts-postgres", "svc-postgres",
           "pvc-postgres", "sec-state-creds", "sa-ai-state", "role-ai-state", "rb-ai-state"]:
    _e(_s, "ns-ai-state", "kmjea", False, "B", "RELATIONSHIP_MATRIX.md#1")
for _s in ["otel-collector", "prometheus", "sm-platform", "alertmanager", "promrule-platform-slo"]:
    _e(_s, "ns-ai-observability", "kmjea", False, "B", "RELATIONSHIP_MATRIX.md#1")

# ---- Section 2: label grouping, 3 edges, provenance B, patch-free blueprint
_e("sts-redis", "sts-postgres", "tagsets", False, "B", "RELATIONSHIP_MATRIX.md#2")
_e("prometheus", "sm-platform", "tagsets", False, "B", "RELATIONSHIP_MATRIX.md#2")
_e("netpol-default-deny", "netpol-ai-allowlist", "tagsets", False, "B", "RELATIONSHIP_MATRIX.md#2")

# ---- Section 3: network reachability, 4 edges (2 provenance B, 2 provenance H)
_e("svc-meshery-control", "deploy-meshery-control", "duixv", False, "B", "RELATIONSHIP_MATRIX.md#3")   # C1
_e("ingress-ai-platform", "svc-meshery-control", "jccsr", False, "B", "RELATIONSHIP_MATRIX.md#3")     # C2
_e("svc-redis", "sts-redis", "duixv", False, "H", "RELATIONSHIP_MATRIX.md#3")                         # C3
_e("svc-postgres", "sts-postgres", "duixv", False, "H", "RELATIONSHIP_MATRIX.md#3")                    # C4

# ---- Section 4: reference bindings, 18 edges, provenance B
_e("pvc-redis", "sts-redis", "rcycs", False, "B", "RELATIONSHIP_MATRIX.md#4.1")                       # D1
_e("pvc-postgres", "sts-postgres", "rcycs", False, "B", "RELATIONSHIP_MATRIX.md#4.1")                  # D2
_e("cm-agent-runtime", "deploy-meshery-control", "pfnyn", False, "B", "RELATIONSHIP_MATRIX.md#4.2")    # D3
_e("cm-model-router", "deploy-meshery-control", "pfnyn", False, "B", "RELATIONSHIP_MATRIX.md#4.2")     # D4
_e("sec-broker-endpoint", "deploy-meshery-control", "secretdep", False, "B", "RELATIONSHIP_MATRIX.md#4.2")  # D5
_e("sec-registry-creds", "deploy-meshery-control", "secretdep", False, "B", "RELATIONSHIP_MATRIX.md#4.2")   # D6
_e("rb-ai-control", "role-ai-control", "keceb", False, "B", "RELATIONSHIP_MATRIX.md#4.3")             # D7
_e("rb-ai-state", "role-ai-state", "keceb", False, "B", "RELATIONSHIP_MATRIX.md#4.3")                 # D8
_e("pdb-sts-redis", "sts-redis", "xtrmo", False, "B", "RELATIONSHIP_MATRIX.md#4.4")                   # D9
_e("pdb-sts-postgres", "sts-postgres", "xtrmo", False, "B", "RELATIONSHIP_MATRIX.md#4.4")              # D10
_e("pc-ai-critical", "sts-redis", "stsp", False, "B", "RELATIONSHIP_MATRIX.md#4.4")                   # D11
_e("pc-ai-critical", "sts-postgres", "stsp", False, "B", "RELATIONSHIP_MATRIX.md#4.4")                # D12
_e("vap-required-labels", "vapb-ai-runtime", "ecilr", False, "B", "RELATIONSHIP_MATRIX.md#4.5")       # D13
_e("prometheus", "sm-platform", "fmlwc", False, "B", "RELATIONSHIP_MATRIX.md#4.6")                    # D14
_e("sm-platform", "svc-meshery-control", "qvwox", False, "B", "RELATIONSHIP_MATRIX.md#4.6")           # D15
_e("sm-platform", "svc-redis", "qvwox", False, "B", "RELATIONSHIP_MATRIX.md#4.6")                    # D16
_e("sm-platform", "svc-postgres", "qvwox", False, "B", "RELATIONSHIP_MATRIX.md#4.6")                 # D17
_e("prometheus", "promrule-platform-slo", "cunlc", False, "B", "RELATIONSHIP_MATRIX.md#4.6")          # D18

# ---- Section 5: permission binding, 2 edges, provenance B, patch-free blueprint
_e("role-ai-control", "sa-ai-control", "homji", False, "B", "RELATIONSHIP_MATRIX.md#5")               # E1
_e("role-ai-state", "sa-ai-state", "homji", False, "B", "RELATIONSHIP_MATRIX.md#5")                   # E2

# ---- Section 6: hand-authored semantic edges, 3 edges, provenance H
_e("sec-state-creds", "sts-postgres", "secretdep", False, "H", "RELATIONSHIP_MATRIX.md#6")             # F1
_e("sec-state-creds", "sts-redis", "secretdep", False, "H", "RELATIONSHIP_MATRIX.md#6")                # F2
_e("prometheus", "alertmanager", "fmlwc", False, "H", "RELATIONSHIP_MATRIX.md#6")                    # F3

# ---- Section 7: Section containment, 23 edges, provenance C
_BANDS = [
    ("sec-L1-mcp-access", ["mcp-access-gateway"]),
    ("sec-L2-agent-runtime", ["agent-runtime", "agent-tool-bridge"]),
    ("sec-L34-routing-fallback", ["model-router", "tier-cloud-managed",
                                  "tier-local-hosted", "tier-offline-cached"]),
    ("sec-L5-grounding", ["context-store", "model-registry", "registry-credential"]),
    ("sec-L6-control-plane", ["meshery-control-plane", "meshsync", "broker"]),
    ("sec-L7-policy-boundary", ["policy-boundary", "grounding-validator",
                                "quota-ai-runtime", "limits-ai-runtime"]),
    ("sec-L11-security", ["trust-boundary", "netpol-default-deny", "netpol-ai-allowlist"]),
    ("sec-L12-degradation", ["degradation-controller", "pdb-sts-redis", "pdb-sts-postgres"]),
]
for _band, _members in _BANDS:
    for _m in _members:
        _e(_band, _m, "iicqa", True, "C", "RELATIONSHIP_MATRIX.md#7")

# ---- Section 8: AI-native semantic chain, 16 edges, provenance H
_CHAIN = [
    ("mcp-access-gateway", "agent-runtime"),
    ("agent-runtime", "agent-tool-bridge"),
    ("agent-runtime", "context-store"),
    ("agent-runtime", "model-router"),
    ("model-router", "tier-cloud-managed"),
    ("model-router", "tier-local-hosted"),
    ("model-router", "tier-offline-cached"),
    ("model-router", "model-registry"),
    ("model-router", "grounding-validator"),
    ("model-registry", "registry-credential"),
    ("registry-credential", "sec-registry-creds"),
    ("grounding-validator", "context-store"),
    ("grounding-validator", "model-registry"),
    ("grounding-validator", "policy-boundary"),
    ("tier-offline-cached", "context-store"),
    ("degradation-controller", "model-router"),
]
for _s, _d in _CHAIN:
    _e(_s, _d, None, True, "H", "RELATIONSHIP_MATRIX.md#8")

# ---- Section 9: annotation-to-native correspondence, 9 edges, provenance A
_CORR = [
    ("meshery-control-plane", "meshsync"),
    ("meshery-control-plane", "broker"),
    ("meshery-control-plane", "deploy-meshery-control"),
    ("context-store", "sts-postgres"),
    ("model-registry", "sec-registry-creds"),
    ("trust-boundary", "ingress-ai-platform"),
    ("policy-boundary", "vap-required-labels"),
    ("degradation-controller", "promrule-platform-slo"),
    ("otel-collector", "prometheus"),
]
for _s, _d in _CORR:
    _e(_s, _d, None, True, "A", "RELATIONSHIP_MATRIX.md#9")

# ---- Section 10: environment scoping, 4 edges, provenance C
for _ns in ["ns-ai-control", "ns-ai-runtime", "ns-ai-state", "ns-ai-observability"]:
    _e("env-production", _ns, "iicqa", True, "C", "RELATIONSHIP_MATRIX.md#10")
