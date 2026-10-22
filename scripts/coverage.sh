#!/usr/bin/env bash

set -eo pipefail

source .venv/bin/activate

package_name=$(echo "$1" | tr '-' '_')

# Run pytest with coverage reports, teeing text output for LLMs to read
mkdir -p htmlcov
coverage_status=0
pytest --cov="src/$package_name"    \
       --cov-report=html            \
       --cov-report=term-missing    \
       --cov-context=test . 2>&1    | tee htmlcov/coverage_report.txt || coverage_status=$?

# Extract just the missing coverage summary
grep -A 20 "Missing" htmlcov/coverage_report.txt > htmlcov/missing_coverage.txt || true
exit "$coverage_status"
