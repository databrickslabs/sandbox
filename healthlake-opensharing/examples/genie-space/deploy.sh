#!/usr/bin/env bash
# Deploys the example Genie space to the consumer workspace.
# usage: bash examples/genie-space/deploy.sh <catalog>   (GENIE_WAREHOUSE_ID optional)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source ../../config.sh
CATALOG="${1:?usage: bash examples/genie-space/deploy.sh <catalog>}"

MIN="1.3.0"
VER=$(databricks version | sed 's/Databricks CLI v//')
if [[ "$(printf '%s\n%s\n' "$MIN" "$VER" | sort -V | head -1)" != "$MIN" ]]; then
  echo "ERROR: databricks CLI $VER < $MIN; genie_spaces bundle support needs >= $MIN" >&2
  exit 1
fi

WAREHOUSE_ID="${GENIE_WAREHOUSE_ID:-$(databricks warehouses list --profile "$CONSUMER_PROFILE" -o json \
  | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['id'])")}"

databricks bundle deploy --profile "$CONSUMER_PROFILE" --var="catalog=$CATALOG" --var="warehouse_id=$WAREHOUSE_ID"
echo "Genie space deployed. Find it with: databricks bundle summary --profile $CONSUMER_PROFILE --var=catalog=$CATALOG --var=warehouse_id=$WAREHOUSE_ID"
