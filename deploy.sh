#!/usr/bin/env bash
#
# deploy.sh — regenerate, validate, and deploy the ai-native-platform design
#             to a live Kubernetes cluster through a local Meshery server.
#
# End to end this reproduces validation/GATE9-REPORT.md: 40 of 40 components
# apply with zero failures.
#
# Usage:
#   bash deploy.sh [CONTEXT_ID]
#
# Environment overrides:
#   MESHERY_URL      Meshery server base URL         (default http://127.0.0.1:9081)
#   MESHERY_CONTEXT  target Meshery context id       (default: first registered context)
#   DESIGN_ID        pattern id sent in the payload  (default: the design's id)
#
set -euo pipefail

cd "$(dirname "$0")"

MESHERY_URL="${MESHERY_URL:-http://127.0.0.1:9081}"
DESIGN="generated/design.yml"
EXPECTED=40

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# --- 1. regenerate ---------------------------------------------------------
log "Regenerating $DESIGN"
python3 validation/tools/gen.py "$DESIGN"
md5sum "$DESIGN"

# --- 2. offline gates ------------------------------------------------------
log "Structural verification (verify.py)"
python3 validation/tools/verify.py "$DESIGN"

log "Strict schema gate (gate1.py)"
tmp_gate1="$(mktemp -d)"
python3 validation/tools/gate1.py "$DESIGN" "$tmp_gate1"
rm -rf "$tmp_gate1"

log "Full harness (tests/run_all.sh)"
bash tests/run_all.sh

# --- 3. reach the Meshery server ------------------------------------------
log "Checking Meshery server at $MESHERY_URL"
curl -fsS -m 30 "$MESHERY_URL/api/system/version" >/dev/null \
  || fail "Meshery server not reachable at $MESHERY_URL (start it with: mesheryctl system start -p docker)"

# --- 4. resolve the target context ----------------------------------------
CONTEXT="${1:-${MESHERY_CONTEXT:-}}"
if [ -z "$CONTEXT" ]; then
  log "Discovering registered Meshery context"
  CONTEXT="$(curl -fsS -m 30 "$MESHERY_URL/api/system/kubernetes/contexts" \
    | python3 -c 'import sys,json
d=json.load(sys.stdin)
ctx=d.get("contexts", d) if isinstance(d,dict) else d
ctx=ctx if isinstance(ctx,list) else ctx.get("contexts",[])
print(ctx[0]["id"] if ctx else "")')"
fi
[ -n "$CONTEXT" ] || fail "No Meshery context found. Register a cluster, or pass a context id."
log "Target context: $CONTEXT"

DESIGN_ID="${DESIGN_ID:-$(python3 -c 'import re,sys; print(re.search(r"^id:\s*(\S+)", open(sys.argv[1]).read(), re.M).group(1))' "$DESIGN")}"

# --- 5. clean any previous run of this design -----------------------------
# PVC specs are immutable, so a re-apply over an existing run fails on
# pvc-redis/pvc-postgres. A clean apply is the acceptance scenario for Gate 9.
# Set KEEP=1 to deploy on top of whatever is already there.
if [ "${KEEP:-0}" != "1" ]; then
  log "Cleaning previous run of this design (set KEEP=1 to skip)"
  kubectl delete ns ns-ai-control ns-ai-runtime ns-ai-state ns-ai-observability \
    --ignore-not-found --wait=true >/dev/null 2>&1 || true
  kubectl -n default delete netpol netpol-ai-allowlist netpol-default-deny \
    --ignore-not-found >/dev/null 2>&1 || true
  kubectl delete priorityclass pc-ai-critical --ignore-not-found >/dev/null 2>&1 || true
  kubectl delete validatingadmissionpolicybinding vapb-ai-runtime --ignore-not-found >/dev/null 2>&1 || true
  kubectl delete validatingadmissionpolicy vap-required-labels --ignore-not-found >/dev/null 2>&1 || true
fi

# --- 6. build the deploy payload ------------------------------------------
payload="$(mktemp)"
python3 - "$DESIGN" "$DESIGN_ID" >"$payload" <<'PY'
import json, sys
design = open(sys.argv[1]).read()
json.dump({"patternFile": design, "patternID": sys.argv[2]}, sys.stdout)
PY

# --- 7. deploy -------------------------------------------------------------
log "Deploying to context $CONTEXT (this can take ~1 minute)"
result="$(mktemp)"
curl -fsS -m 900 -X POST \
  "$MESHERY_URL/api/pattern/deploy?contexts=$CONTEXT" \
  -H 'Content-Type: application/json' \
  --data @"$payload" -o "$result"
rm -f "$payload"

# --- 8. assert -------------------------------------------------------------
log "Result"
python3 - "$result" "$EXPECTED" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
expected = int(sys.argv[2])
ok, bad = set(), {}
for _, entries in data.items():
    for e in entries:
        for s in e.get("Summary", []):
            key = (s.get("CompName"), s.get("Kind"))
            if s.get("Success"):
                ok.add(key)
            else:
                bad[key] = str(s.get("Error"))[:300]
print(f"applied : {len(ok)} unique components")
print(f"failed  : {len(bad)} unique components")
for (name, kind), err in sorted(bad.items()):
    print(f"   FAIL {name} ({kind}): {err}")
if len(ok) != expected or bad:
    sys.exit(1)
print(f"PASS: {expected}/{expected} components applied with zero failures.")
PY

log "Applied inventory"
kubectl get ns 2>/dev/null | grep ns-ai || true
kubectl -n ns-ai-control get deploy,svc,ingress 2>/dev/null || true
kubectl -n ns-ai-state get sts,pvc,svc 2>/dev/null || true
kubectl -n ns-ai-observability get prometheus,alertmanager,servicemonitor 2>/dev/null || true

log "Done. See validation/GATE9-REPORT.md for the recorded evidence."
