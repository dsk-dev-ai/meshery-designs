# Troubleshooting — Meshery Playground

Issues observed when importing this design into Meshery Playground
(`https://play.meshery.io`), their cause, and their status.

## 1. Dry-run: "could not find component with name: Environment, model: meshery-core"

**Observed**

```
error: Unable to deploy the selected design "ai-native-platform"
probableCause: Connection Error ...
longDescription: could not find component with name: Environment,
model: meshery-core, apiVersion: core.meshery.io/v1alpha1
```

**Diagnosis** — Not a design defect. The design file is structurally
valid (Gate 1 PASS, `verify.py` 28/0, full test suite PASS). The failure
is raised while the Playground resolves the `Environment` component from
the `meshery-core` model (0.7.2) during the deploy/dry-run step, which
needs a resolvable model catalog plus a connected Kubernetes target.

**Resolution** — Import the design without the immediate deploy/dry-run,
and ensure the Playground environment has the `meshery-core` model loaded
and a Kubernetes connection assigned to the selected environment.

## 2. Upload: 404 on `meshmap/index.js`

**Observed**

```
Uh-oh! Please pardon our mesh.
Error: HTTP Error Response: 404
(/api/provider/extension/provider/navigator/meshmap/index.js?packageVersion=v1.0.71-1)
```

**Diagnosis** — A Playground frontend/extension asset is missing for the
published bundle version (`v1.0.71-1`). This is a server/deployment issue
on the Meshery side and is unrelated to the design file.

**Resolution** — Hard refresh or open Playground in an incognito window
to drop the stale cached bundle, retry the upload, or use **URL Import**
instead of File Upload. If it persists, report it upstream at
`meshery/meshery` issues.

## 3. Duplicate designs in the account

If repeated import attempts left duplicate `ai-native-platform` entries,
remove the stale ones in the UI (Designs → three-dot menu → Delete) and
re-import `generated/design.yml` once.

The design to keep is `ai-native-platform`, 66 components / 113
relationships. The valid artifact is `generated/design.yml`.

## Verifying the artifact before any upload

```sh
python3 validation/tools/verify.py generated/design.yml   # expect 28 checks, 0 failed
python3 validation/tools/gate1.py generated/design.yml /tmp/g1out   # expect GATE 1: PASS
bash tests/run_all.sh                                     # expect ALL TESTS PASSED
```

`md5 6aead397280a3a6a34780b5a0db009fd` — 66 components, 113 relationships.
