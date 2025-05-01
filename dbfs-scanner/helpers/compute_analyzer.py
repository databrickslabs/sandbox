import base64
import json
import re
from typing import Optional, Tuple

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.compute import ClusterSource, ClusterDetails, ClusterSpec
from databricks.sdk.service.jobs import Task
from databricks.sdk.service.pipelines import PipelineCluster
from databricks.sdk.service.workspace import ExportFormat


__notebook_pip_install_from_dbfs__ = re.compile(r"^#\s+MAGIC\s+%pip\s+install.*(/dbfs/.*)$")
__notebook_dbfs_fuse_use__ = re.compile(r"^.*[\"'](/dbfs/[^\"']*)[\"'].*$")
__notebook_dbfs_hdfs_use__ = re.compile(r"^.*[\"'](dbfs:/[^\"']*)[\"'].*$")
__supported_dbfs_paths__ = re.compile(r"^(/dbfs|dbfs:)(/Volumes|/databricks-datasets|/databricks-results|/databricks/mlflow-registry|/databricks/mlflow-tracking)(/.*)?$")


def _is_supported_dbfs_path(path: str) -> bool:
    return __supported_dbfs_paths__.match(path) is not None


def _analyze_notebook_or_wsfile(wc: WorkspaceClient, notebook_path: str) -> Tuple[list, list]:
    """Analyzes a notebook or workspace file for DBFS libraries and file references.

    Args:
        wc: The Databricks workspace client
        notebook_path: The path to the notebook or workspace file

    Returns:
        Tuple containing:
        - List of library paths found in pip install commands
        - List of DBFS file references found in the code
    """
    libs = []
    dbfs_file_refs = []
    try:
        b64 = wc.workspace.export(notebook_path, format=ExportFormat.SOURCE).content
        content = base64.b64decode(b64).decode("utf-8")
        libs, dbfs_file_refs = _analyze_notebook_content(content)

    except Exception:
        # print(f"Error occurred while analyzing notebook {notebook_path}: {e}")
        pass

    return libs, dbfs_file_refs


def _analyze_notebook_content(content: str) -> Tuple[list, list]:
    """Analyzes notebook content for DBFS libraries and file references.

    Args:
        content: The notebook content as a string

    Returns:
        Tuple containing:
        - List of library paths found in pip install commands
        - List of DBFS file references found in the code
    """
    libs = []
    dbfs_file_refs = []

    for l in content.split("\n"):
        m = __notebook_pip_install_from_dbfs__.match(l)
        if m and _is_supported_dbfs_path(m.group(1)):
            libs.append(m.group(1))
        elif not l.lstrip().startswith("#"):
            m = __notebook_dbfs_fuse_use__.match(l)
            if m and _is_supported_dbfs_path(m.group(1)):
                dbfs_file_refs.append(m.group(1))
            m = __notebook_dbfs_hdfs_use__.match(l)
            if m and _is_supported_dbfs_path(m.group(1)):
                dbfs_file_refs.append(m.group(1))

    return libs, dbfs_file_refs


def analyze_dlt_pipelines(wc: WorkspaceClient) -> dict:
    """Analyzes Databricks Delta Live Tables (DLTs) for DBFS libraries and file references.

    Args:
        wc: The Databricks workspace client

    Returns:
        A dictionary containing the results of the analysis.
    """
    finds = {}
    i = 0
    for l in wc.pipelines.list_pipelines(max_results=100):
        i += 1
        if i % 100 == 0:
            print(f"Scanned {i} DLT pipelines")
        # print("Analyzing pipeline:", l.pipeline_id, l.name)
        p = wc.pipelines.get(l.pipeline_id)
        if not p:
            continue
        p_finds = {}
        # analyze clusters
        clusters = {}
        for cl in p.spec.clusters:
            cl_finds = _analyze_cluster_spec(cl, {})
            if cl_finds:
                clusters[cl.label] = cl_finds
        if clusters:
            p_finds["clusters"] = clusters
        # analyze storage
        if p.spec.storage:
            p_finds["storage"] = p.spec.storage
        # analyze libraries
        lib_finds = {}
        for lib in p.spec.libraries:
            lib_path = ""
            if lib.notebook:
                lib_path = lib.notebook.path
            elif lib.file:
                lib_path = lib.file.path
            if lib_path:
                libs, dbfs_file_refs = _analyze_notebook_or_wsfile(wc, lib_path)
                if libs or dbfs_file_refs:
                    d = {}
                    if libs:
                        d["libraries"] = libs
                    if dbfs_file_refs:
                        d["dbfs_file_refs"] = dbfs_file_refs
                    lib_finds[lib_path] = d
        if lib_finds:
            p_finds["libraries"] = lib_finds
        if p_finds:
            p_finds["name"] = l.name
            finds[l.pipeline_id] = p_finds

    print(f"Total {i} DLT pipelines")

    return finds


