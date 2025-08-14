#!/usr/bin/env bash
usage() {
    echo "Usage: $(basename $0) [--target=dev|prod]"
}
export -f usage
. $(dirname $0)/env.sh $@
databricks pipelines get $FILEPUSH_PIPELINE_ID -t $BUNDLE_TARGET --output json | jq '.spec.configuration["filepush.volume_path"]'
