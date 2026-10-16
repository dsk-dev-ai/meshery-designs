import subprocess
import sys
import tempfile
import os

d = tempfile.mkdtemp()
res = subprocess.run([sys.executable, 'validation/tools/gate1.py', 'generated/design.yml', d], cwd='.', capture_output=True, text=True)
assert res.returncode == 0
assert "GATE 1: PASS" in res.stdout
assert "UNEXPECTED                             0" in res.stdout
print('ok')