def _analyze_task(wc: WorkspaceClient, task: Task ) -> dict:
    """Analyzes a task for DBFS libraries and file references.

    Args:
        wc: The Databricks workspace client
        task: The task to analyze

    Returns:
        A dictionary containing the results of the analysis.
    """
    finds = {}
    if task.spark_python_task:
        if task.spark_python_task.python_file.startswith("dbfs:/"):
            finds["python_file_on_dbfs"] = task.spark_python_task.python_file
        elif task.spark_python_task.python_file.startswith("/"):
            libs, dbfs_file_refs = _analyze_notebook_or_wsfile(wc, task.spark_python_task.python_file)
            if libs or dbfs_file_refs:
                finds["python_file_in_ws"] = {
                    "path": task.spark_python_task.python_file
                }
                if libs:
                    finds["python_file_in_ws"]["libraries"] = libs
                if dbfs_file_refs:
                    finds["python_file_in_ws"]["dbfs_file_refs"] = dbfs_file_refs

    if task.notebook_task:
        libs, dbfs_file_refs = _analyze_notebook_or_wsfile(wc, task.notebook_task.notebook_path)
        if libs or dbfs_file_refs:
            finds["notebook"] = {
                "path": task.notebook_task.notebook_path,
            }
            if libs:
                finds["notebook"]["libraries"] = libs
            if dbfs_file_refs:
                finds["notebook"]["dbfs_file_refs"] = dbfs_file_refs

    if task.for_each_task:
        fe_finds = _analyze_task(wc, task.for_each_task.task)
        if fe_finds:
            finds["for_each_task"] = fe_finds

    for lib in (task.libraries or []):
        dbfs_lib = ""
        if lib.jar and lib.jar.startswith("dbfs:/"):
            dbfs_lib = lib.jar
        if lib.whl and lib.whl.startswith("dbfs:/"):
            dbfs_lib = lib.whl
        if lib.egg and lib.egg.startswith("dbfs:/"):
            dbfs_lib = lib.egg
        if dbfs_lib:
            r = finds.get("libraries", [])
            r.append(dbfs_lib)
            finds["libraries"] = r

    if task.new_cluster:
        finds = _analyze_cluster_spec(task.new_cluster, finds)

    return finds


def analyze_jobs(wc: WorkspaceClient) -> dict:
    """Analyzes Databricks jobs for DBFS libraries and file references.

    Args:
        wc: The Databricks workspace client

    Returns:
        A dictionary containing the results of the analysis.
    """
    res = {}
    i = 0
    for job in wc.jobs.list(expand_tasks=True, limit=100):
        i += 1
        if i % 100 == 0:
            print(f"Scanned {i} jobs")
        finds = {}
        js = job.settings
        # print("Analyzing job:", js.name)
        for task in (js.tasks or []):
            task_res = _analyze_task(wc, task)

            if task_res:
                t = finds.get("tasks", {})
                t[task.task_key] = task_res
                finds["tasks"] = t

        jcs_finds = {}
        for jc in (js.job_clusters or []):
            jc_finds = {}
            if jc.new_cluster:
                jc_finds = _analyze_cluster_spec(jc.new_cluster, jc_finds)
            if jc_finds:
                jcs_finds[jc.job_cluster_key] = jc_finds

        if jcs_finds:
            finds["job_clusters"] = jcs_finds

        if finds:
            finds["job_name"] = js.name
            res[job.job_id] = finds

    print(f"Total {i} jobs")
    return res


