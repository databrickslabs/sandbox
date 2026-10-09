#!/usr/bin/env bash
# Removes everything deploy.sh and configure-consumer.sh created: the consumer
# catalogs and provider, the AWS role and Lake Formation grants, the app, and
# the recipient service principal. HealthLake data stores are not touched.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
source config.sh

for SHARE in $(cat .state/shares 2>/dev/null); do
  databricks api delete "/api/2.1/unity-catalog/catalogs/${CATALOG_PREFIX}${SHARE}" --profile "$CONSUMER_PROFILE" \
    && echo "deleted catalog ${CATALOG_PREFIX}${SHARE}" || true
done
databricks api delete "/api/2.1/unity-catalog/providers/$PROVIDER_NAME" --profile "$CONSUMER_PROFILE" \
  && echo "deleted provider $PROVIDER_NAME" || true

terraform -chdir=terraform destroy

export BUNDLE_VAR_app_name="$APP_NAME" BUNDLE_VAR_aws_region="$AWS_REGION" BUNDLE_VAR_aws_role_arns=unused \
  BUNDLE_VAR_recipient_sp_application_id="$(cat .state/recipient-client-id)"
databricks bundle destroy
databricks service-principals delete "$(cat .state/recipient-sp-id)" && echo "deleted $RECIPIENT_SP_NAME"
rm -rf .state
