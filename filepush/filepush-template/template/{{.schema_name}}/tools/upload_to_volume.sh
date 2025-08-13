#!/usr/bin/env bash
. $(dirname $0)/env.sh
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 <table_name> <local_file_path>"
  exit 1
fi
databricks fs mkdir dbfs:${FILEPUSH_VOLUME_PATH}$1/
databricks fs cp $2 dbfs:${FILEPUSH_VOLUME_PATH}$1/
