# Playing with Meshery

Hands-on exercise against a **live Meshery server** using the `ai-native-platform`
design. This is the evidence trail for step #6 of the roadmap: run the design
through a real Meshery instance (not just the CLI gates) and record what worked.

## Environment

| Item | Value |
|---|---|
| Meshery server | `v1.0.71` (`commitsha a2a47d38`), running in Docker on host network |
| Endpoint | `http://127.0.0.1:9081` |
| Provider | **Local** (single-user, no remote provider) |
| CLI | `mesheryctl v1.0.71` at `~/.meshery/bin/mesheryctl` |
| Auth | `~/.meshery/auth.json` → `{"token":"","meshery-provider":"Local"}` |
| Context | `073aa6d8f9ed17503d2ae6ba6731d7e8` → cluster `kind-ai-native` |

Start the server with:

```bash
docker compose -f "$HOME/.meshery/meshery.yaml" up -d
```

> `mesheryctl system start` can hang on this setup; `docker compose` is the
> reliable path. Verify with `curl http://127.0.0.1:9081/api/system/version`.

## What was exercised

| # | Endpoint | Purpose | Result |
|---|---|---|---|
| 1 | `GET /api/system/version` | health / version | ✅ `v1.0.71`, not outdated |
| 2 | `POST /api/registry/register` (via `mesheryctl model import`) | register the `gateway-api` model | ✅ 6 components registered |
| 3 | `POST /api/pattern` (native design save) | persist the design | ⚠️ stored with 0 components (see Findings) |
| 4 | `POST /api/pattern/import` | import a raw file as a design | ⚠️ rejects native designs (manifest/Helm only) |
| 5 | `POST /api/registry/relationships/evaluate` | run the policy/relationship engine | ✅ full pass, 62 actions |

## Evidence

### 1. Health

```
GET /api/system/version
→ {"build":"v1.0.71","commitsha":"a2a47d38","latest":"v1.0.71","outdated":false,"releaseChannel":"stable"}
```

### 2. `gateway-api` model import

Registered the new `gateway-api` model (contributed upstream in
[meshery/meshery#22452](https://github.com/meshery/meshery/pull/22452)) against
the live server:

```
mesheryctl model import -f models/gateway-api
→ SUMMARY: Imported model gateway-api (6 components)
   BackendTLSPolicy, Gateway, GatewayClass, GRPCRoute, HTTPRoute, ReferenceGrant
```

This is the authoritative validation: the server accepted every component
against the real Meshery schema. `mesheryctl model delete gateway-api` then a
clean re-import reproduced the same result.

### 3 & 4. Design persistence (partial)

Two attempts to save/import the native `design.yml` did **not** preserve the
66 components:

- `POST /api/pattern` with `{patternData:{designFile:<design>}, save:true}`
  returned a stored design whose `patternFile` was empty (0 components).
- `POST /api/pattern/import` (the file-import path) rejects native Meshery
  designs — it is for Helm charts / Kubernetes manifests
  (`NewPatternFileFromK8sManifest`), not `designs.meshery.io/v1beta3` files.

The design itself is valid (see `docs/VALIDATION.md` — Validate returns 0
errors, and GATE9 applies 40/40 to a real cluster). The save-path mismatch is a
Meshery v1.0.71 API shape issue, not a defect in the artifact.

### 5. Relationship / policy evaluation (the real "play")

The evaluation engine takes the design inline and re-derives the relationship
graph. This is the strongest server-side exercise of the design:

```
POST /api/registry/relationships/evaluate
body: {"design": <design.yml>}
→ HTTP 200 in ~102s, 315 KB response
```

| Metric | Input | Output |
|---|---|---|
| Components | 66 | 68 (+2) |
| Relationships | 113 | 119 (+6) |

**62 policy actions** were emitted:

| Action | Count |
|---|---|
| `delete_relationship` | 37 (all `hierarchical`) |
| `update_relationship` | 12 |
| `update_component_configuration` | 11 |
| `add_component` | 2 |

The two added components are auto-generated `Container` records
(`containers.0`) produced by the engine's genealogy pass — the same behaviour
seen when the design is hydrated from annotation components. The `trace`
object (`componentsAdded`, `relationshipsUpdated`, …) confirms the engine
re-derived the graph rather than echoing the input.

## Findings

1. **The server is the authority.** CLI gates (`validation/tools/*`) run
   offline; importing into a live server exercises the real registry, schema
   validation, and policy engine. The `gateway-api` model registering cleanly
   here is the acceptance signal for the upstream contribution.

2. **Native-design save is broken in v1.0.71 for this API shape.** The
   `/api/pattern` POST path stores an empty `patternFile`. This does not affect
   the artifact's validity (GATE9 applies 40/40) but is worth noting for anyone
   scripting against the REST API rather than the UI.

3. **`/api/pattern/import` is not the design-import path.** It converts
   Helm/K8s manifests. Native designs go through `/api/pattern` (POST) or the
   UI's Import flow.

4. **Evaluation is expensive but informative.** A 66-component design takes
   ~100s to evaluate server-side (policy passes over every component/relationship
   pair). Budget the timeout accordingly.

5. **The policy engine actively prunes.** 37 hierarchical relationships were
   deleted on evaluation. The design bakes in resolved `ns_of` hierarchical
   edges; the engine re-derives them and drops the ones it does not agree with.
   This is expected — the design is a *snapshot* of a resolved graph, and the
   engine owns the canonical form.

## Reproduce

```bash
# 0. server up
docker compose -f "$HOME/.meshery/meshery.yaml" up -d
curl -s http://127.0.0.1:9081/api/system/version

# 1. register the gateway-api model (from the meshery checkout)
mesheryctl model import -f models/gateway-api
mesheryctl model list | grep gateway

# 2. evaluate the design server-side
python3 -c "import json,yaml; json.dump({'design': yaml.safe_load(open('generated/design.yml'))}, open('/tmp/eval.json','w'))"
curl -s -X POST http://127.0.0.1:9081/api/registry/relationships/evaluate \
  -H 'Content-Type: application/json' --data-binary @/tmp/eval.json \
  --max-time 600 -o /tmp/eval-resp.json -w 'HTTP %{http_code} in %{time_total}s\n'

# 3. summarize
python3 -c "
import json; r=json.load(open('/tmp/eval-resp.json'))
print('components:', len(r['design']['components']), '| relationships:', len(r['design']['relationships']))
print('actions:', len(r['actions']))
"
```

## Related

- `docs/VALIDATION.md` — offline gates (Validate / Dryrun / GATE1–9)
- `validation/GATE9-REPORT.md` — 40/40 apply on the real `kind` cluster
- `docs/QUICKSTART.md` — deploying the design
- Upstream contribution: [meshery/meshery#22452](https://github.com/meshery/meshery/pull/22452)
