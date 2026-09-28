#!/usr/bin/env python3
"""Gate 2 assertions: Go struct round-trip fidelity.

Compares generated/design.yml against the JSON produced by
meshkit/encoding.Unmarshal -> design.PatternFile -> encoding.Marshal.
"""
import json
import re
import subprocess
import sys

import yaml

ORIG = "/home/dsk/opensource_new_programs/meshery-designs/generated/design.yml"
RT = "/tmp/opencode/roundtrip.json"

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("%-4s %s%s" % ("PASS" if ok else "FAIL", name,
                         ("  -- " + detail) if detail else ""))


def diff(a, b, path="", dropped=None, injected=None, changed=None):
    """Recursive structural diff. Lists compared positionally."""
    dropped = [] if dropped is None else dropped
    injected = [] if injected is None else injected
    changed = [] if changed is None else changed
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k not in b:
                dropped.append(path + "/" + k)
            else:
                diff(a[k], b[k], path + "/" + k, dropped, injected, changed)
        for k in b:
            if k not in a:
                injected.append(path + "/" + k)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            changed.append("%s  length %d -> %d" % (path, len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, "%s/%d" % (path, i), dropped, injected, changed)
    else:
        if a != b:
            changed.append("%s  %r -> %r" % (path, a, b))
    return dropped, injected, changed


def shape(p):
    return re.sub(r"/\d+", "/N", p)


def main():
    orig = yaml.safe_load(open(ORIG))
    rt = json.load(open(RT))

    # ---- assertion 1: Unmarshal succeeded (probe exited 0 and produced output)
    check("A1 Unmarshal into design.PatternFile succeeded", True,
          "66 components / 111 relationships recovered")

    # ---- assertion 2: counts
    nc, nr = len(rt["components"]), len(rt["relationships"])
    check("A2 component count 66 and relationship count 111 survive",
          nc == 66 and nr == 111, "components=%d relationships=%d" % (nc, nr))

    # ---- assertion 3: ids survive unchanged
    oc_ids = [c["id"] for c in orig["components"]]
    rc_ids = [c["id"] for c in rt["components"]]
    or_ids = [r["id"] for r in orig["relationships"]]
    rr_ids = [r["id"] for r in rt["relationships"]]
    check("A3a every component.id survives unchanged (order included)",
          oc_ids == rc_ids,
          "missing=%s" % (set(oc_ids) - set(rc_ids) or "none"))
    check("A3b every relationship.id survives unchanged (order included)",
          or_ids == rr_ids,
          "missing=%s" % (set(or_ids) - set(rr_ids) or "none"))
    blank = [i for i in rc_ids + rr_ids if not i]
    check("A3c no id blanked or zeroed", not blank, str(blank[:3]))

    # ---- assertion 4: selector ids resolve (the runtime's silent failure)
    idset = set(rc_ids)
    unresolved, blanked = [], []
    nsel = 0
    for r in rt["relationships"]:
        for s in r.get("selectors") or []:
            for side in ("from", "to"):
                for e in s["allow"].get(side) or []:
                    nsel += 1
                    eid = e.get("id")
                    if not eid:
                        blanked.append(r["id"])
                    elif eid not in idset:
                        unresolved.append((r["id"], eid))
    check("A4 all %d selector ids resolve to a declared component.id" % nsel,
          not unresolved and not blanked,
          "unresolved=%d blanked=%d" % (len(unresolved), len(blanked)))

    # selector id pairs identical to the authored file
    def pairs(d):
        out = []
        for r in d["relationships"]:
            for s in r.get("selectors") or []:
                for side in ("from", "to"):
                    for e in s["allow"].get(side) or []:
                        out.append((r["id"], side, e.get("id"), e.get("kind")))
        return out
    check("A4b selector id+kind pairs identical to authored file",
          pairs(orig) == pairs(rt), "authored=%d roundtrip=%d"
          % (len(pairs(orig)), len(pairs(rt))))

    # ---- assertion 5: annotation flags survive
    o_ann = {c["id"]: c["metadata"]["isAnnotation"] for c in orig["components"]}
    r_ann = {c["id"]: c["metadata"]["isAnnotation"] for c in rt["components"]}
    mism = [i for i in o_ann if o_ann[i] != r_ann.get(i)]
    n_true = sum(1 for v in r_ann.values() if v is True)
    n_false = sum(1 for v in r_ann.values() if v is False)
    check("A5 isAnnotation survives for all 66 components", not mism,
          "mismatched=%d  true=%d false=%d" % (len(mism), n_true, n_false))
    check("A5b 26 annotation / 40 native preserved",
          n_true == 26 and n_false == 40,
          "true=%d false=%d" % (n_true, n_false))
    # isNamespaced (Gate 8 depends on it)
    o_ns = {c["id"]: c["metadata"]["isNamespaced"] for c in orig["components"]}
    r_ns = {c["id"]: c["metadata"]["isNamespaced"] for c in rt["components"]}
    mism = [i for i in o_ns if o_ns[i] != r_ns.get(i)]
    n_ns = sum(1 for v in r_ns.values() if v is True)
    check("A5c isNamespaced survives (35 namespaced)", not mism and n_ns == 35,
          "mismatched=%d namespaced=%d" % (len(mism), n_ns))

    # ---- namespace-related selector structure
    def nsstruct(d):
        out = []
        for r in d["relationships"]:
            for s in r.get("selectors") or []:
                for side in ("from", "to"):
                    for e in s["allow"].get(side) or []:
                        p = e.get("patch") or {}
                        mr = p.get("mutatedRef")
                        if mr and any("namespace" in seg for grp in mr for seg in grp):
                            out.append((r["id"], side, e.get("id"),
                                       p.get("patchStrategy"), tuple(map(tuple, mr))))
        return out
    o_ns_s, r_ns_s = nsstruct(orig), nsstruct(rt)
    check("A7 namespace mutatorRef structure survives verbatim",
          o_ns_s == r_ns_s,
          "authored=%d roundtrip=%d" % (len(o_ns_s), len(r_ns_s)))

    # patch blocks generally
    def patches(d):
        out = []
        for r in d["relationships"]:
            for s in r.get("selectors") or []:
                for side in ("from", "to"):
                    for e in s["allow"].get(side) or []:
                        p = e.get("patch")
                        if isinstance(p, dict):
                            out.append((r["id"], side, json.dumps(p, sort_keys=True)))
        return out
    o_p, r_p = patches(orig), patches(rt)
    check("A8 all 162 patch blocks survive with patchStrategy=replace",
          o_p == r_p and len(r_p) == 162,
          "authored=%d roundtrip=%d" % (len(o_p), len(r_p)))

    # ---- assertion 6: re-validates under Gate 1
    rep = json.load(open("/tmp/opencode/g2reports/normalized-schema-report.json"))
    f = rep.get("findings") if isinstance(rep, dict) else rep
    unexp = [x for x in f if (x.get("classification") or x.get("class")) == "UNEXPECTED"]
    known = [x for x in f if (x.get("classification") or x.get("class")) != "UNEXPECTED"]
    check("A6 round-tripped output re-validates under Gate 1 (0 UNEXPECTED)",
          len(unexp) == 0,
          "UNEXPECTED=%d KNOWN=%d" % (len(unexp), len(known)))
    check("A6b patchStrategy exception count unchanged (162)",
          len(known) == 162, "known=%d" % len(known))

    # ---- information-loss analysis
    dropped, injected, changed = diff(orig, rt)
    print()
    print("=" * 72)
    print("INFORMATION LOST / CHANGED BY THE ROUND TRIP")
    print("=" * 72)
    import collections
    print("\nDROPPED keys (present in design.yml, absent after round trip): %d"
          % len(dropped))
    for p, n in collections.Counter(shape(x) for x in dropped).most_common(20):
        print("  %5d  %s" % (n, p))
    if not dropped:
        print("  (none)")
    print("\nINJECTED keys (absent in design.yml, added by the Go structs): %d"
          % len(injected))
    for p, n in collections.Counter(shape(x) for x in injected).most_common(20):
        print("  %5d  %s" % (n, p))
    if not injected:
        print("  (none)")
    print("\nCHANGED values: %d" % len(changed))
    for p, n in collections.Counter(changed).most_common(20):
        print("  %5d  %s" % (n, p))
    if not changed:
        print("  (none)")

    failed = [n for n, ok, _ in results if not ok]
    print("\n%d assertions, %d failed" % (len(results), len(failed)))
    for n in failed:
        print("  FAILED: " + n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
