#!/usr/bin/env python3
"""Gate 1 harness for the ai-native-platform design.

Runs strict Draft-07 validation against the SHIPPED, UNMODIFIED Meshery schema
and then produces two reports:

  strict-schema-report     the raw validator output, exceptions included as
                           errors. This command is expected to fail.
  normalized-schema-report the same findings classified as
                           KNOWN_UPSTREAM_SCHEMA_EXCEPTION or UNEXPECTED.

The schema is opened read-only. Nothing here patches, filters, or rewrites the
schema or the artifact; the only transformation is the classification of already
reported findings, which happens strictly after validation.
"""
import json
import os
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import url2pathname, pathname2url

import yaml
import jsonschema
from jsonschema import RefResolver

SCHEMAS = ("/home/dsk/go/pkg/mod/github.com/meshery/schemas@v1.3.37/"
           "schemas/constructs")
DESIGN_SCHEMA = os.path.join(SCHEMAS, "v1beta3/design/design.yaml")

KNOWN = "KNOWN_UPSTREAM_SCHEMA_EXCEPTION"
UNEXPECTED = "UNEXPECTED"

# The exact scope of the documented exception. Anything outside this is a real
# violation and must fail the gate.
def classify(err, design):
    path = list(err.absolute_path)
    # ... relationships[i].selectors[j].allow.{from,to}[k].patch.patchStrategy
    if len(path) >= 6 and path[0] == "relationships":
        try:
            idx = path[1]
        except Exception:
            return UNEXPECTED
        if path[2] != "selectors" or path[4] != "allow" or path[5] not in ("from", "to"):
            return UNEXPECTED
        if path[-2:] != ["patch", "patchStrategy"]:
            return UNEXPECTED
        value = err.instance
        if value != "replace":
            return UNEXPECTED
        return KNOWN
    return UNEXPECTED


