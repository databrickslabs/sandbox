#!/usr/bin/env bash
# =============================================================================
# End-to-end validation test for ABAC module examples
# =============================================================================
# Validates each example config with:
#   1. validate_abac.py (structure, cross-refs, naming)
#   2. terraform validate (HCL syntax against provider schema)
#
# Usage:
#   ./test.sh              # run all checks
#   ./test.sh --skip-tf    # skip terraform validate (no init required)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SKIP_TF=false
for arg in "$@"; do
  case "$arg" in
    --skip-tf) SKIP_TF=true ;;
    -h|--help) echo "Usage: $0 [--skip-tf]"; exit 0 ;;
  esac
done

PASS=0
FAIL=0
ERRORS=""

report() {
  local status="$1"
  local msg="$2"
  if [ "$status" = "PASS" ]; then
    echo "  ✓ $msg"
    ((PASS++))
  else
    echo "  ✗ $msg"
    ((FAIL++))
    ERRORS="${ERRORS}\n  - ${msg}"
  fi
}

echo "============================================"
echo "  ABAC Module — End-to-End Validation"
echo "============================================"
echo ""

# --- Check prerequisites ---
if ! python3 -c "import hcl2" 2>/dev/null; then
  echo "ERROR: python-hcl2 is required. Install with: pip install python-hcl2"
  exit 2
fi

# --- Validate finance example ---
echo "--- Finance Example ---"
FINANCE_TFVARS="examples/finance/finance.tfvars.example"
FINANCE_SQL="examples/finance/0.1finance_abac_functions.sql"

if [ -f "$FINANCE_TFVARS" ]; then
  if python3 validate_abac.py "$FINANCE_TFVARS" "$FINANCE_SQL" > /dev/null 2>&1; then
    report "PASS" "finance: validate_abac.py passed"
  else
    report "FAIL" "finance: validate_abac.py failed"
  fi
else
  report "FAIL" "finance: $FINANCE_TFVARS not found"
fi

# --- Validate healthcare example ---
echo ""
echo "--- Healthcare Example ---"
HC_TFVARS="examples/healthcare/healthcare.tfvars.example"
HC_SQL="examples/healthcare/masking_functions.sql"

if [ -f "$HC_TFVARS" ]; then
  if [ -f "$HC_SQL" ]; then
    if python3 validate_abac.py "$HC_TFVARS" "$HC_SQL" > /dev/null 2>&1; then
      report "PASS" "healthcare: validate_abac.py passed"
    else
      report "FAIL" "healthcare: validate_abac.py failed"
    fi
  else
    if python3 validate_abac.py "$HC_TFVARS" > /dev/null 2>&1; then
      report "PASS" "healthcare: validate_abac.py passed (no SQL file)"
    else
      report "FAIL" "healthcare: validate_abac.py failed"
    fi
  fi
else
  report "FAIL" "healthcare: $HC_TFVARS not found"
fi

# --- Validate abac.auto.tfvars.example skeleton ---
echo ""
echo "--- Skeleton Example ---"
SKELETON_TFVARS="abac.auto.tfvars.example"

if [ -f "$SKELETON_TFVARS" ]; then
  if python3 validate_abac.py "$SKELETON_TFVARS" > /dev/null 2>&1; then
    report "PASS" "skeleton: validate_abac.py passed"
  else
    report "FAIL" "skeleton: validate_abac.py failed"
  fi
else
  report "FAIL" "skeleton: $SKELETON_TFVARS not found"
fi

# --- Terraform validate (requires terraform init) ---
if ! $SKIP_TF; then
  echo ""
  echo "--- Terraform Validate ---"

  TMPDIR_TF=$(mktemp -d)
  trap 'rm -rf "$TMPDIR_TF"' EXIT

  cp "$FINANCE_TFVARS" "$TMPDIR_TF/abac.auto.tfvars" 2>/dev/null || true
  cp auth.auto.tfvars.example "$TMPDIR_TF/auth.auto.tfvars" 2>/dev/null || true
  cp env.auto.tfvars.example "$TMPDIR_TF/env.auto.tfvars" 2>/dev/null || true

  if terraform -chdir="$SCRIPT_DIR" validate -no-color > "$TMPDIR_TF/tf_validate.log" 2>&1; then
    report "PASS" "terraform validate passed"
  else
    report "FAIL" "terraform validate failed (see output below)"
    cat "$TMPDIR_TF/tf_validate.log" | head -20
  fi
fi

# --- Summary ---
echo ""
echo "============================================"
TOTAL=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
  echo "  RESULT: ALL PASSED ($PASS/$TOTAL checks)"
else
  echo "  RESULT: $FAIL FAILED ($PASS passed, $FAIL failed)"
  echo -e "  Failures:$ERRORS"
fi
echo "============================================"

exit "$FAIL"
