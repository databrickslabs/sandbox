#!/usr/bin/env bash
usage() {
    echo "Usage: $(basename $0) <catalog_name> <schema_name>"
}
if [ -z "$1" ] || [ -z "$2" ]; then
  usage
  exit 1
fi
if ! databricks catalogs get "$1" >/dev/null 2>&1; then
  echo "Catalog \`$1\` not found (or no permission)"
  exit 1
fi
volume_path=$(databricks schemas get $1.$2 --output json | jq -r '.properties["filepush.volume_path"]')
if [ -z "$volume_path" ] || [ "$volume_path" == "null" ]; then
  echo "Schema \`$1.$2\` is not a filepush schema. Did you run create_filepush_schema.sh to create it?"
  exit 1
fi
working_dir=$(pwd)
schema_name=$2
cd $schema_name
databricks bundle destroy --force-lock -t prod
cd $working_dir