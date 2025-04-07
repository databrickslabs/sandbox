from databricks.sdk import WorkspaceClient
from helpers.dbfs_analyzer import scan_dbfs

import sys
import pprint
import json


if __name__ == '__main__':
    wc = WorkspaceClient()
    results = {}
    path = "/"
    if len(sys.argv) > 1:
        path = sys.argv[1]
    print("Starting scanning DBFS at path:", path)
    scan_dbfs(wc, results, path)
    print("Scan results: ")
    pprint.pprint(results)
    with open("dbfs_scan_results.json", "w") as f:
        json.dump(results, f, indent=4)
