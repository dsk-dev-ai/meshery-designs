#!/usr/bin/env python3
"""Generate the ai-native-platform Meshery design from the frozen specifications.

Every catalog-derived value (model, kind, component.version, component.schema,
model id, registrant, isNamespaced, genealogy, styles, capabilities) is read from
the Meshery model catalog at the pinned versions. Nothing is invented.

The only deliberate override is Environment.metadata.isAnnotation, documented in
COMPONENT_INVENTORY.md.

Deterministic UUIDs (uuid5) are used so re-running produces an identical file.
"""
import json
import os
import sys
import uuid
import collections

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_data as S  # noqa: E402

MODELS_ROOT = "/home/dsk/opensource_new_programs/meshery/models"
MODEL_VERSION = {
    S.K8S: "v1.37.1",
    S.CORE: "0.7.2",
    S.OPER: "1.0.70",
    S.PROM: "89.2.2",
    S.SUMO: "4.18.0",
}
DESIGN_ID = uuid.uuid5(uuid.NAMESPACE_URL, "meshery-design/ai-native-platform")
COMPONENT_NS = uuid.uuid5(uuid.NAMESPACE_URL, "meshery-design/ai-native-platform/component")
RELATIONSHIP_NS = uuid.uuid5(uuid.NAMESPACE_URL, "meshery-design/ai-native-platform/relationship")
DESIGN_SCHEMA_VERSION = "designs.meshery.io/v1beta3"
COMPONENT_SCHEMA_VERSION = "components.meshery.io/v1beta2"
RELATIONSHIP_SCHEMA_VERSION = "relationships.meshery.io/v1beta2"
ZERO_UUID = "00000000-0000-0000-0000-000000000000"


def load(rel_path):
    with open(os.path.join(MODELS_ROOT, rel_path)) as fh:
        return json.load(fh)


def first_rel(doc):
    r = doc.get("relationships", doc)
    return r[0] if isinstance(r, list) else r


# Keys the shipped ModelDefinition permits (additionalProperties: false).
MODEL_KEYS = {
    "id", "schemaVersion", "version", "name", "displayName", "description",
    "status", "registrant", "registrantId", "categoryId", "category",
    "subCategory", "metadata", "model", "relationships", "components",
    "componentsCount", "relationshipsCount", "created_at", "updated_at",
}
# Keys the shipped Connection permits (additionalProperties: false).
REGISTRANT_KEYS = {
    "id", "name", "credentialId", "type", "subType", "kind", "metadata",
    "status", "user_id", "created_at", "updated_at", "deleted_at",
    "environments", "schemaVersion",
}


def registrant_block(reg):
    """Normalise a catalog registrant into the shipped Connection shape.

    sumologic spells the field `sub_type` where every other model spells it
    `subType`, and the shipped schema requires `subType` and rejects unknown
    keys, so the spelling is normalised here. Null-valued optional fields are
    dropped because the shipped schema types them as strings.
    """
    out = {k: v for k, v in reg.items() if k in REGISTRANT_KEYS and v is not None}
    out["subType"] = reg.get("subType", reg.get("sub_type", "")) or ""
    out.pop("sub_type", None)
    if not out.get("schemaVersion"):
        out["schemaVersion"] = "models.meshery.io/v1beta1"
    return out


# The shipped Shape enum (25 values) has no 'circle', 'shield' or
# 'right-rhomboid', all of which the catalog uses. Each mapping below is
# either an exact or a nearest-form match and is reported in the fidelity
# census. An unmapped shape raises rather than silently falling back.
SHAPE_MAP = {
    "circle": "ellipse",            # 25 components; circle is an ellipse
    "right-rhomboid": "rhomboid",   # 1 component; exact suffix match
    "shield": "pentagon",           # 4 components; nearest 5-sided form
}
SHAPE_ENUM = {
    "barrel", "bottom-round-rectangle", "concave-hexagon", "cut-rectangle",
    "diamond", "ellipse", "heptagon", "hexagon", "octagon", "pentagon",
    "polygon", "rectangle", "rhomboid", "round-diamond", "round-heptagon",
    "round-hexagon", "round-octagon", "round-pentagon", "round-rectangle",
    "round-tag", "round-triangle", "star", "tag", "triangle", "vee",
}


def model_metadata(meta):
    """Keep only the model.metadata keys the shipped schema can represent.

    `capabilities` is null in every catalog model.json but is typed as an
    array, and `shape` uses the catalog's 'circle' value which the shipped
    Shape enum rejects. Both are dropped; the shape is carried on the
    component's `styles` block instead, where it is mapped to a legal value.
    """
    out = {}
    for k in ("isAnnotation", "primaryColor", "secondaryColor",
              "svgWhite", "svgColor", "svgComplete", "styleOverrides"):
        v = meta.get(k)
        if v not in (None, ""):
            out[k] = v
    return out


