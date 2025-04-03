from databricks.sdk import WorkspaceClient
from helpers.compute_analyzer import analyze_clusters, analyze_cluster_policies, analyze_jobs, analyze_dlt_pipelines

import pprint
import json


if __name__ == '__main__':
    wc = WorkspaceClient()
    full_results: dict = {}
    # clusters
    print("Starting scanning clusters")
    cluster_results = analyze_clusters(wc)
    if cluster_results:
        full_results["clusters"] = cluster_results
    # cluster policies
    print("Starting scanning cluster policies")
    cluster_policy_results = analyze_cluster_policies(wc)
    if cluster_policy_results:
        full_results["cluster_policies"] = cluster_policy_results
    # jobs
    print("Starting scanning jobs")
    jobs_results = analyze_jobs(wc)
    if jobs_results:
        full_results["jobs"] = jobs_results
    # DLT pipelines
    print("Starting scanning DLT pipelines")
    dlt_results = analyze_dlt_pipelines(wc)
    if dlt_results:
        full_results["dlt"] = dlt_results
    print("Scan results: ")
    if full_results:
        pprint.pprint(full_results)
        with open("compute_scan_results.json", "w") as f:
            json.dump(full_results, f, indent=4)
    else:
        print("Nothing is found")
