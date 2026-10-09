#!/usr/bin/env bash
# OPTIONAL: creates a demo HealthLake data store preloaded with synthetic
# (Synthea) FHIR data. Creation takes ~25 minutes; the Iceberg tables fill in
# over the following ~15 minutes. Idempotent.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source config.sh
HEALTHLAKE_DATASTORE_NAME="${1:?usage: bash scripts/create-test-datastore.sh <data store name>}"

DATASTORE_ID=$(aws healthlake list-fhir-datastores \
  --query "DatastorePropertiesList[?DatastoreName=='$HEALTHLAKE_DATASTORE_NAME' && DatastoreStatus!='DELETED'].DatastoreId | [0]" \
  --output text)
if [[ "$DATASTORE_ID" == "None" || -z "$DATASTORE_ID" ]]; then
  echo "creating data store '$HEALTHLAKE_DATASTORE_NAME' (Synthea preload)..."
  TAGS=$(python3 -c "
import json, os
tags = json.loads(os.environ.get('TF_VAR_tags', '{}'))
print(json.dumps([{'Key': k, 'Value': v} for k, v in tags.items()]))")
  DATASTORE_ID=$(aws healthlake create-fhir-datastore \
    --datastore-name "$HEALTHLAKE_DATASTORE_NAME" \
    --datastore-type-version R4 \
    --preload-data-config PreloadDataType=SYNTHEA \
    --tags "$TAGS" \
    --query DatastoreId --output text)
else
  echo "data store exists: $DATASTORE_ID"
fi

echo "waiting for ACTIVE (~25 min on first creation)..."
while true; do
  STATUS=$(aws healthlake describe-fhir-datastore --datastore-id "$DATASTORE_ID" \
    --query DatastoreProperties.DatastoreStatus --output text)
  echo "$(date +%H:%M:%S) status=$STATUS"
  [[ "$STATUS" == "ACTIVE" ]] && break
  [[ "$STATUS" == "CREATE_FAILED" ]] && { echo "ERROR: creation failed" >&2; exit 1; }
  sleep 60
done

# HealthLake names its resource link <name>_<datastore id>_healthlake_view
LINK="$(echo "$HEALTHLAKE_DATASTORE_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_]/_/g')_${DATASTORE_ID}_healthlake_view"
echo "waiting for the Glue resource link $LINK ..."
for _ in $(seq 1 30); do
  aws glue get-database --name "$LINK" >/dev/null 2>&1 && { echo "resource link ready"; break; }
  sleep 30
done

echo "done: add '$HEALTHLAKE_DATASTORE_NAME' to HEALTHLAKE_DATASTORES (or leave it empty) and run bash scripts/deploy.sh"
echo "note: the principal creating the data store needs RAM share-acceptance permissions"
