#!/usr/bin/env bash
usage() {
    echo "Usage: $(basename $0) [--target=dev|prod]"
}
export -f usage
. $(dirname $0)/env.sh $@
databricks schemas get ${FILEPUSH_CATALOG_NAME}.${FILEPUSH_SCHEMA_NAME} -t $BUNDLE_TARGET --output json | jq '.properties["filepush.volume_path"]'