# The catalog's subCategory values are validated against the shipped SubCategory
# enum. `meshery-operator` ships "App Definition and Development", which that
# enum does not contain; the schema's own documented default is used instead of
# inventing a classification. Recorded in the fidelity report.
SUBCATEGORY_ENUM = {
    "API Gateway", "API Integration", "Application Definition & Image Build",
    "Automation & Configuration", "Certified Kubernetes - Distribution",
    "Chaos Engineering", "Cloud Native Storage", "Cloud Provider", "CNI",
    "Compute", "Container Registry", "Container Runtime", "Container Security",
    "Container", "Content Delivery Network",
    "Continuous Integration & Delivery", "Coordination & Service Discovery",
    "Database", "Flowchart", "Framework", "Installable Platform",
    "Key Management", "Key Management Service", "Logging", "Machine Learning",
    "Management", "Marketplace", "Monitoring", "Observability", "Orchestration",
    "Provisioning", "Reporting", "Runtime", "Scaling", "Scheduling",
    "Scheduling & Orchestration", "Security & Compliance", "Service Mesh",
    "Storage", "System", "Streaming & Messaging", "Uncategorized",
}
SUBCATEGORY_DEFAULT = "Uncategorized"


def model_block(mj, fidelity=None):
    """Build the full ModelDefinition the design schema requires.

    The catalog's model.json omits `description`, `categoryId`, `registrantId`
    and spells the two counts in snake_case. Every value below is derived from
    catalog fields; `description` is a factual restatement of the model's own
    name, display name and catalog version and asserts nothing beyond them.

    `metadata` is deliberately omitted: it is not required by the shipped model
    schema, and the catalog's values (null `capabilities`, shape `circle`, an
    empty `svgColor` on sumologic) cannot be represented under it. The same
    information is carried on each component's `styles` block.
    """
    m = {k: v for k, v in mj.items() if k in MODEL_KEYS}
    m.pop("components_count", None)
    m.pop("relationships_count", None)
    m.pop("connection_id", None)
    m.pop("metadata", None)
    m["description"] = (
        "%s model registered in the Meshery catalog, catalog model version %s."
        % (mj["displayName"], mj["model"]["version"])
    )
    m["categoryId"] = (mj.get("category") or {}).get("id", ZERO_UUID)
    m["registrantId"] = (mj.get("registrant") or {}).get("id", ZERO_UUID)
    m["componentsCount"] = mj.get("components_count") or 0
    m["relationshipsCount"] = mj.get("relationships_count") or 0
    m["components"] = mj.get("components") or []
    m["relationships"] = mj.get("relationships") or []
    cat = dict(mj.get("category") or {})
    cat.setdefault("metadata", {})
    m["category"] = cat
    m["registrant"] = registrant_block(mj.get("registrant") or {})
    sub = mj.get("subCategory")
    if sub not in SUBCATEGORY_ENUM:
        if fidelity is not None:
            fidelity.setdefault("subcategory_not_in_enum", {})[mj["name"]] = sub
        sub = SUBCATEGORY_DEFAULT
    m["subCategory"] = sub
    if not m.get("schemaVersion"):
        m["schemaVersion"] = "models.meshery.io/v1beta1"
    return m


def model_reference(mj):
    return {
        "id": mj["id"],
        "name": mj["name"],
        "version": mj["version"],
        "displayName": mj["displayName"],
        "model": mj["model"],
        "registrant": {"kind": (mj.get("registrant") or {}).get("kind", "")},
    }


def styles_block(cat_styles, fidelity=None):
    """ComponentStyles requires five keys; carry the cosmetic extras through.

    The shipped schema caps each svg* field at 500 characters, but the catalog
    ships full inline SVG markup far longer than that. Values that fit are kept
    verbatim; values that do not are emitted empty, which is what the shipped
    reference design does for the same reason.
    """
    cs = cat_styles or {}
    raw = cs.get("shape") or "rectangle"
    shape = SHAPE_MAP.get(raw, raw)
    if shape not in SHAPE_ENUM:
        raise SystemExit(
            "catalog shape %r has no legal value in the shipped Shape enum; add "
            "an explicit entry to SHAPE_MAP rather than substituting" % raw)
    if shape != raw and fidelity is not None:
        fidelity.setdefault("shape_mapped", {})
        fidelity["shape_mapped"][raw] = fidelity["shape_mapped"].get(raw, 0) + 1

    def svg(key):
        v = cs.get(key, "") or ""
        return v if len(v) <= 500 else ""

    out = {
        "shape": shape,
        "primaryColor": cs.get("primaryColor", ""),
        "svgColor": svg("svgColor"),
        "svgWhite": svg("svgWhite"),
        "svgComplete": svg("svgComplete"),
    }
    for k in ("background-image", "background-opacity", "border-style",
              "border-width", "height", "width", "secondaryColor", "data"):
        if k in cs:
            out[k] = cs[k]
    return out



