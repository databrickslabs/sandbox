#!/usr/bin/env bash
usage() {
    echo "Usage: $(basename $0) [--target=dev|prod]"
}
export -f usage
. $(dirname $0)/env.sh $@
databricks schemas update ${FILEPUSH_CATALOG_NAME}.${FILEPUSH_SCHEMA_NAME} --json '{ "properties": { "filepush.volume_path": "'${FILEPUSH_VOLUME_PATH}'" } }'
