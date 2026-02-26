#!/usr/bin/env bash
# =============================================================================
# Genie Space: create / set-acls / trash
# =============================================================================
# Commands:
#   create    Create a Genie Space with configured tables and set ACLs.
#             Wildcards (catalog.schema.*) are expanded via the UC Tables API.
#             (POST /api/2.0/genie/spaces, then PUT permissions for groups).
#   set-acls  Set CAN_RUN on an existing Genie Space for the configured groups.
#   trash     Move a Genie Space to trash. Reads space_id from GENIE_ID_FILE.
#
# Authentication (in order of precedence):
#   1. DATABRICKS_TOKEN (PAT) - if set, used directly
#   2. DATABRICKS_CLIENT_ID + DATABRICKS_CLIENT_SECRET (Service Principal OAuth M2M)
#      - Requires DATABRICKS_HOST to be set for token endpoint
#
# Configuration:
#   GENIE_GROUPS_CSV     Required for create/set-acls. Comma-separated group names.
#   GENIE_TABLES_CSV     Required for create. Comma-separated fully-qualified
#                        table names (catalog.schema.table). Wildcards (catalog.schema.*)
#                        are expanded via the UC Tables API.
#   GENIE_WAREHOUSE_ID   Warehouse ID for create. Falls back to sql_warehouse_id
#                        in auth.auto.tfvars if not set.
#   GENIE_TITLE          Optional. Title for the new Genie Space (default: "ABAC Genie Space").
#   GENIE_DESCRIPTION    Optional. Description for the new Genie Space.
#   GENIE_ID_FILE        Optional. File path to save the created space ID
#                        (used by Terraform for lifecycle management).
#
# Usage:
#   ./genie_space.sh create [workspace_url] [token] [title] [warehouse_id]
#   ./genie_space.sh set-acls [workspace_url] [token] [space_id]
#   ./genie_space.sh trash
#
# Or set env and run: ./genie_space.sh create   or   ./genie_space.sh set-acls
# Re-running create adds a new space each time (not idempotent).
# =============================================================================

set -e

usage() {
  echo "Usage: $0 create [workspace_url] [token] [title] [warehouse_id]"
  echo "       $0 set-acls [workspace_url] [token] [space_id]"
  echo "       $0 trash"
  echo "  Or set DATABRICKS_HOST + DATABRICKS_TOKEN (or DATABRICKS_CLIENT_ID + DATABRICKS_CLIENT_SECRET)"
  echo "  For create: set GENIE_WAREHOUSE_ID; for set-acls: set GENIE_SPACE_OBJECT_ID"
  exit 1
}

# ---------- Get OAuth token from Service Principal credentials ----------
get_sp_token() {
  local workspace_url="$1"
  local client_id="$2"
  local client_secret="$3"
  workspace_url="${workspace_url%/}"

  local token_endpoint="${workspace_url}/oidc/v1/token"

  local response
  response=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials&client_id=${client_id}&client_secret=${client_secret}&scope=all-apis" \
    "${token_endpoint}")

  local http_code
  http_code=$(echo "$response" | tail -n1)
  local response_body
  response_body=$(echo "$response" | sed '$d')

  if [[ "$http_code" != "200" ]]; then
    echo "Failed to get OAuth token (HTTP ${http_code}). Check client_id/client_secret and workspace URL." >&2
    echo "Response: ${response_body}" >&2
    return 1
  fi

  local token
  token=$(echo "$response_body" | grep -o '"access_token"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')
  if [[ -z "$token" ]]; then
    token=$(echo "$response_body" | jq -r '.access_token // empty' 2>/dev/null)
  fi

  if [[ -z "$token" ]]; then
    echo "Could not parse access_token from OAuth response." >&2
    return 1
  fi

  echo "$token"
}

# ---------- Resolve token: use DATABRICKS_TOKEN or get from SP credentials ----------
resolve_token() {
  local workspace_url="$1"
  local explicit_token="$2"

  if [[ -n "$explicit_token" ]]; then
    echo "$explicit_token"
    return 0
  fi

  if [[ -n "${DATABRICKS_TOKEN:-}" ]]; then
    echo "$DATABRICKS_TOKEN"
    return 0
  fi

  if [[ -n "${DATABRICKS_CLIENT_ID:-}" && -n "${DATABRICKS_CLIENT_SECRET:-}" ]]; then
    echo "Using Service Principal OAuth M2M authentication..." >&2
    get_sp_token "$workspace_url" "$DATABRICKS_CLIENT_ID" "$DATABRICKS_CLIENT_SECRET"
    return $?
  fi

  echo "No authentication found. Set DATABRICKS_TOKEN or DATABRICKS_CLIENT_ID + DATABRICKS_CLIENT_SECRET." >&2
  return 1
}

# ---------- Read sql_warehouse_id from auth.auto.tfvars (fallback) ----------
read_warehouse_from_tfvars() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local tfvars="${script_dir}/../auth.auto.tfvars"
  if [[ -f "$tfvars" ]]; then
    grep -E '^\s*sql_warehouse_id\s*=' "$tfvars" \
      | sed 's/.*=\s*"\(.*\)".*/\1/' \
      | head -1
  fi
}

