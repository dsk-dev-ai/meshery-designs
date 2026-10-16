import sys
sys.path.insert(0, '.')
from validation.tools import spec_data as sd

# Check counts
assert len(sd.COMPONENTS) == 66
assert len(sd.EDGES) == 113

# Check PDBs are present
pdbs = [c for c in sd.COMPONENTS if c[2] == 'PodDisruptionBudget']
assert len(pdbs) == 2

# Check PDB namespace edges
pdbs_named = set()
for c in sd.COMPONENTS:
    if c[2] == 'PodDisruptionBudget':
        pdbs_named.add(c[0])
inv_edges = [e for e in sd.EDGES if e[2] == 'kmjea' and e[4] == 'B' and e[1] == 'ns-ai-state' and e[0] in pdbs_named]
assert len(inv_edges) == 2, f"Expected 2, got {len(inv_edges)}"

print('ok')
