import subprocess
import sys

# run verify on generated
res = subprocess.run([sys.executable, 'validation/tools/verify.py', 'generated/design.yml'], cwd='.', capture_output=True, text=True)
assert res.returncode == 0
assert "28 checks, 0 failed" in res.stdout
print('ok')
