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
databricks bundle init filepush-template --config-file <(echo "{\"catalog_name\": \"$1\", \"schema_name\": \"$2\"}")
working_dir=$(pwd)
schema_name=$2
cd $schema_name
databricks bundle deploy --force-lock --auto-approve -t prod
cd $working_dir