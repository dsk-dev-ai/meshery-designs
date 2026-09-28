#!/usr/bin/env python3
"""Structural and fidelity verification of the generated design.

Covers Gate 1 assertions 1-12 and the offline parts of Gates 3, 5, 6:
  - every catalog-derived value still matches the catalog on disk
  - every selector id resolves to a declared component
  - no Pod components and no firewall edges
  - every kind/type/subType triple actually occurs in the upstream catalog
  - provenance classification matches RELATIONSHIP_MATRIX.md
"""
import collections
import glob
import json
import os
import re
import sys
import uuid

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_data as S  # noqa: E402

MODELS_ROOT = "/home/dsk/opensource_new_programs/meshery/models"
MODEL_VERSION = {S.K8S: "v1.37.1", S.CORE: "0.7.2", S.OPER: "1.0.70",
                 S.PROM: "89.2.2", S.SUMO: "4.18.0"}
ZERO = "00000000-0000-0000-0000-000000000000"
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("%-4s %s%s" % ("PASS" if ok else "FAIL", name,
                         ("  -- " + detail) if detail else ""))
    return ok


def main():
    design = yaml.safe_load(open(sys.argv[1]))
    comps = design["components"]
    rels = design["relationships"]
    by_id = {c["id"]: c for c in comps}
    name_of = {c["id"]: c["description"][:0] or c["component"]["kind"] for c in comps}

    # ---- design naming: map component id -> spec name via description order
    spec_order = [c[0] for c in S.COMPONENTS]
    id_by_name = {}
    for (spec_name, model, kind, ann, _d), c in zip(S.COMPONENTS, comps):
        id_by_name[spec_name] = c["id"]
    check("component order matches COMPONENT_INVENTORY.md",
          [c["component"]["kind"] for c in comps] == [x[2] for x in S.COMPONENTS])

    # ---- Gate 1 assertion 1 & 2
    allowed = {"id", "name", "schemaVersion", "version", "metadata", "components",
               "preferences", "relationships"}
    check("A1 top-level keys subset of allowed",
          set(design) <= allowed, str(set(design) - allowed))
    check("A2 all 6 required top-level keys present",
          {"id", "name", "schemaVersion", "version", "components",
           "relationships"} <= set(design))

    # ---- assertion 3
    req11 = {"id", "displayName", "description", "schemaVersion", "format",
             "version", "configuration", "metadata", "model", "modelReference",
             "component"}
    bad = [c["id"] for c in comps if not req11 <= set(c)]
    check("A3 every component has all 11 required keys", not bad, str(bad[:3]))

    # ---- assertion 4
    req6 = {"genealogy", "isAnnotation", "isNamespaced", "published",
            "instanceDetails", "configurationUISchema"}
    bad = [c["id"] for c in comps if not req6 <= set(c["metadata"])]
    check("A4 every component metadata has all 6 sub-keys", not bad, str(bad[:3]))

    # ---- assertion 5
    bad = [c["id"] for c in comps if not {"version", "kind", "schema"} <= set(c["component"])]
    check("A5 every component block has version/kind/schema", not bad, str(bad[:3]))

    # ---- assertion 6
    req7 = {"id", "schemaVersion", "version", "model", "kind", "type", "subType"}
    bad = [r["id"] for r in rels if not req7 <= set(r)]
    check("A6 every relationship has all 7 required keys", not bad, str(bad[:3]))

    # ---- assertion 7
    bad = [r["id"] for r in rels
           if r["kind"] not in {"hierarchical", "edge", "sibling"}
           or r.get("status") not in {"enabled", "ignored", "deleted",
                                      "approved", "pending"}]
    check("A7 relationship kind/status within enums", not bad, str(bad[:3]))

    # ---- assertion 8
    req6b = {"id", "name", "version", "displayName", "model", "registrant"}
    bad = [c["id"] for c in comps if not req6b <= set(c["modelReference"])]
    check("A8 every modelReference has all 6 required keys", not bad, str(bad[:3]))

    # ---- assertion 9
    bad = []
    for c in comps + rels:
        if not UUID_RE.match(c["id"]) or c["id"] == ZERO:
            bad.append(c["id"])
        uuid.UUID(c["id"])
    check("A9 every id is a valid non-zero UUID", not bad, str(bad[:3]))

    # ---- assertion 10
    check("A10 name 1-255 and version 1-50",
          1 <= len(design["name"]) <= 255 and 1 <= len(design["version"]) <= 50,
          "name=%r version=%r" % (design["name"], design["version"]))

    # ---- assertion 11
    with_patch, patch_fields = 0, 0
    values = set()
    for r in rels:
        hit = False
        for sel in r["selectors"]:
            for side in ("from", "to"):
                for e in sel["allow"][side]:
                    p = e.get("patch") or {}
                    if "patchStrategy" in p:
                        patch_fields += 1
                        values.add(p["patchStrategy"])
                        hit = True
        with_patch += 1 if hit else 0
    check("A11 exactly 81 relationships carry patchStrategy, all 'replace'",
          with_patch == 81 and values == {"replace"},
          "with=%d fields=%d values=%s" % (with_patch, patch_fields, sorted(values)))
    check("A11b remaining 30 carry no patchStrategy",
          len(rels) - with_patch == 30, str(len(rels) - with_patch))

    # ---- counts vs the frozen specifications
    ann = sum(1 for c in comps if c["metadata"]["isAnnotation"])
    check("66 components (40 native / 26 annotation)",
          len(comps) == 66 and ann == 26 and len(comps) - ann == 40,
          "n=%d native=%d annotation=%d" % (len(comps), len(comps) - ann, ann))

    rel_ann = sum(1 for r in rels if r["metadata"]["isAnnotation"])
    check("111 relationships (59 semantic / 52 annotation)",
          len(rels) == 111 and rel_ann == 52 and len(rels) - rel_ann == 59,
          "n=%d semantic=%d annotation=%d" % (len(rels), len(rels) - rel_ann, rel_ann))

    by_model = collections.Counter(
        c["modelReference"]["name"] for c in comps)
    expect = {S.K8S: 33, S.CORE: 26, S.OPER: 2, S.PROM: 4, S.SUMO: 1}
    check("component count per model matches inventory", dict(by_model) == expect,
          str(dict(by_model)))

    # ---- Gate 3: catalog fidelity
    bad = []
    for (spec_name, model, kind, is_ann, _d), c in zip(S.COMPONENTS, comps):
        p = os.path.join(MODELS_ROOT, model, MODEL_VERSION[model], "v1.0.0",
                         "components", kind + ".json")
        cat = json.load(open(p))
        if c["component"]["version"] != cat["component"]["version"]:
            bad.append((spec_name, "component.version"))
        if c["component"]["kind"] != cat["component"]["kind"]:
            bad.append((spec_name, "component.kind"))
        if c["metadata"]["isNamespaced"] != cat["metadata"]["isNamespaced"]:
            bad.append((spec_name, "isNamespaced"))
        if c["metadata"]["genealogy"] != cat["metadata"].get("genealogy", ""):
            bad.append((spec_name, "genealogy"))
    check("Gate 3 every component.version/kind/isNamespaced/genealogy matches catalog",
          not bad, str(bad[:5]))

    # ---- the one documented override
    overrides = []
    for (spec_name, model, kind, is_ann, _d), c in zip(S.COMPONENTS, comps):
        p = os.path.join(MODELS_ROOT, model, MODEL_VERSION[model], "v1.0.0",
                         "components", kind + ".json")
        cat_ann = json.load(open(p))["metadata"]["isAnnotation"]
        if bool(cat_ann) != bool(c["metadata"]["isAnnotation"]):
            overrides.append(spec_name)
    check("Environment is the only isAnnotation override vs catalog",
          overrides == ["env-production"], str(overrides))

    # ---- selector integrity (Gate 2 assertion 4, offline half)
    bad = []
    for r in rels:
        for sel in r["selectors"]:
            for side in ("from", "to"):
                for e in sel["allow"][side]:
                    if e["id"] not in by_id:
                        bad.append((r["id"], e["id"]))
    check("every selector id resolves to a declared component", not bad, str(bad[:5]))

    # ---- no invented k8s kinds (Gate 6 assertion 4)
    kinds = {c["component"]["kind"] for c in comps}
    check("no Pod components", "Pod" not in kinds)
    check("no StorageClass component", "StorageClass" not in kinds)
    check("no firewall relationship",
          not any(r["subType"] == "firewall" for r in rels))
    check("no edge with a Pod participant",
          not any(e["kind"] == "Pod"
                  for r in rels for sel in r["selectors"]
                  for side in ("from", "to") for e in sel["allow"][side]))

    # ---- every triple occurs in the upstream catalog (Gate 5 assertion 10)
    triples = {(r["kind"], r["type"], r["subType"]) for r in rels}
    catalog_triples = set()
    for path in glob.glob(os.path.join(MODELS_ROOT, "*", "*", "v*", "relationships", "*.json")):
        try:
            d = json.load(open(path))
        except Exception:
            continue
        rs = d.get("relationships", d)
        for r in (rs if isinstance(rs, list) else [rs]):
            if isinstance(r, dict) and {"kind", "type", "subType"} <= set(r):
                catalog_triples.add((r["kind"], r["type"], r["subType"]))
    invented = triples - catalog_triples
    check("every kind/type/subType triple exists in the catalog",
          not invented, str(invented))

    # ---- provenance classification matches the matrix
    prov = collections.Counter(e[4] for e in S.EDGES)
    check("provenance split B54 / H21 / C27 / A9",
          dict(prov) == {"B": 54, "H": 21, "C": 27, "A": 9}, str(dict(prov)))
    check("relationship count matches the matrix", len(rels) == len(S.EDGES) == 111)

    # ---- each hand-authored edge is labelled as such in its description
    hand = [r for r in rels if "Provenance H" in r["metadata"]["description"]]
    check("hand-authored edges declare Provenance H (%d)" % prov["H"],
          len(hand) == prov["H"], str(len(hand)))
    hb = [r for r in rels
          if "no upstream blueprint exists" in r["metadata"]["description"]]
    check("only the 25 basis-less edges claim no blueprint (%d)" % len(hb),
          len(hb) == 25, str(len(hb)))

    failed = [n for n, ok, _ in results if not ok]
    print("\n%d checks, %d failed" % (len(results), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
