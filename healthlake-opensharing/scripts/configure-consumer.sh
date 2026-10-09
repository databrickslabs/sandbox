#!/usr/bin/env bash
# Mounts the app's shares in Unity Catalog on the consumer workspace:
# 1. creates the recipient service principal's OAuth secret (once)
# 2. registers the app as an OpenSharing provider. Its token endpoint is the
#    hosting workspace's own OIDC endpoint, and the Apps gateway accepts that
#    token, so the server mints none itself
# 3. creates one catalog per share the server lists (<CATALOG_PREFIX><share>)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source config.sh
WORKSPACE_URL=$(cat .state/workspace-url)
APP_URL=$(cat .state/app-url)

if [[ ! -s .state/recipient-secret ]]; then
  (umask 077; databricks service-principal-secrets-proxy create "$(cat .state/recipient-sp-id)" -o json \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['secret'])" > .state/recipient-secret)
  echo "recipient secret created"
fi

PROFILE_STR=$(python3 - "$APP_URL" "$WORKSPACE_URL" <<'PY'
import json, sys
app_url, workspace = sys.argv[1:3]
print(json.dumps(json.dumps({
    "shareCredentialsVersion": 2,
    "type": "oauth_client_credentials",
    "endpoint": f"{app_url}/delta-sharing",
    "tokenEndpoint": f"{workspace}/oidc/v1/token",
    "clientId": open(".state/recipient-client-id").read().strip(),
    "clientSecret": open(".state/recipient-secret").read().strip(),
    "scope": "all-apis",
})))
PY
)

if databricks api get "/api/2.1/unity-catalog/providers/$PROVIDER_NAME" --profile "$CONSUMER_PROFILE" >/dev/null 2>&1; then
  databricks api patch "/api/2.1/unity-catalog/providers/$PROVIDER_NAME" --profile "$CONSUMER_PROFILE" \
    --json "{\"recipient_profile_str\": $PROFILE_STR}" >/dev/null
  echo "provider $PROVIDER_NAME updated"
else
  databricks api post /api/2.1/unity-catalog/providers --profile "$CONSUMER_PROFILE" --json "{
    \"name\": \"$PROVIDER_NAME\",
    \"authentication_type\": \"OAUTH_CLIENT_CREDENTIALS\",
    \"recipient_profile_str\": $PROFILE_STR,
    \"comment\": \"AWS HealthLake via OpenSharing, served from a Databricks App\"
  }" >/dev/null
  echo "provider $PROVIDER_NAME created"
fi

TOKEN=$(curl -sf -u "$(cat .state/recipient-client-id):$(cat .state/recipient-secret)" \
  "$WORKSPACE_URL/oidc/v1/token" -d "grant_type=client_credentials&scope=all-apis" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")
SHARES=$(curl -sf -H "Authorization: Bearer $TOKEN" "$APP_URL/delta-sharing/shares" \
  | python3 -c "import json,sys; print(' '.join(s['name'] for s in json.load(sys.stdin)['items']))")
[[ -n "$SHARES" ]] || { echo "ERROR: the server lists no shares; check the app logs" >&2; exit 1; }

for SHARE in $SHARES; do
  CATALOG="${CATALOG_PREFIX}${SHARE}"
  if databricks api get "/api/2.1/unity-catalog/catalogs/$CATALOG" --profile "$CONSUMER_PROFILE" >/dev/null 2>&1; then
    echo "catalog $CATALOG exists"
    continue
  fi
  databricks api post /api/2.1/unity-catalog/catalogs --profile "$CONSUMER_PROFILE" --json "{
    \"name\": \"$CATALOG\",
    \"provider_name\": \"$PROVIDER_NAME\",
    \"share_name\": \"$SHARE\",
    \"comment\": \"AWS HealthLake FHIR via OpenSharing (no copy; Lake Formation credential vending)\"
  }" >/dev/null
  echo "catalog $CATALOG created"
done
echo "$SHARES" | tr ' ' '\n' > .state/shares

echo
echo "Grant access with Unity Catalog, e.g.: GRANT USE CATALOG, USE SCHEMA, SELECT ON CATALOG <catalog> TO \`clinical-analysts\`"
