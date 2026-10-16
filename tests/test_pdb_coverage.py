import yaml

d = yaml.safe_load(open('generated/design.yml'))
# namespaced components
namespaced = [c for c in d['components'] if c['metadata']['isNamespaced']]
# namespaces themselves
ns = {c['id'] for c in d['components'] if c['component']['kind'] == 'Namespace'}
# components that get namespace via inventory
inv_targets = set()
for r in d['relationships']:
    if r['kind']=='hierarchical' and r['subType']=='inventory' and r['type']=='parent':
        for s in r.get('selectors', []):
            for e in s['allow'].get('from', []):
                inv_targets.add(e['id'])
# namespaced but not namespaces
non_ns = [c for c in namespaced if c['id'] not in ns]
for c in non_ns:
    assert c['id'] in inv_targets, f"Missing namespace for {c['id']}"
print('ok', len(non_ns), 'covered')
