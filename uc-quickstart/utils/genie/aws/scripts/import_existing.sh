#!/usr/bin/env bash
# =============================================================================
# Import existing Databricks resources into Terraform state
# =============================================================================
# Imports groups, tag policies, and FGAC policies that already exist in
# Databricks so that Terraform can manage them without "already exists" errors.
#
# Prerequisites:
#   - auth.auto.tfvars configured with valid credentials
#   - abac.auto.tfvars configured with groups/tag_policies/fgac_policies
#   - terraform init already run
#
# Usage:
#   ./scripts/import_existing.sh              # import all resource types
#   ./scripts/import_existing.sh --groups-only # import only groups
#   ./scripts/import_existing.sh --tags-only   # import only tag policies
#   ./scripts/import_existing.sh --fgac-only   # import only FGAC policies
#   ./scripts/import_existing.sh --dry-run     # show commands without running
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

DRY_RUN=false
IMPORT_GROUPS=true
IMPORT_TAGS=true
IMPORT_FGAC=true

for arg in "$@"; do
  case "$arg" in
    --dry-run)     DRY_RUN=true ;;
    --groups-only) IMPORT_TAGS=false; IMPORT_FGAC=false ;;
    --tags-only)   IMPORT_GROUPS=false; IMPORT_FGAC=false ;;
    --fgac-only)   IMPORT_GROUPS=false; IMPORT_TAGS=false ;;
    -h|--help)
      echo "Usage: $0 [--dry-run] [--groups-only|--tags-only|--fgac-only]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: $0 [--dry-run] [--groups-only|--tags-only|--fgac-only]"
      exit 1
      ;;
  esac
done

cd "$MODULE_DIR"

if [ ! -f abac.auto.tfvars ]; then
  echo "ERROR: abac.auto.tfvars not found. Configure it before importing."
  exit 1
fi

if [ ! -d .terraform ]; then
  echo "ERROR: .terraform/ not found. Run 'terraform init' first."
  exit 1
fi

run_import() {
  local address="$1"
  local id="$2"

  if $DRY_RUN; then
    echo "  [DRY RUN] terraform import '$address' '$id'"
  else
    echo "  Importing: $address -> $id"
    if terraform import "$address" "$id" 2>&1; then
      echo "  ✓ Imported $address"
    else
      echo "  ✗ Failed to import $address (may not exist or already in state)"
    fi
  fi
}

# Extract group names from abac.auto.tfvars using grep/sed
extract_group_names() {
  python3 -c "
import hcl2, sys
with open('abac.auto.tfvars') as f:
    cfg = hcl2.load(f)
for name in cfg.get('groups', {}):
    print(name)
" 2>/dev/null || {
    echo "WARNING: Could not parse abac.auto.tfvars with python-hcl2." >&2
    echo "Install with: pip install python-hcl2" >&2
  }
}

extract_tag_keys() {
  python3 -c "
import hcl2, sys
with open('abac.auto.tfvars') as f:
    cfg = hcl2.load(f)
for tp in cfg.get('tag_policies', []):
    print(tp.get('key', ''))
" 2>/dev/null || {
    echo "WARNING: Could not parse abac.auto.tfvars with python-hcl2." >&2
  }
}

extract_fgac_names() {
  python3 -c "
import hcl2, sys
with open('abac.auto.tfvars') as f:
    cfg = hcl2.load(f)
for p in cfg.get('fgac_policies', []):
    name = p.get('name', '')
    catalog = p.get('catalog', '')
    if name and catalog:
        print(name + '|' + catalog + '_' + name)
" 2>/dev/null || {
    echo "WARNING: Could not parse tfvars files with python-hcl2." >&2
  }
}

echo "============================================"
echo "  Import Existing Resources into Terraform"
echo "============================================"
echo ""

imported=0
skipped=0

if $IMPORT_GROUPS; then
  echo "--- Groups ---"
  group_names=$(extract_group_names)
  if [ -z "$group_names" ]; then
    echo "  No groups found in abac.auto.tfvars."
  else
    while IFS= read -r name; do
      [ -z "$name" ] && continue
      run_import "databricks_group.groups[\"$name\"]" "$name"
      ((imported++)) || true
    done <<< "$group_names"
  fi
  echo ""
fi

if $IMPORT_TAGS; then
  echo "--- Tag Policies ---"
  tag_keys=$(extract_tag_keys)
  if [ -z "$tag_keys" ]; then
    echo "  No tag policies found in abac.auto.tfvars."
  else
    while IFS= read -r key; do
      [ -z "$key" ] && continue
      run_import "databricks_tag_policy.policies[\"$key\"]" "$key"
      ((imported++)) || true
    done <<< "$tag_keys"
  fi
  echo ""
fi

if $IMPORT_FGAC; then
  echo "--- FGAC Policies ---"
  fgac_entries=$(extract_fgac_names)
  if [ -z "$fgac_entries" ]; then
    echo "  No FGAC policies found in abac.auto.tfvars."
  else
    while IFS='|' read -r policy_key policy_name; do
      [ -z "$policy_key" ] && continue
      run_import "databricks_policy_info.policies[\"$policy_key\"]" "$policy_name"
      ((imported++)) || true
    done <<< "$fgac_entries"
  fi
  echo ""
fi

echo "============================================"
if $DRY_RUN; then
  echo "  Dry run complete. $imported import(s) would be attempted."
else
  echo "  Done. $imported import(s) attempted."
fi
echo "  Next: terraform plan (to verify state is consistent)"
echo "============================================"
