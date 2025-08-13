#!/usr/bin/env bash
. $(dirname $0)/env.sh
databricks schemas update ${FILEPUSH_CATALOG_NAME}.${FILEPUSH_SCHEMA_NAME} --json '{ "properties": { "filepush.volume_path": "'${FILEPUSH_VOLUME_PATH}'" } }'
