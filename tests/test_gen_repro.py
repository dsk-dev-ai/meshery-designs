import subprocess
import sys
import tempfile
import os
import hashlib

d = tempfile.mktemp(suffix='.yml')
try:
    res = subprocess.run([sys.executable, 'validation/tools/gen.py', d], cwd='.', capture_output=True, text=True)
    assert res.returncode == 0
    # compare
    with open('generated/design.yml','rb') as a, open(d,'rb') as b:
        assert a.read() == b.read()
    print('ok')
finally:
    try: os.remove(d)
    except: pass