# ---------- Expand wildcard table entries via UC Tables API ----------
expand_tables() {
  local workspace_url="$1"
  local token="$2"
  local tables_csv="$3"
  workspace_url="${workspace_url%/}"

  IFS=',' read -ra RAW_ENTRIES <<< "$tables_csv"
  local expanded=()

  for entry in "${RAW_ENTRIES[@]}"; do
    entry=$(echo "$entry" | xargs)  # trim whitespace
    if [[ "$entry" == *.* && "$entry" == *.\* ]]; then
      # Wildcard: catalog.schema.*
      local catalog schema
      catalog=$(echo "$entry" | cut -d. -f1)
      schema=$(echo "$entry" | cut -d. -f2)
      echo "Expanding wildcard ${entry} via UC Tables API..." >&2

      local api_url="${workspace_url}/api/2.1/unity-catalog/tables?catalog_name=${catalog}&schema_name=${schema}"
      local resp
      resp=$(curl -s -H "Authorization: Bearer ${token}" "${api_url}")

      local table_names
      table_names=$(echo "$resp" | grep -o '"full_name"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')
      if [[ -z "$table_names" ]]; then
        table_names=$(echo "$resp" | jq -r '.tables[]?.full_name // empty' 2>/dev/null)
      fi

      if [[ -z "$table_names" ]]; then
        echo "WARNING: No tables found for ${catalog}.${schema}.* — skipping wildcard." >&2
        continue
      fi

      while IFS= read -r tbl; do
        [[ -n "$tbl" ]] && expanded+=("$tbl")
      done <<< "$table_names"
      echo "  Expanded to ${#expanded[@]} table(s) from ${catalog}.${schema}" >&2
    else
      expanded+=("$entry")
    fi
  done

  local IFS=','
  echo "${expanded[*]}"
}

