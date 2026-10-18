# Contributing

Thanks for your interest in the AI-Native Platform Meshery design.

## Ground rules

- **The generated artifact is derived.** Never edit `generated/design.yml` by hand. Change the
  specification (`validation/tools/spec_data.py`) or the generator (`validation/tools/gen.py`) and
  regenerate. CI checks that the committed artifact reproduces byte-for-byte.
- **Nothing is invented.** Every component kind, version, annotation flag and relationship blueprint
  must exist in the pinned Meshery catalog. The tooling raises rather than substituting.
- **Keep the gates green.** A change is not complete until every gate passes.

## Development setup

The generator and verifier read the pinned Meshery catalog from disk. Point them at a checkout of
the four models they use:

```bash
export MESHER_MODELS_ROOT=/path/to/meshery/models      # default: /home/dsk/opensource_new_programs/meshery/models
export MESHER_SCHEMAS=/path/to/schemas/schemas/constructs   # Gate 1 only
```

The models needed are `kubernetes/v1.37.1`, `meshery-core/0.7.2`, `meshery-operator/1.0.70`, and
`kube-prometheus-stack/89.2.2`. Gate 1 additionally needs
[`meshery/schemas`](https://github.com/meshery/schemas) at tag `v1.3.37`.

## Make a change

```bash
# 1. edit spec_data.py and/or gen.py

# 2. regenerate (deterministic)
python3 validation/tools/gen.py generated/design.yml

# 3. run every gate
bash tests/run_all.sh
python3 validation/tools/gate1.py generated/design.yml /tmp/gate1
```

If the design changes, update the affected reports and docs in the same pull request
(`validation/*-REPORT.md`, `spec/*`, `docs/*`, `README.md`, and this changelog).

## Validate a live deploy (optional)

If you have a Kubernetes cluster and a local Meshery server:

```bash
bash deploy.sh
```

This must report `PASS: 40/40 components applied with zero failures`.

## Commit and pull requests

- Branch from `main`; short-lived branches merged with `--no-ff`.
- Use conventional commit messages: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- One logical change per pull request; keep the artifact and its source changes together.
- Describe what changed, why, and which gates you ran.

## Reporting issues

Open an issue at
[github.com/dsk-dev-ai/meshery-designs/issues](https://github.com/dsk-dev-ai/meshery-designs/issues)
with the command you ran, the output, and the `md5sum` of `generated/design.yml`.
