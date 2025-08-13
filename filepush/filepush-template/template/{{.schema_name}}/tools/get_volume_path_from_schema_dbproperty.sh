#!/usr/bin/env bash
. $(dirname $0)/env.sh
databricks schemas get ${FILEPUSH_CATALOG_NAME}.${FILEPUSH_SCHEMA_NAME} --output json | jq '.properties["filepush.volume_path"]'