# ---------- Set ACLs on a Genie Space (CAN_RUN for configured groups) ----------
set_genie_acls() {
  local workspace_url="$1"
  local token="$2"
  local space_id="$3"
  workspace_url="${workspace_url%/}"

  IFS=',' read -ra GENIE_GROUPS <<< "${GENIE_GROUPS_CSV}"

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

# ---------- Create Genie Space with configured tables then set ACLs ----------
create_genie_space() {
  local workspace_url="$1"
  local token="$2"
  local title="${3:-${GENIE_TITLE:-ABAC Genie Space}}"
  local warehouse_id="$4"
  workspace_url="${workspace_url%/}"

  if [[ -z "${GENIE_TABLES_CSV:-}" ]]; then
    echo "ERROR: GENIE_TABLES_CSV not set. Pass comma-separated fully-qualified table names." >&2
    echo "  Example: GENIE_TABLES_CSV='cat.schema.t1,cat.schema.t2' $0 create" >&2
    exit 1
  fi

  # Expand wildcards before building the API payload
  local resolved_csv
  resolved_csv=$(expand_tables "$workspace_url" "$token" "$GENIE_TABLES_CSV")
  IFS=',' read -ra TABLE_LIST <<< "$resolved_csv"

  local sorted_identifiers=()
  while IFS= read -r id; do
    [[ -n "$id" ]] && sorted_identifiers+=("$id")
  done < <(printf '%s\n' "${TABLE_LIST[@]}" | LC_ALL=C sort)

  if [[ ${#sorted_identifiers[@]} -eq 0 ]]; then
    echo "ERROR: No tables resolved after wildcard expansion. Nothing to create." >&2
    exit 1
  fi

  local tables_json=""
  for id in "${sorted_identifiers[@]}"; do
    tables_json="${tables_json}{\"identifier\": \"${id}\"},"
  done
  tables_json="[${tables_json%,}]"

  local serialized_space="{\"version\":1,\"data_sources\":{\"tables\":${tables_json}}}"
  local serialized_escaped
  serialized_escaped=$(echo "$serialized_space" | sed 's/\\/\\\\/g; s/"/\\"/g')

  # Build create body with optional description
  local description="${GENIE_DESCRIPTION:-}"
  local create_body
  if [[ -n "$description" ]]; then
    create_body="{\"warehouse_id\": \"${warehouse_id}\", \"title\": \"${title}\", \"description\": \"${description}\", \"serialized_space\": \"${serialized_escaped}\"}"
  else
    create_body="{\"warehouse_id\": \"${warehouse_id}\", \"title\": \"${title}\", \"serialized_space\": \"${serialized_escaped}\"}"
  fi

  local tables_display
  tables_display=$(printf '%s\n' "${sorted_identifiers[@]}" | tr '\n' ' ')
  echo "Creating Genie Space '${title}' with warehouse ${warehouse_id} and ${#sorted_identifiers[@]} tables: ${tables_display}"

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

  # Save space_id to file for Terraform lifecycle (destroy)
  if [[ -n "${GENIE_ID_FILE:-}" ]]; then
    echo "$space_id" > "$GENIE_ID_FILE"
    echo "Space ID saved to ${GENIE_ID_FILE}"
  fi

  echo "Setting ACLs for groups..."
  set_genie_acls "$workspace_url" "$token" "$space_id"
  echo "Done. Genie Space ID: ${space_id}"
}

# ---------- Trash (delete) a Genie Space ----------
trash_genie_space() {
  local workspace_url="${DATABRICKS_HOST}"
  workspace_url="${workspace_url%/}"

  if [[ -z "$workspace_url" ]]; then
    echo "Need workspace URL. Set DATABRICKS_HOST." >&2
    exit 1
  fi

  local token
  token=$(resolve_token "$workspace_url" "") || exit 1

  local space_id=""

  # Read space_id from the ID file
  if [[ -n "${GENIE_ID_FILE:-}" && -f "${GENIE_ID_FILE}" ]]; then
    space_id=$(cat "${GENIE_ID_FILE}" | tr -d '[:space:]')
  fi

  if [[ -z "$space_id" ]]; then
    echo "No Genie Space ID file found at ${GENIE_ID_FILE:-<not set>}. Nothing to trash."
    exit 0
  fi

  echo "Trashing Genie Space ${space_id}..."
  local response
  response=$(curl -s -w "\n%{http_code}" -X DELETE \
    -H "Authorization: Bearer ${token}" \
    "${workspace_url}/api/2.0/genie/spaces/${space_id}")

  local http_code
  http_code=$(echo "$response" | tail -n1)
  local response_body
  response_body=$(echo "$response" | sed '$d')

  if [[ "$http_code" == "200" || "$http_code" == "204" ]]; then
    echo "Genie Space ${space_id} trashed successfully."
    rm -f "${GENIE_ID_FILE}"
  elif [[ "$http_code" == "404" ]]; then
    echo "Genie Space ${space_id} not found (already deleted). Cleaning up ID file."
    rm -f "${GENIE_ID_FILE}"
  else
    echo "Failed to trash Genie Space (HTTP ${http_code})."
    echo "API response: ${response_body}"
    exit 1
  fi
}

# ---------- Main ----------
COMMAND="${1:-create}"
shift || true

if [[ "$COMMAND" == "create" ]]; then
  WORKSPACE_URL="${1:-${DATABRICKS_HOST}}"
  EXPLICIT_TOKEN="${2:-}"
  TITLE="${3:-${GENIE_TITLE:-ABAC Genie Space}}"
  WAREHOUSE_ID="${4:-${GENIE_WAREHOUSE_ID:-}}"

  if [[ -z "$WORKSPACE_URL" ]]; then
    echo "Need workspace URL. Set DATABRICKS_HOST or pass as first argument."
    exit 1
  fi

  TOKEN=$(resolve_token "$WORKSPACE_URL" "$EXPLICIT_TOKEN") || exit 1

  if [[ -z "$WAREHOUSE_ID" ]]; then
    WAREHOUSE_ID=$(read_warehouse_from_tfvars)
  fi
  if [[ -z "$WAREHOUSE_ID" ]]; then
    echo "No warehouse ID found. Set GENIE_WAREHOUSE_ID, pass as argument, or configure sql_warehouse_id in auth.auto.tfvars."
    exit 1
  fi

  # Require groups for create
  if [[ -z "${GENIE_GROUPS_CSV:-}" ]]; then
    echo "ERROR: GENIE_GROUPS_CSV not set. Pass comma-separated group names." >&2
    echo "  Example: GENIE_GROUPS_CSV='Analyst,Admin' $0 create" >&2
    exit 1
  fi

  create_genie_space "$WORKSPACE_URL" "$TOKEN" "$TITLE" "$WAREHOUSE_ID"

elif [[ "$COMMAND" == "set-acls" ]]; then
  WORKSPACE_URL="${1:-${DATABRICKS_HOST}}"
  EXPLICIT_TOKEN="${2:-}"
  SPACE_ID="${3:-${GENIE_SPACE_OBJECT_ID:-}}"

  if [[ -z "$WORKSPACE_URL" ]]; then
    echo "Need workspace URL. Set DATABRICKS_HOST or pass as first argument."
    exit 1
  fi

  TOKEN=$(resolve_token "$WORKSPACE_URL" "$EXPLICIT_TOKEN") || exit 1

  if [[ -z "$SPACE_ID" ]]; then
    echo "Genie Space ID required. Set GENIE_SPACE_OBJECT_ID or pass as third argument."
    exit 1
  fi

  # Require groups for set-acls
  if [[ -z "${GENIE_GROUPS_CSV:-}" ]]; then
    echo "ERROR: GENIE_GROUPS_CSV not set. Pass comma-separated group names." >&2
    echo "  Example: GENIE_GROUPS_CSV='Analyst,Admin' $0 set-acls" >&2
    exit 1
  fi

  set_genie_acls "$WORKSPACE_URL" "$TOKEN" "$SPACE_ID"

elif [[ "$COMMAND" == "trash" ]]; then
  trash_genie_space

else
  usage
fi
