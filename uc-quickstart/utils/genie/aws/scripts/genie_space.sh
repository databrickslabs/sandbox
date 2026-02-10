#!/usr/bin/env bash
# =============================================================================
# Genie Space: create space with finance tables and/or set ACLs (single script)
# =============================================================================
# Commands:
#   create    Create a Genie Space with all finance schema tables and set ACLs
#             (POST /api/2.0/genie/spaces, then PUT permissions for five groups).
#   set-acls  Set CAN_RUN on an existing Genie Space for the five finance groups.
#
# Prerequisites: DATABRICKS_HOST, DATABRICKS_TOKEN; for create also GENIE_WAREHOUSE_ID.
# Get warehouse ID: terraform output -raw genie_warehouse_id
#
# Usage:
#   ./genie_space.sh create [workspace_url] [token] [title] [warehouse_id]
#   ./genie_space.sh set-acls [workspace_url] [token] [space_id]
#
# Or set env and run: ./genie_space.sh create   or   ./genie_space.sh set-acls
# Re-running create adds a new space each time (not idempotent).
# =============================================================================

set -e

GENIE_GROUPS=("Junior_Analyst" "Senior_Analyst" "US_Region_Staff" "EU_Region_Staff" "Compliance_Officer")

usage() {
  echo "Usage: $0 create [workspace_url] [token] [title] [warehouse_id]"
  echo "       $0 set-acls [workspace_url] [token] [space_id]"
  echo "  Or set DATABRICKS_HOST, DATABRICKS_TOKEN; for create set GENIE_WAREHOUSE_ID; for set-acls set GENIE_SPACE_OBJECT_ID"
  exit 1
}

# ---------- Set ACLs on a Genie Space (CAN_RUN for five groups) ----------
set_genie_acls() {
  local workspace_url="$1"
  local token="$2"
  local space_id="$3"
  workspace_url="${workspace_url%/}"

  local access_control=""
  for g in "${GENIE_GROUPS[@]}"; do
    access_control="${access_control}{\"group_name\": \"${g}\", \"permission_level\": \"CAN_RUN\"},"
  done
  access_control="[${access_control%,}]"

  local body="{\"access_control_list\": ${access_control}}"
  local path="/api/2.0/permissions/genie/${space_id}"

  echo "Putting permissions on Genie Space ${space_id} for groups: ${GENIE_GROUPS[*]}"
  local response
  response=$(curl -s -w "\n%{http_code}" -X PUT \
    -H "Authorization: Bearer ${token}" \
    -H "Content-Type: application/json" \
    -d "${body}" \
    "${workspace_url}${path}")

  local http_code
  http_code=$(echo "$response" | tail -n1)
  local response_body
  response_body=$(echo "$response" | sed '$d')

  if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
    echo "Request failed (HTTP ${http_code}). Check workspace URL, token, and Genie Space ID."
    echo "API response: ${response_body}"
    exit 1
  fi
  echo "Genie Space ACLs updated successfully."
}

# ---------- Create Genie Space with finance tables then set ACLs ----------
create_genie_space() {
  local workspace_url="$1"
  local token="$2"
  local title="$3"
  local warehouse_id="$4"
  workspace_url="${workspace_url%/}"

  local catalog="${GENIE_CATALOG:-fincat}"
  local schema="${GENIE_SCHEMA:-finance}"

  local finance_tables=(Accounts AMLAlerts AuditLogs CreditCards CustomerInteractions Customers TradingPositions Transactions)
  local sorted_identifiers=()
  while IFS= read -r id; do
    [[ -n "$id" ]] && sorted_identifiers+=("$id")
  done < <(for t in "${finance_tables[@]}"; do echo "${catalog}.${schema}.${t}"; done | LC_ALL=C sort)

  local tables_json=""
  for id in "${sorted_identifiers[@]}"; do
    tables_json="${tables_json}{\"identifier\": \"${id}\"},"
  done
  tables_json="[${tables_json%,}]"

  local serialized_space="{\"version\":1,\"data_sources\":{\"tables\":${tables_json}}}"
  local serialized_escaped
  serialized_escaped=$(echo "$serialized_space" | sed 's/\\/\\\\/g; s/"/\\"/g')
  local create_body="{\"warehouse_id\": \"${warehouse_id}\", \"title\": \"${title}\", \"serialized_space\": \"${serialized_escaped}\"}"

  local tables_display
  tables_display=$(printf '%s\n' "${sorted_identifiers[@]}" | sed "s|^${catalog}\\.${schema}\\.||" | tr '\n' ' ')
  echo "Creating Genie Space '${title}' with warehouse ${warehouse_id} and tables (sorted): ${tables_display}"

  local response
  response=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Authorization: Bearer ${token}" \
    -H "Content-Type: application/json" \
    -d "${create_body}" \
    "${workspace_url}/api/2.0/genie/spaces")

  local http_code
  http_code=$(echo "$response" | tail -n1)
  local response_body
  response_body=$(echo "$response" | sed '$d')

  if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
    echo "Create Genie Space failed (HTTP ${http_code})."
    echo "API response: ${response_body}"
    exit 1
  fi

  local space_id
  space_id=$(echo "$response_body" | grep -o '"space_id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')
  if [[ -z "$space_id" ]]; then
    space_id=$(echo "$response_body" | jq -r '.space_id // empty' 2>/dev/null)
  fi
  if [[ -z "$space_id" ]]; then
    echo "Created space but could not parse space_id from response. Response: ${response_body}"
    exit 1
  fi

  echo "Genie Space created: ${space_id}"
  echo "Setting ACLs for the five finance groups..."
  set_genie_acls "$workspace_url" "$token" "$space_id"
  echo "Done. Genie Space ID: ${space_id}"
}

# ---------- Main ----------
COMMAND="${1:-create}"
shift || true

if [[ "$COMMAND" == "create" ]]; then
  WORKSPACE_URL="${1:-${DATABRICKS_HOST}}"
  TOKEN="${2:-${DATABRICKS_TOKEN}}"
  TITLE="${3:-Finance Genie Space}"
  WAREHOUSE_ID="${4:-${GENIE_WAREHOUSE_ID}}"

  if [[ -z "$WORKSPACE_URL" || -z "$TOKEN" ]]; then
    echo "Need workspace URL and token. Usage: $0 create [workspace_url] [token] [title] [warehouse_id]"
    exit 1
  fi
  if [[ -z "$WAREHOUSE_ID" ]]; then
    echo "GENIE_WAREHOUSE_ID not set. Get it from: terraform output -raw genie_warehouse_id"
    exit 1
  fi
  create_genie_space "$WORKSPACE_URL" "$TOKEN" "$TITLE" "$WAREHOUSE_ID"

elif [[ "$COMMAND" == "set-acls" ]]; then
  WORKSPACE_URL="${1:-${DATABRICKS_HOST}}"
  TOKEN="${2:-${DATABRICKS_TOKEN}}"
  SPACE_ID="${3:-${GENIE_SPACE_OBJECT_ID}}"

  if [[ -z "$WORKSPACE_URL" || -z "$TOKEN" ]]; then
    echo "Need workspace URL and token. Usage: $0 set-acls [workspace_url] [token] [space_id]"
    exit 1
  fi
  if [[ -z "$SPACE_ID" ]]; then
    echo "Genie Space ID required. Set GENIE_SPACE_OBJECT_ID or pass as third argument."
    exit 1
  fi
  set_genie_acls "$WORKSPACE_URL" "$TOKEN" "$SPACE_ID"

else
  usage
fi
