#!/usr/bin/env bash
usage() {
    echo "Usage: $(basename $0) [--target=dev|prod]"
}
export -f usage
. $(dirname $0)/env.sh $@
databricks bundle run $FILEPUSH_JOB_NAME
