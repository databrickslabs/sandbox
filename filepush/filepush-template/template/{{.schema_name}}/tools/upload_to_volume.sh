#!/usr/bin/env bash
usage() {
    echo "Usage: $(basename $0) <table_name> <local_file_path> [--target=dev|prod]"
}
export -f usage
. $(dirname $0)/env.sh $@
if [ -z "$1" ] || [ -z "$2" ]; then
  usage
  exit 1
fi
databricks fs mkdir dbfs:${FILEPUSH_VOLUME_PATH}$1/
databricks fs cp $2 dbfs:${FILEPUSH_VOLUME_PATH}$1/
