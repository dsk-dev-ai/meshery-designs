#!/bin/bash
set -e
cd "$(dirname "$0")/.."
python3 tests/test_spec_data.py
python3 tests/test_counts.py
python3 tests/test_pdb_coverage.py
python3 tests/test_gen_repro.py
python3 tests/test_verify.py
python3 tests/test_gate1.py
echo "ALL TESTS PASSED"