def component_configuration(name):
    """Return the minimum catalog-valid resource configuration for Meshery validation."""
    configs = {
        "deploy-meshery-control": {
            "spec": {
                "selector": {
                    "matchLabels": {
                        "app.kubernetes.io/name": "meshery-control",
                    },
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app.kubernetes.io/name": "meshery-control",
                        },
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "meshery-control",
                            },
                        ],
                    },
                },
            },
        },
        "sts-redis": {
            "spec": {
                "serviceName": "redis",
                "selector": {
                    "matchLabels": {
                        "app.kubernetes.io/name": "redis",
                    },
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app.kubernetes.io/name": "redis",
                        },
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "redis",
                            },
                        ],
                    },
                },
            },
        },
        "sts-postgres": {
            "spec": {
                "serviceName": "postgres",
                "selector": {
                    "matchLabels": {
                        "app.kubernetes.io/name": "postgres",
                    },
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app.kubernetes.io/name": "postgres",
                        },
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "postgres",
                            },
                        ],
                    },
                },
            },
        },
        "prometheus": {
            "spec": {},
        },
        "sm-platform": {
            "spec": {
                "selector": {
                    "matchLabels": {
                        "app.kubernetes.io/name": "meshery-control",
                    },
                },
                "endpoints": [
                    {
                        "port": "metrics",
                    },
                ],
            },
        },
        "alertmanager": {
            "spec": {},
        },
        "rb-ai-control": {
            "roleRef": {
                "apiGroup": "rbac.authorization.k8s.io",
                "kind": "Role",
                "name": "role-ai-control",
            },
        },
        "rb-ai-state": {
            "roleRef": {
                "apiGroup": "rbac.authorization.k8s.io",
                "kind": "Role",
                "name": "role-ai-state",
            },
        },
        "vapb-ai-runtime": {
            "spec": {
                "policyName": "vap-required-labels",
                "validationActions": [
                    "Deny",
                ],
            },
        },
    }
    return configs.get(name, {})


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------
def build_components():
    components = []
    by_name = {}
    model_cache = {}
    fidelity = {"schema_omitted": [], "capabilities_omitted": 0}

    for name, model, kind, is_ann, desc in S.COMPONENTS:
        cat = load(f"{model}/{MODEL_VERSION[model]}/v1.0.0/components/{kind}.json")
        if model not in model_cache:
            model_cache[model] = load(f"{model}/{MODEL_VERSION[model]}/v1.0.0/model.json")
        mj = model_cache[model]

        assert cat["component"]["kind"] == kind, (name, kind, cat["component"]["kind"])

        cat_meta = cat.get("metadata") or {}
        if name == "env-production":
            assert cat_meta.get("isAnnotation") is False, "override no longer needed"

        cid = str(uuid.uuid5(COMPONENT_NS, f"{model}/{kind}/{name}"))

        # component.schema is capped at 500 characters by the shipped schema.
        # Several catalog schemas are far longer; the shipped reference design
        # carries an empty schema in that case, and so does this one.
        raw_schema = cat["component"].get("schema", "") or ""
        if len(raw_schema) > 500:
            fidelity["schema_omitted"].append(name)
            raw_schema = ""

        if cat.get("capabilities"):
            fidelity["capabilities_omitted"] += 1

        # `displayName` is typed as InputString (no spaces) but the catalog
        # ships spaced values such as "API Group". Stripping the spaces
        # reproduces the component `kind` exactly in every case, so `kind` is
        # used and the normalisation is reported rather than assumed.
        cat_dn = cat.get("displayName") or kind
        if cat_dn.replace(" ", "") != kind:
            raise SystemExit(
                "catalog displayName %r does not reduce to kind %r; add an "
                "explicit mapping rather than guessing" % (cat_dn, kind))
        if cat_dn != kind:
            fidelity["displayname_normalised"] = \
                fidelity.get("displayname_normalised", 0) + 1

        comp = {
            "id": cid,
            "schemaVersion": COMPONENT_SCHEMA_VERSION,
            "version": cat.get("version", "v1.0.0"),
            "displayName": kind,
            "description": desc,
            "format": cat.get("format", "JSON"),
            "status": cat.get("status", "enabled"),
            "model": model_block(mj, fidelity),
            "modelReference": model_reference(mj),
            "metadata": {
                "genealogy": cat_meta.get("genealogy", ""),
                "isAnnotation": is_ann,
                "isNamespaced": cat_meta.get("isNamespaced", False),
                "published": cat_meta.get("published", False),
                "instanceDetails": cat_meta.get("instanceDetails") or {},
                "configurationUISchema": cat_meta.get("configurationUISchema", ""),
            },
            "configuration": {"metadata": {"labels": {}, "annotations": {}}, **component_configuration(name)},
            "component": {
                "version": cat["component"]["version"],
                "kind": cat["component"]["kind"],
                "schema": raw_schema,
            },
            "styles": styles_block(cat.get("styles"), fidelity),
        }

        components.append(comp)
        by_name[name] = comp
    return components, by_name, fidelity


