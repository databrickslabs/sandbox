#!/usr/bin/env bash
. $(dirname $0)/env.sh
databricks bundle run $FILEPUSH_JOB_NAME
