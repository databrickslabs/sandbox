#!/usr/bin/env bash
usage() {
    echo "Usage: $(basename $0) [--target=dev|prod]"
}
export -f usage
. $(dirname $0)/env.sh $@
databricks bundle open ${FILEPUSH_BUNDLE_NAME} -t $BUNDLE_TARGET
databricks bundle open ${FILEPUSH_BUNDLE_NAME}_job -t $BUNDLE_TARGET
databricks bundle open ${FILEPUSH_BUNDLE_NAME}_pipeline -t $BUNDLE_TARGET
databricks bundle open ${FILEPUSH_BUNDLE_NAME}_volume -t $BUNDLE_TARGET