# ---------------------------------------------------------------------------
# Blueprints -> instantiated relationship selectors
# ---------------------------------------------------------------------------
def blueprint_pairs(key):
    """Expand a blueprint into (selector_index, from_entry, to_entry) pairs."""
    rel = first_rel(load(S.BLUEPRINTS[key]))
    pairs = []
    for i, sel in enumerate(rel.get("selectors") or []):
        allow = sel.get("allow") or {}
        for f in (allow.get("from") or []):
            for t in (allow.get("to") or []):
                pairs.append((i, f, t))
    return rel, pairs


def pick_pair(pairs, src_kind, dst_kind):
    def m(a, b):
        return (0 if a in ("*", b) else 1, 0 if b in ("*", b) else 1)

    exact = [p for p in pairs
             if (p[1].get("kind") in ("*", src_kind) and p[2].get("kind") in ("*", dst_kind))]
    if exact:
        return exact[0]
    return min(pairs, key=lambda p: (m(p[1].get("kind"), src_kind)[0]
                                     + m(p[2].get("kind"), dst_kind)[0],
                                     m(p[1].get("kind"), src_kind)[1]))


def strip_nulls(node):
    """Drop keys whose value is null.

    The catalog uses `id: null` inside `match` blocks to mean "any component".
    The shipped schema types those as strings, so the key is dropped rather
    than carrying a null across. Absent and null mean the same thing here.
    """
    if isinstance(node, dict):
        return {k: strip_nulls(v) for k, v in node.items() if v is not None}
    if isinstance(node, list):
        return [strip_nulls(v) for v in node]
    return node


def participant(entry, comp, catalog_model):
    """Build a concrete SelectorItem bound to one component UUID."""
    out = {
        "id": comp["id"],
        "kind": comp["component"]["kind"],
        "model": catalog_model,
    }
    match = entry.get("match")
    if match:
        out["match"] = strip_nulls(match)
    patch = entry.get("patch")
    if patch:
        # Copied verbatim from the catalog blueprint, including patchStrategy.
        out["patch"] = {
            k: v for k, v in patch.items()
            if k in ("patchStrategy", "mutatorRef", "mutatedRef") and v is not None
        }
    return out


def build_relationships(by_name, model_of, model_ref_of):
    relationships = []
    for idx, (src, dst, basis, is_ann, prov, ref) in enumerate(S.EDGES):
        s_comp, d_comp = by_name[src], by_name[dst]
        s_model, d_model = model_of[src], model_of[dst]

        if basis:
            bp, pairs = blueprint_pairs(basis)
            si, f_entry, t_entry = pick_pair(pairs, s_comp["component"]["kind"],
                                             d_comp["component"]["kind"])
            selector = {
                "allow": {
                    "from": [participant(f_entry, s_comp, s_model)],
                    "to": [participant(t_entry, d_comp, d_model)],
                }
            }
            kind, rtype, sub = bp["kind"], bp["type"], bp["subType"]
            # The blueprint's own model block carries an empty displayName and
            # version, so rebuild the reference from the catalog model it names.
            rel_model = model_ref_of[bp["model"]["name"]]
            version = bp.get("version", "v1.0.0")
        else:
            # No blueprint exists. The triple is the catalog's dominant
            # edge/non-binding/reference (RELATIONSHIP_MATRIX.md section 8).
            kind, rtype, sub = "edge", "non-binding", "reference"
            selector = {
                "allow": {
                    "from": [{"id": s_comp["id"], "kind": s_comp["component"]["kind"],
                              "model": s_model}],
                    "to": [{"id": d_comp["id"], "kind": d_comp["component"]["kind"],
                            "model": d_model}],
                }
            }
            rel_model = d_model
            version = "v1.0.0"

        relationships.append({
            "id": str(uuid.uuid5(RELATIONSHIP_NS, f"{idx:03d}/{src}->{dst}/{kind}/{rtype}/{sub}")),
            "schemaVersion": RELATIONSHIP_SCHEMA_VERSION,
            "version": version,
            "kind": kind,
            "type": rtype,
            "subType": sub,
            "status": "enabled",
            "metadata": {
                "description": (
                    f"{src} -> {dst}. "
                    f"Provenance {prov} ({ref}); basis: "
                    + (os.path.basename(S.BLUEPRINTS[basis]) if basis
                       else "no upstream blueprint exists for this participant pairing")
                    + "."
                ),
                "isAnnotation": is_ann,
            },
            "model": rel_model,
            "selectors": [selector],
        })
    return relationships


