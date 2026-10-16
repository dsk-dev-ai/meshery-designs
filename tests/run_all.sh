#!/bin/bash
set -e
python3 /tmp/test_spec_data.py
python3 /tmp/test_counts.py
python3 /tmp/test_pdb_coverage.py
python3 /tmp/test_gen_repro.py
python3 /tmp/test_verify.py
python3 /tmp/test_gate1.py
echo "ALL TESTS PASSED"
