#!/usr/bin/env bash
usage() {
    echo "Usage: $(basename $0) <catalog_name> <schema_name> <table_name> <file_path>"
}
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ] || [ -z "$4" ]; then
  usage
  exit 1
fi
volume_path=$(databricks schemas get $1.$2 --output json | jq -r '.properties["filepush.volume_path"]')
if [ -z "$volume_path" ] || [ "$volume_path" == "null" ]; then
  echo "Schema \`$1.$2\` is not a filepush schema. Did you run create_filepush_schema.sh to create it?"
  exit 1
fi
databricks fs mkdir dbfs:${volume_path}$3/
databricks fs cp $4 dbfs:${volume_path}$3/