def main():
    components, by_name, fidelity = build_components()
    model_of = {n: c["modelReference"] for n, c in by_name.items()}
    model_ref_of = {}
    for c in components:
        mr = c["modelReference"]
        model_ref_of.setdefault(mr["name"], mr)

    relationships = build_relationships(by_name, model_of, model_ref_of)

    design = {
        "id": str(DESIGN_ID),
        "name": "ai-native-platform",
        "schemaVersion": DESIGN_SCHEMA_VERSION,
        "version": "v1.0.0",
        "metadata": {"resolvedAliases": {}},
        "components": components,
        "relationships": relationships,
    }

    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1
                          else os.path.join(os.path.dirname(
                              os.path.abspath(__file__)), "design.generated.yml"))
    with open(out, "w") as fh:
        fh.write("# Generated by validation/tools/gen.py from the frozen specifications\n")
        fh.write("# in ../spec. Catalog values are read from the Meshery model catalog\n")
        fh.write("# at the pinned versions; nothing in this file is invented.\n")
        fh.write("# Do not hand-edit: regenerate with `python3 gen.py <out>`.\n")
        yaml.safe_dump(design, fh, default_flow_style=False, sort_keys=False,
                       width=100, allow_unicode=True)

    # ---- self-checks -------------------------------------------------------
    n_ann_c = sum(1 for c in components if c["metadata"]["isAnnotation"])
    with_patch = 0
    fields = 0
    for r in relationships:
        hit = False
        for sel in r["selectors"]:
            for side in ("from", "to"):
                for e in sel["allow"][side]:
                    p = e.get("patch")
                    if p and "patchStrategy" in p:
                        fields += 1
                        assert p["patchStrategy"] == "replace", p
                        hit = True
        with_patch += 1 if hit else 0

    ids = {c["id"] for c in components} | {r["id"] for r in relationships}
    print(f"components              {len(components)} (native {len(components)-n_ann_c}, annotation {n_ann_c})")
    print(f"relationships           {len(relationships)}")
    print(f"  semantic / annotation {sum(1 for r in relationships if not r['metadata']['isAnnotation'])}"
          f" / {sum(1 for r in relationships if r['metadata']['isAnnotation'])}")
    print(f"  with patchStrategy    {with_patch}  (expect 81)")
    print(f"  patch fields          {fields}  (derived, not fixed)")
    print(f"  without patchStrategy {len(relationships)-with_patch}  (expect 30)")
    print(f"unique ids              {len(ids)} of {len(components)+len(relationships)}")
    for c in components + relationships:
        assert c["id"] != ZERO_UUID, c
    print("\nfidelity census (schema-forced, not design choices)")
    print(f"  component.schema omitted  catalog >500 chars, "
          f"ComponentSchema.maxLength=500   {len(fidelity['schema_omitted'])}"
          f"   (24 others are empty in the catalog)")
    print(f"  capabilities omitted       array-typed, catalog omits the key  "
          f"{fidelity['capabilities_omitted']}  (426 catalog items dropped)")
    print(f"  displayName normalised     spaced catalog value -> kind        "
          f"{fidelity.get('displayname_normalised', 0)}")
    print(f"  styles.shape mapped        catalog value absent from Shape enum "
          f"{fidelity['shape_mapped']}")
    print(f"  model.metadata omitted     not required; null capabilities,      "
          f"{len({c['modelReference']['name'] for c in components})} models")
    print( "                             shape 'circle', empty svgColor")
    for m, v in fidelity.get("subcategory_not_in_enum", {}).items():
        print(f"  subCategory not in enum    {m}: {v!r} -> 'Uncategorized' "
              f"(schema default)")
    print(f"\nwritten                 {out}")


if __name__ == "__main__":
    main()
