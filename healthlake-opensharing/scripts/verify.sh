#!/usr/bin/env bash
# End-to-end check: workspace OIDC token -> Apps gateway -> share and table
# listing -> query (Lake Formation vending) -> anonymous download of a presigned
# data file -> SELECT through Unity Catalog on the consumer workspace.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source config.sh
WORKSPACE_URL=$(cat .state/workspace-url)
ENDPOINT="$(cat .state/app-url)/delta-sharing"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "=== 1/5 Token from the hosting workspace's OIDC endpoint (recipient SP, scope all-apis) ==="
TOKEN=$(curl -sf -u "$(cat .state/recipient-client-id):$(cat .state/recipient-secret)" \
  "$WORKSPACE_URL/oidc/v1/token" -d "grant_type=client_credentials&scope=all-apis" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")
echo "token issued"

echo "=== 2/5 Shares and tables through the Apps gateway ==="
SHARE=$(curl -sf -H "Authorization: Bearer $TOKEN" "$ENDPOINT/shares" \
  | python3 -c "import json,sys; s=[x['name'] for x in json.load(sys.stdin)['items']]; print(len(s), 'share(s):', ' '.join(s), file=sys.stderr); print(s[0])")
curl -sf -H "Authorization: Bearer $TOKEN" "$ENDPOINT/shares/$SHARE/all-tables" > "$TMP/tables.json"
read -r SCHEMA TABLE < <(python3 - "$TMP/tables.json" <<'PY'
import json, sys
items = json.load(open(sys.argv[1]))["items"]
print(f"{len(items)} tables in the first share", file=sys.stderr)
pick = next((t for t in items if t["name"] == "patient"), items[0])
print(pick["schema"], pick["name"])
PY
)

echo "=== 3/5 Query $SHARE.$SCHEMA.$TABLE (Lake Formation vending) ==="
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{}' \
  -w '\nHTTP %{http_code} in %{time_total}s\n' \
  "$ENDPOINT/shares/$SHARE/schemas/$SCHEMA/tables/$TABLE/query" > "$TMP/query.ndjson"
tail -1 "$TMP/query.ndjson"
python3 - "$TMP" <<'PY'
import json, sys
lines = [json.loads(l) for l in open(f"{sys.argv[1]}/query.ndjson").read().splitlines()[:-1] if l.strip()]
if "errorCode" in lines[0]:
    raise SystemExit(f"query failed: {lines[0]}")
files = [l["file"] for l in lines if "file" in l]
print(f"response: {[next(iter(l)) for l in lines[:2]]} + {len(files)} file(s)")
if not files:
    raise SystemExit("table has no data files yet; pick a table with data")
open(f"{sys.argv[1]}/presigned.txt", "w").write(files[0]["url"])
PY

echo "=== 4/5 Anonymous download of a presigned data file ==="
curl -sf -o "$TMP/sample.parquet" "$(cat "$TMP/presigned.txt")"
head -c 4 "$TMP/sample.parquet" | grep -q PAR1 \
  && echo "valid Parquet ($(wc -c < "$TMP/sample.parquet" | tr -d ' ') bytes)"

CATALOG="${CATALOG_PREFIX}${SHARE}"
echo "=== 5/5 SELECT through Unity Catalog ($CONSUMER_PROFILE: $CATALOG.$SCHEMA.$TABLE) ==="
if databricks api get "/api/2.1/unity-catalog/catalogs/$CATALOG" --profile "$CONSUMER_PROFILE" >/dev/null 2>&1; then
  WH=$(databricks warehouses list --profile "$CONSUMER_PROFILE" -o json \
    | python3 -c "import json,sys; w=json.load(sys.stdin); print(next((x['id'] for x in w if x['state']=='RUNNING'), w[0]['id']))")
  databricks api post /api/2.0/sql/statements --profile "$CONSUMER_PROFILE" --json "{
    \"warehouse_id\": \"$WH\", \"wait_timeout\": \"50s\",
    \"statement\": \"SELECT count(*) AS row_count FROM $CATALOG.$SCHEMA.$TABLE\"
  }" | python3 -c "
import json,sys
r=json.load(sys.stdin)
print('state:', r.get('status',{}).get('state'), (r.get('result') or {}).get('data_array') or r.get('status',{}).get('error'))"
else
  echo "catalog $CATALOG not found on $CONSUMER_PROFILE; run bash scripts/configure-consumer.sh first"
fi

echo
echo "verification complete"
