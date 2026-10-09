#!/usr/bin/env bash
# Deploys the OpenSharing server as a Databricks App and plans the AWS side:
# 1. finds the HealthLake data stores and their Glue resource links
# 2. creates the recipient service principal Unity Catalog will authenticate as
# 3. deploys and starts the app (bundle)
# 4. reads the app's token claims and writes a Terraform plan for the IAM role
#    and Lake Formation grants. Apply it yourself after reviewing the trust policy.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ -f config.sh ]] || { echo "ERROR: copy config.example.sh to config.sh and fill it in" >&2; exit 1; }
source config.sh
mkdir -p .state

echo "=== 1/4 HealthLake data stores and their Glue resource links ==="
STORES_JSON=$(python3 - <<'PY'
import json, os, re, subprocess
def aws(*args):
    return json.loads(subprocess.run(["aws", *args, "--output", "json"], check=True, capture_output=True, text=True).stdout)
wanted = {s.strip() for s in os.environ.get("HEALTHLAKE_DATASTORES", "").split(",") if s.strip()}
stores, token = [], None
while True:
    page = aws("healthlake", "list-fhir-datastores", "--filter", "DatastoreStatus=ACTIVE", *(["--next-token", token] if token else []))
    for ds in page["DatastorePropertiesList"]:
        if wanted and ds["DatastoreName"] not in wanted:
            continue
        # HealthLake names its resource link <name>_<datastore id>_healthlake_view
        link = re.sub(r"[^a-z0-9_]", "_", ds["DatastoreName"].lower()) + f"_{ds['DatastoreId']}_healthlake_view"
        target = aws("glue", "get-database", "--name", link)["Database"]["TargetDatabase"]
        stores.append({"name": ds["DatastoreName"], "link_db": link,
                       "service_account": target["CatalogId"], "target_db": target["DatabaseName"]})
    token = page.get("NextToken")
    if not token:
        break
missing = wanted - {s["name"] for s in stores}
if missing:
    raise SystemExit(f"ERROR: no ACTIVE data store named {sorted(missing)}")
if not stores:
    raise SystemExit("ERROR: no ACTIVE HealthLake data stores in this account and region")
print(json.dumps(stores))
PY
)
echo "$STORES_JSON" > .state/stores.json
python3 -c "import json,sys; [print(f\"  {s['name']}: {s['link_db']} -> {s['service_account']}:{s['target_db']}\") for s in json.load(open('.state/stores.json'))]"

echo "=== 2/4 Recipient service principal (the identity Unity Catalog authenticates as) ==="
SP_ID=$(databricks service-principals list --filter "displayName eq $RECIPIENT_SP_NAME" -o json \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print(r[0]['id'] if r else '')")
if [[ -z "$SP_ID" ]]; then
  SP_ID=$(databricks service-principals create --display-name "$RECIPIENT_SP_NAME" -o json \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
fi
SP_APP_ID=$(databricks service-principals get "$SP_ID" -o json \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['applicationId'])")
echo "$SP_ID" > .state/recipient-sp-id
echo "$SP_APP_ID" > .state/recipient-client-id
echo "recipient: $RECIPIENT_SP_NAME ($SP_APP_ID)"

echo "=== 3/4 Deploy and start the app (bundle) ==="
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
# --var splits values on commas, so list-valued variables go through BUNDLE_VAR_*
export BUNDLE_VAR_app_name="$APP_NAME"
export BUNDLE_VAR_aws_region="$AWS_REGION"
export BUNDLE_VAR_aws_role_arns="arn:aws:iam::$ACCOUNT:role/${TF_VAR_name_prefix}-reader${ADDITIONAL_AWS_ROLE_ARNS:+,$ADDITIONAL_AWS_ROLE_ARNS}"
export BUNDLE_VAR_recipient_sp_application_id="$SP_APP_ID"
export BUNDLE_VAR_layout="$LAYOUT"
export BUNDLE_VAR_stores="$HEALTHLAKE_DATASTORES"
databricks bundle deploy
databricks bundle run healthlake_opensharing
APP_URL=$(databricks apps get "$APP_NAME" -o json | python3 -c "import json,sys; print(json.load(sys.stdin)['url'])")
echo "$APP_URL" > .state/app-url
databricks auth describe -o json | python3 -c "import json,sys; print(json.load(sys.stdin)['details']['host'])" > .state/workspace-url
echo "app: $APP_URL"

echo "=== 4/4 Terraform plan for the AWS side ==="
IDENTITY=""
for _ in $(seq 1 12); do
  IDENTITY=$(databricks apps logs "$APP_NAME" --tail-lines 500 2>/dev/null \
    | grep -o 'DATABRICKS_IDENTITY {.*}' | tail -1 | cut -d' ' -f2- || true)
  [[ -n "$IDENTITY" ]] && break
  sleep 10
done
[[ -n "$IDENTITY" ]] || { echo "ERROR: app never logged its DATABRICKS_IDENTITY line" >&2; exit 1; }
echo "app token claims: $IDENTITY"
python3 - "$IDENTITY" <<'PY' > terraform/terraform.tfvars.json
import json, os, sys
claims = json.loads(sys.argv[1])
aud = claims["aud"][0] if isinstance(claims["aud"], list) else claims["aud"]
stores = json.load(open(".state/stores.json"))
print(json.dumps({
    "aws_region": os.environ["AWS_REGION"],
    "oidc_issuer": claims["iss"],
    "oidc_audience": aud,
    "app_sp_client_id": claims["sub"],
    "healthlake_stores": [{k: s[k] for k in ("link_db", "service_account", "target_db")} for s in stores],
}))
PY
terraform -chdir=terraform init -input=false >/dev/null
terraform -chdir=terraform plan -input=false -out=tfplan

echo
echo "App deployed: $APP_URL/delta-sharing"
echo "Next: review the IAM trust policy in the plan above, then apply it:"
echo "  (source config.sh && terraform -chdir=terraform apply tfplan)"
echo "Then: bash scripts/configure-consumer.sh   (recipient secret, Unity Catalog provider + catalogs)"
echo "      bash scripts/verify.sh               (end-to-end check)"
