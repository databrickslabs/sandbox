#!/usr/bin/env bash
usage() {
    echo "Usage: $(basename $0) <table_name> [--target=dev|prod]"
}
export -f usage
. $(dirname $0)/env.sh $@
databricks tables get ${FILEPUSH_CATALOG_NAME}.${FILEPUSH_SCHEMA_NAME}.$1 --output json | jq '.properties["filepush.volume_path"]'
