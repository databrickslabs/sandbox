#!/usr/bin/env bash
. $(dirname $0)/env.sh
databricks pipelines get $FILEPUSH_PIPELINE_ID --output json | jq '.spec.configuration["filepush.volume_path"]'
