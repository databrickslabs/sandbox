#!/usr/bin/env bash
# =============================================================================
# Set Genie Space ACLs (CAN VIEW, CAN RUN) for the five finance groups
# =============================================================================
# Uses the Databricks workspace REST API to grant permissions on the Genie Space.
# Run after the Genie Space exists. Replace GENIE_SPACE_OBJECT_ID with the
# actual space ID from the Genie UI or list API.
#
# Prerequisites: DATABRICKS_HOST and DATABRICKS_TOKEN set, or pass as arguments.
# Usage: ./set_genie_space_acls.sh [workspace_url] [token] [genie_space_id]
#
# References:
# - https://docs.databricks.com/aws/en/genie/set-up
# - https://community.databricks.com/t5/generative-ai/databricks-rest-api-to-manage-and-deploy-genie-spaces/td-p/107937
# - https://docs.databricks.com/api/workspace (Genie / permissions endpoints)
# =============================================================================

set -e

WORKSPACE_URL="${1:-${DATABRICKS_HOST}}"
TOKEN="${2:-${DATABRICKS_TOKEN}}"
GENIE_SPACE_ID="${3:-${GENIE_SPACE_OBJECT_ID}}"

if [[ -z "$WORKSPACE_URL" || -z "$TOKEN" ]]; then
  echo "Usage: $0 <workspace_url> <token> [genie_space_id]"
  echo "  Or set DATABRICKS_HOST, DATABRICKS_TOKEN, and optionally GENIE_SPACE_OBJECT_ID"
  exit 1
fi

if [[ -z "$GENIE_SPACE_ID" ]]; then
  echo "GENIE_SPACE_OBJECT_ID not set. Get the Genie Space ID from the Genie UI or API, then:"
  echo "  export GENIE_SPACE_OBJECT_ID=<space_id>"
  echo "  $0 '$WORKSPACE_URL' '<token>'"
  exit 1
fi

# Normalize workspace URL (no trailing slash)
WORKSPACE_URL="${WORKSPACE_URL%/}"

# Groups to grant CAN_VIEW and CAN_RUN
GROUPS=("Junior_Analyst" "Senior_Analyst" "US_Region_Staff" "EU_Region_Staff" "Compliance_Officer")

# Build access_control list JSON
ACCESS_CONTROL=""
for g in "${GROUPS[@]}"; do
  ACCESS_CONTROL="${ACCESS_CONTROL}{\"group_name\": \"${g}\", \"permission_level\": \"CAN_RUN\"},"
done
ACCESS_CONTROL="[${ACCESS_CONTROL%,}]"

BODY=$(cat <<EOF
{
  "access_control_list": ${ACCESS_CONTROL}
}
EOF
)

# Databricks Permissions API pattern for workspace objects.
# If Genie Space uses a different resource type (e.g. genie_spaces), adjust the path.
# See: https://docs.databricks.com/api/workspace/permissions
PERMISSIONS_PATH="/api/2.0/permissions/genie-spaces/${GENIE_SPACE_ID}"

echo "Putting permissions on Genie Space ${GENIE_SPACE_ID} for groups: ${GROUPS[*]}"
HTTP=$(curl -s -w "%{http_code}" -X PUT \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "${BODY}" \
  "${WORKSPACE_URL}${PERMISSIONS_PATH}")

HTTP_CODE="${HTTP: -3}"
if [[ "$HTTP_CODE" != "200" && "$HTTP_CODE" != "201" ]]; then
  echo "Request may have failed (HTTP ${HTTP_CODE}). Check workspace URL, token, and Genie Space ID."
  echo "If the permissions path for Genie Space differs, update PERMISSIONS_PATH in this script."
  exit 1
fi

echo "Genie Space ACLs updated successfully."
