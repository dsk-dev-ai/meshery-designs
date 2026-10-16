import yaml

d = yaml.safe_load(open('generated/design.yml'))
assert len(d['components']) == 66
assert len(d['relationships']) == 113
# splits
sem = sum(1 for r in d['relationships'] if not r['metadata']['isAnnotation'])
ann = sum(1 for r in d['relationships'] if r['metadata']['isAnnotation'])
assert sem == 61 and ann == 52
# patches
patches = 0
for r in d['relationships']:
    for s in r.get('selectors', []):
        for side in ('from','to'):
            for e in s['allow'].get(side, []):
                if e.get('patch') and isinstance(e['patch'], dict) and e['patch'].get('patchStrategy'):
                    patches += 1
assert patches == 166
# namespace inventory
inv = sum(1 for r in d['relationships'] if r['kind']=='hierarchical' and r['subType']=='inventory' and r['type']=='parent')
assert inv == 31
# selector IDs
sids = 0
for r in d['relationships']:
    for s in r.get('selectors', []):
        for side in ('from','to'):
            for e in s['allow'].get(side, []):
                sids += 1
assert sids == 226
print('ok')
