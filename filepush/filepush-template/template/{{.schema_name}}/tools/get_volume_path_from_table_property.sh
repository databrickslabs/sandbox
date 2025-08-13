#!/usr/bin/env bash
. $(dirname $0)/env.sh
databricks tables get ${FILEPUSH_CATALOG_NAME}.${FILEPUSH_SCHEMA_NAME}.$1 --output json | jq '.properties["filepush.volume_path"]'