def _analyze_cluster_spec(cl: ClusterDetails | ClusterSpec | PipelineCluster, finds: dict):
    """Analyzes a cluster specification for DBFS libraries and file references.

    Args:
        cl: The cluster specification to analyze
        finds: A dictionary containing the results of the analysis

    Returns:
        A dictionary containing the results of the analysis.
    """
    for init_script in (cl.init_scripts or []):
        if init_script.dbfs:
            r = finds.get("init_scripts", [])
            r.append(init_script.dbfs.destination)
            finds["init_scripts"] = r
    # check if we have cluster conf pointing to DBFS
    if cl.cluster_log_conf and cl.cluster_log_conf.dbfs and cl.cluster_log_conf.dbfs.destination:
        finds["cluster_log_conf"] = cl.cluster_log_conf.dbfs.destination

    return finds


def analyze_clusters(wc: WorkspaceClient) -> dict:
    """Analyzes Databricks clusters for DBFS libraries and file references.

    Args:
        wc: The Databricks workspace client

    Returns:
        A dictionary containing the results of the analysis.
    """
    res = {}
    i = 0
    for cl in wc.clusters.list(page_size=100):
        if cl.cluster_source not in [ClusterSource.UI, ClusterSource.API]:
            continue
        i += 1
        if i % 100 == 0:
            print(f"Scanned {i} clusters")
        # print("Analyzing cluster:", cl.cluster_name)
        finds = {}

        # check if we have any libraries pointing to DBFS
        for lib in wc.libraries.cluster_status(cl.cluster_id):
            dbfs_lib = ""
            if lib.library.jar and lib.library.jar.startswith("dbfs:/"):
                dbfs_lib = lib.library.jar
            if lib.library.whl and lib.library.whl.startswith("dbfs:/"):
                dbfs_lib = lib.library.whl
            if dbfs_lib:
                r = finds.get("libraries", [])
                r.append(dbfs_lib)
                finds["libraries"] = r

        finds = _analyze_cluster_spec(cl, finds)

        # if we found anything, add it to the results
        if finds:
            finds["cluster_name"] = cl.cluster_name
            res[cl.cluster_id] = finds

    print(f"Total {i} clusters")
    return res


def _check_policy_definition(sdef: Optional[str], finds: dict):
    """Analyzes a policy definition for DBFS libraries and file references.

    Args:
        sdef: The policy definition to analyze
        finds: A dictionary containing the results of the analysis

    """
    policy_def = json.loads(sdef or "{}")
    for k, v in policy_def.items():
        if not isinstance(v, dict):
            continue
        typ = v.get("type")
        if not typ:
            continue
        val = v.get("value") or v.get("defaultValue")
        if typ == "fixed" and k == "cluster_log_conf.path" and val and val.startswith("dbfs:/"):
            finds["cluster_log_conf"] = val
        if typ == "fixed" and k.startswith("init_scripts.") and k.endswith(".dbfs.destination"):
            r = finds.get("init_scripts", [])
            r.append(val)
            finds["init_scripts"] = r

    return finds


def analyze_cluster_policies(wc: WorkspaceClient) -> dict:
    """Analyzes Databricks cluster policies for DBFS libraries and file references.

    Args:
        wc: The Databricks workspace client

    Returns:
        A dictionary containing the results of the analysis.
    """
    res = {}
    i = 0
    for pf in wc.policy_families.list():
        i += 1
        if i % 100 == 0:
            print(f"Scanned {i} policies")
        finds = {}
        # print("Analyzing cluster policy family:", pf.name)
        finds = _check_policy_definition(pf.definition, finds)

        if finds:
            finds["policy_name"] = pf.name
            res[pf.policy_id] = finds

    for pl in wc.cluster_policies.list():
        i += 1
        if i % 100 == 0:
            print(f"Scanned {i} policies")
        # print("Analyzing cluster policy:", pl.name)
        finds = {}
        for lib in (pl.libraries or []):
            dbfs_lib = ""
            if lib.jar and lib.jar.startswith("dbfs:/"):
                dbfs_lib = lib.jar
            if lib.whl and lib.whl.startswith("dbfs:/"):
                dbfs_lib = lib.whl
            if dbfs_lib:
                r = finds.get("libraries", [])
                r.append(dbfs_lib)
                finds["libraries"] = r

        finds = _check_policy_definition(pl.definition, finds)

        if finds:
            finds["policy_name"] = pl.name
            res[pl.policy_id] = finds

    print(f"Total {i} cluster policies and families")
    return res