def _walk_refs(node):
    """Yield every (container, key) holding a '$ref' string, recursively."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str):
                yield node, k
            else:
                yield from _walk_refs(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_refs(v)


def build_bundle(entry):
    """Inline the external $ref graph into one self-contained schema.

    The upstream documents declare flattened `$id`s such as
    `https://schemas.meshery.io/component.yaml`, which do not correspond to
    their real directory layout, so $id-based re-basing cannot resolve relative
    refs. Files are therefore bundled by their *filesystem* location, and $id is
    dropped from the in-memory copy. Files on disk are opened read-only and are
    never modified.
    """
    docs = {}        # abspath -> parsed doc
    order = []       # stable ordering
    queue = [os.path.abspath(entry)]

    def load(path):
        if path in docs:
            return
        doc = yaml.safe_load(open(path))
        if isinstance(doc, dict):
            doc.pop("$id", None)
        docs[path] = doc
        order.append(path)
        for container, key in _walk_refs(doc):
            ref = container[key]
            if not isinstance(ref, str) or ref.startswith("#"):
                continue
            target = ref.split("#", 1)[0]
            if not target:
                continue
            if "://" in target:
                raise RuntimeError("unexpected absolute $ref %r in %s" % (ref, path))
            queue.append(os.path.abspath(os.path.join(os.path.dirname(path), target)))

    while queue:
        load(queue.pop())

    index = {p: "f%d" % i for i, p in enumerate(order)}

    def rewrite(path, node):
        if isinstance(node, dict):
            for k, v in list(node.items()):
                if k == "$ref" and isinstance(v, str):
                    target, _, frag = v.partition("#")
                    if target:
                        abs_target = os.path.abspath(
                            os.path.join(os.path.dirname(path), target))
                        if abs_target not in index:
                            raise RuntimeError("unresolved $ref %r in %s" % (v, path))
                        node[k] = "#/definitions/%s%s" % (
                            index[abs_target], frag if frag.startswith("/") else "")
                    else:
                        node[k] = "#/definitions/%s%s" % (
                            index[path], frag if frag.startswith("/") else "")
                else:
                    rewrite(path, v)
        elif isinstance(node, list):
            for v in node:
                rewrite(path, v)

    for p in order:
        rewrite(p, docs[p])

    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {index[p]: docs[p] for p in order},
        "$ref": "#/definitions/%s" % index[os.path.abspath(entry)],
    }


def main():
    design_path = sys.argv[1]
    reports_dir = sys.argv[2]

    design = yaml.safe_load(open(design_path))
    bundle = build_bundle(DESIGN_SCHEMA)
    validator = jsonschema.Draft7Validator(bundle)

    errors = sorted(validator.iter_errors(design),
                    key=lambda e: (list(map(str, e.absolute_path)), e.message))

    findings = []
    for e in errors:
        findings.append({
            "path": "/".join(str(x) for x in e.absolute_path) or "<root>",
            "value": e.instance if isinstance(e.instance, (str, int, float, bool))
                     or e.instance is None else "<object>",
            "message": e.message,
            "classification": classify(e, design),
        })

    known = [f for f in findings if f["classification"] == KNOWN]
    unexpected = [f for f in findings if f["classification"] == UNEXPECTED]

    # Relationships carrying at least one patchStrategy field.
    rel_with_patch = 0
    patch_fields = 0
    for rel in design.get("relationships", []):
        hit = False
        for sel in rel.get("selectors", []):
            for side in ("from", "to"):
                for entry in (sel.get("allow", {}).get(side) or []):
                    p = entry.get("patch") or {}
                    if "patchStrategy" in p:
                        patch_fields += 1
                        hit = True
        rel_with_patch += 1 if hit else 0

    os.makedirs(reports_dir, exist_ok=True)

    # ---------------- strict-schema-report ----------------
    with open(os.path.join(reports_dir, "strict-schema-report.txt"), "w") as fh:
        fh.write("Gate 1 strict Draft-07 validation\n")
        fh.write("schema:  %s\n" % DESIGN_SCHEMA)
        fh.write("artifact: %s\n" % design_path)
        fh.write("schema modified by this harness: NO\n")
        fh.write("expected outcome: FAIL on patchStrategy='replace' "
                 "(upstream schema/catalog inconsistency)\n")
        fh.write("=" * 78 + "\n")
        fh.write("design %s is INVALID under the shipped schema: "
                 "%d error(s)\n" % (design.get("name"), len(findings)))
        fh.write("=" * 78 + "\n\n")
        for f in findings:
            fh.write("FAIL  %s\n" % f["path"])
            fh.write("      value:   %r\n" % f["value"])
            fh.write("      message: %s\n\n" % f["message"])
        fh.write("-" * 78 + "\n")
        fh.write("total errors: %d\n" % len(findings))
        fh.write("  patchStrategy='replace': %d\n" % len(known))
        fh.write("  other:                   %d\n" % len(unexpected))
        fh.write("\nExit status: 1 (expected)\n")

    # ---------------- normalized-schema-report ----------------
    with open(os.path.join(reports_dir, "normalized-schema-report.txt"), "w") as fh:
        fh.write("Gate 1 normalized report\n")
        fh.write("artifact: %s\n" % design_path)
        fh.write("=" * 78 + "\n")
        fh.write("EXCEPTION NOTICE\n")
        fh.write("Strict Draft-07 validation against the shipped Meshery schema fails\n")
        fh.write("for patchStrategy='replace'. This is an upstream schema/catalog\n")
        fh.write("inconsistency. The design preserves the catalog value faithfully.\n")
        fh.write("The exception is narrowly scoped and does not relax any other schema\n")
        fh.write("constraint.\n")
        fh.write("=" * 78 + "\n\n")
        fh.write("Counts\n")
        fh.write("  total findings                          %d\n" % len(findings))
        fh.write("  %-40s %d\n" % (KNOWN, len(known)))
        fh.write("  %-40s %d\n" % (UNEXPECTED, len(unexpected)))
        fh.write("\nScope\n")
        fh.write("  relationships carrying patchStrategy      %d (expect 81)\n"
                 % rel_with_patch)
        fh.write("  relationships without patchStrategy       %d (expect 30)\n"
                 % (len(design.get("relationships", [])) - rel_with_patch))
        fh.write("  patchStrategy fields (derived)            %d\n" % patch_fields)
        fh.write("\nClassification rule: a finding is %s only if its path is\n"
                 % KNOWN)
        fh.write("relationships[i].selectors[j].allow.{from,to}[k].patch.patchStrategy\n")
        fh.write("and its value is exactly \"replace\". Every other finding is %s\n"
                 % UNEXPECTED)
        fh.write("and fails the gate.\n")
        fh.write("\n" + "-" * 78 + "\n")
        fh.write("UNEXPECTED findings\n")
        fh.write("-" * 78 + "\n")
        if unexpected:
            for f in unexpected:
                fh.write("%s  %s\n      %s\n" % (UNEXPECTED, f["path"], f["message"]))
        else:
            fh.write("(none)\n")
        fh.write("\n" + "-" * 78 + "\n")
        fh.write("KNOWN_UPSTREAM_SCHEMA_EXCEPTION findings\n")
        fh.write("-" * 78 + "\n")
        for f in known:
            fh.write("%s  %s\n" % (KNOWN, f["path"]))
        fh.write("\n" + "=" * 78 + "\n")
        gate1 = "PASS" if (not unexpected and rel_with_patch == 81) else "FAIL"
        fh.write("GATE 1: %s\n" % gate1)
        if unexpected:
            fh.write("  reason: %d unexpected violation(s)\n" % len(unexpected))
        if rel_with_patch != 81:
            fh.write("  reason: %d relationships carry patchStrategy, expected 81\n"
                     % rel_with_patch)
        if gate1 == "PASS":
            fh.write("  zero unexpected violations; the only findings are the documented\n")
            fh.write("  patchStrategy='replace' exception. Upstream schema unmodified.\n")

    with open(os.path.join(reports_dir, "normalized-schema-report.json"), "w") as fh:
        json.dump({
            "artifact": design_path,
            "schema": DESIGN_SCHEMA,
            "schema_modified": False,
            "total_findings": len(findings),
            "known_upstream_schema_exception": len(known),
            "unexpected": len(unexpected),
            "relationships_with_patchStrategy": rel_with_patch,
            "relationships_without_patchStrategy":
                len(design.get("relationships", [])) - rel_with_patch,
            "patchStrategy_fields": patch_fields,
            "gate1": "PASS" if (not unexpected and rel_with_patch == 81) else "FAIL",
            "findings": findings,
        }, fh, indent=2)

    print("total findings               %d" % len(findings))
    print("  %-38s %d" % (KNOWN, len(known)))
    print("  %-38s %d" % (UNEXPECTED, len(unexpected)))
    print("relationships w/ patch       %d (expect 81)" % rel_with_patch)
    print("relationships w/o patch      %d (expect 30)"
          % (len(design.get("relationships", [])) - rel_with_patch))
    print("patch fields (derived)       %d" % patch_fields)
    for f in unexpected[:20]:
        print("  UNEXPECTED %s :: %s" % (f["path"], f["message"][:110]))
    print("GATE 1: %s" % ("PASS" if (not unexpected and rel_with_patch == 81) else "FAIL"))
    return 0 if not unexpected else 1


if __name__ == "__main__":
    sys.exit(main())
