# Troubleshooting — Meshery Playground

Issues observed when importing this design into Meshery Playground
(`https://play.meshery.io`), their cause, and their status.

## 1. Dry-run: "could not find component with name: Environment, model: meshery-core"

**Observed** (fixed in this repository; kept for reference)

```
error: Unable to deploy the selected design "ai-native-platform"
probableCause: Connection Error ...
longDescription: could not find component with name: Environment,
model: meshery-core, apiVersion: core.meshery.io/v1alpha1
```

**Diagnosis** — This *was* a design defect. The design originally used
meshery-core's catalog `Environment` component as the environment
grouping. That component is the only one in `meshery-core` 0.7.2 with an
empty `component.schema` **and** `metadata.isAnnotation: false`;
`ComponentDefinition.Create`
(`schemas/models/v1beta3/component/component_helper.go`) silently returns
without registering any component in that state, so the registry never
holds a `meshery-core` `Environment`. Dry-run validation resolves every
referenced component and fails when it reaches this one. The file is
structurally valid (Gate 1 PASS, `verify.py` 28/0, full test suite PASS);
the failure is specifically in component *resolution*.

**Resolution** — Fixed by replacing `env-production`'s kind with the
registered meshery-core `Section` annotation and retargeting its four §10
`hierarchical/parent/alias` edges. No `isAnnotation` override remains. See
`spec/COMPONENT_INVENTORY.md`. The current `generated/design.yml` contains
zero `Environment` component references.

## 2. Upload: 404 on `meshmap/index.js`

**Observed**

```
Uh-oh! Please pardon our mesh.
Error: HTTP Error Response: 404
(/api/provider/extension/provider/navigator/meshmap/index.js?packageVersion=v1.0.71-1)
```

**Diagnosis** — Upstream Meshery bug, not a design defect. The error is
rendered by the Navigator/MeshMap host when `useRemoteComponent(url)`
fails to fetch the extension bundle
(`ui/components/layout/Navigator/NavigatorExtension.tsx`, the
`NavigatorExtensionError` component at the `err != null` branch). The
Playground provider advertises extension `packageVersion=v1.0.71-1` but
does not serve that bundle, so the fetch returns 404. It fires while the
Navigator UI loads, independently of any design import — the design
upload itself succeeds.

**Resolution** — Not fixable from this repository. Workarounds: hard
refresh or an incognito window to drop the stale cached bundle; retry
after Playground redeploys; or wait for the provider to publish the
matching extension version. Report at `meshery/meshery` issues (the
host error path above), noting the requested
`packageVersion=v1.0.71-1` returned 404.

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

`md5 7f5c4e87802de37a323204099958369c` — 66 components, 113 relationships.
