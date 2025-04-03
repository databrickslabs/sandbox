import pathlib
import re
from dataclasses import dataclass
import os
from typing import Tuple
from datetime import datetime, timezone

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.files import FileInfo


@dataclass
class DbfsDirectoryInfo:
    full_path: str
    name: str
    entries: list[FileInfo]


__dirs_to_skip__ = {
    "/Volumes", "/mnt", "/databricks-datasets", "/Volume", "/databricks/mlflow-registry",
    "/databricks/mlflow-tracking", "/databricks-results", "/volume", "/volumes"
}


def list_dbfs_ignore_error(wc: WorkspaceClient, path: str, recursive: bool = False) -> list[FileInfo]:
    try:
        return list(wc.dbfs.list(path, recursive=recursive))
    except Exception as e:
        print(f"Error occurred while listing {path}: {e}")
        return []


# TODO: reimplement it as iterator so we can use a thread pool to scan multiple directories
#  in parallel.  Look how Python handles writing to a map from multiple threads.
def scan_dbfs(wc: WorkspaceClient, results: dict, path: str = "/"):
    """
    Scans the given path in DBFS and returns list of analyzed entries.

    :param wc: workspace client
    :param results:
    :param path: The start path to scan.
    :return: A DbfsDirectoryInfo object representing the directory.
    """
    print("Scanning directory at path:", path)
    dir_info = DbfsDirectoryInfo(full_path=path, name=os.path.basename(path),
                                 entries=list_dbfs_ignore_error(wc, path))
    should_process_nested, r = analyze_dbfs_directory(wc, dir_info)
    if r:
        print(path, r)
        results[path] = r
        size = r.get("size", 0)
        if size > 0:  # Update the parent directory size
            parent_dir = os.path.dirname(path)
            while parent_dir in results and parent_dir != "/":
                # print("Updating size for", parent_dir)
                results[parent_dir]["size"] = results[parent_dir].get("size", 0) + size
                parent_dir = os.path.dirname(parent_dir)

    if should_process_nested:
        for file_info in dir_info.entries:
            if file_info.is_dir and file_info.path not in __dirs_to_skip__:
                scan_dbfs(wc, results, file_info.path)

    return results


def _is_present_and_is_dir(local_names: dict, name: str) -> bool:
    return name in local_names and local_names[name]


def _is_in_local_names(local_names: dict, check_fn) -> bool:
    for k, v in local_names.items():
        if check_fn(k, v):
            return True
    return False


__cluster_directory_regex__ = re.compile(r'^\d{4}-\d{6}-\w{8}_\d+_\d+_\d+_\d+$')
__autoloader_schema_file_regex__ = re.compile(r'^\d+$')


# TODO: refactor all this logic into separate functions so we can compose them easier
# TODO: can we detect update time for tables, and similar things? Maybe when we scan things at the end?
def analyze_dbfs_directory(wc: WorkspaceClient, dir_info: DbfsDirectoryInfo) -> Tuple[bool, dict]:
    """
    Scans the given path in DBFS and returns list of analyzed entries.

    :param wc: workspace client
    :param dir_info:
    :return: A DbfsDirectoryInfo object representing the directory.
    """
    results = {}
    should_process_nested = True
    local_names = dict([(os.path.basename(e.path), e.is_dir) for e in dir_info.entries])
    # print("analyzing", dir_info.full_path, local_names)
    if dir_info.full_path == "/user/hive/warehouse" and len(dir_info.entries) > 0:
        results["type"] = "hive_database"
        should_process_nested = False
    if should_process_nested and _is_present_and_is_dir(local_names, "_delta_log"):
        results["type"] = "delta_table"
        # We're expecting that Delta tables don't have any additional data
        should_process_nested = False
    if (should_process_nested and _is_present_and_is_dir(local_names, "system") and
        (_is_present_and_is_dir(local_names, "tables") or
         _is_present_and_is_dir(local_names, "checkpoints") or
         _is_present_and_is_dir(local_names, "autoloader"))):
        results["type"] = "dlt_storage"
        should_process_nested = False
    if should_process_nested and _is_present_and_is_dir(local_names, "system"):
        # It could be a DLT storage, but we're not sure - need to check for additional directories
        matched_dirs = False
        for f in wc.dbfs.list(os.path.join(dir_info.full_path, "system")):
            if f.is_dir and f.path.endswith("/events"):
                matched_dirs = True
                break
        if matched_dirs:
            results["type"] = "dlt_storage"
            should_process_nested = False
    if (should_process_nested and _is_present_and_is_dir(local_names, "commits")
            and _is_present_and_is_dir(local_names, "offsets")):
        # also _is_present_and_is_dir(local_names, "sources")
        # also could be _is_present_and_is_dir(local_names, "state"), but alone
        results["type"] = "ss_checkpoint"
        should_process_nested = False
    if (should_process_nested and _is_present_and_is_dir(local_names, "driver")
            and _is_present_and_is_dir(local_names, "eventlog")):
        # also _is_present_and_is_dir(local_names, "executor")
        results["type"] = "cluster_logs"
        should_process_nested = False
    # This "could be" cluster logs, but with errors when `driver` didn't start at all
    if should_process_nested and _is_present_and_is_dir(local_names, "init_scripts"):
        matched_dirs = False
        for f in wc.dbfs.list(os.path.join(dir_info.full_path, "init_scripts")):
            if f.is_dir and __cluster_directory_regex__.match(os.path.basename(f.path)):
                matched_dirs = True
                break
        if matched_dirs:
            results["type"] = "cluster_logs"
            should_process_nested = False
    # This could autoloader schema inference directory
    if should_process_nested and _is_present_and_is_dir(local_names, "_schemas"):
        schema_file_found = False
        for f in wc.dbfs.list(os.path.join(dir_info.full_path, "_schemas")):
            if (__autoloader_schema_file_regex__.match(os.path.basename(f.path)) or
                    os.path.basename(f.path) =="/__tmp_path_dir"):
                schema_file_found = True
                break
        if schema_file_found:
            results["type"] = "autoloader_schema"
            should_process_nested = False
    # This could be a MLflow model directory
    if (should_process_nested and _is_in_local_names(local_names, lambda k, v: not v and k == "MLmodel") and
            (_is_in_local_names(local_names, lambda k, v: not v and k == "conda.yaml") or
             _is_in_local_names(local_names, lambda k, v: not v and k == "requirements.txt") or
             _is_in_local_names(local_names, lambda k, v: not v and k == "python_env.yaml"))):
        results["type"] = "mlflow_model"
        should_process_nested = False
    # This could be a saved data directory. We're looking for _SUCCESS file and part- files
    # But it may have part- files and no _SUCCESS file (but it will have _started and/or _committed)
    if (should_process_nested and
            _is_in_local_names(local_names, lambda k, v: not v and k.startswith("part-"))
            and ("_SUCCESS" in local_names) or
            _is_in_local_names(local_names, lambda k, v: not v and k.startswith("_started_")) or
            _is_in_local_names(local_names, lambda k, v: not v and k.startswith("_committed_"))
        ):
        parts_file_found = False
        file_extension = ""
        for k, v in local_names.items():
            if k.startswith("part-") and not v:
                file_extension = ''.join(pathlib.Path(k).suffixes).lstrip('.')
                parts_file_found = True
                break
        if parts_file_found:
            results["type"] = f"saved data ({file_extension})"
            should_process_nested = False

    size = 0
    last_update_time = 0
    if should_process_nested:
        whl_files = []
        jar_files = []
        for file_info in dir_info.entries:
            if file_info.is_dir:
                continue
            size += file_info.file_size
            last_update_time = max(last_update_time, file_info.modification_time)
            if file_info.path.endswith(".jar"):
                jar_files.append(os.path.basename(file_info.path))
            if file_info.path.endswith(".whl"):
                whl_files.append(os.path.basename(file_info.path))

        if whl_files:
            results["whl_files"] = whl_files
        if jar_files:
            results["jar_files"] = jar_files
    else:  # collect size and update timestamp of the directory if it's not going to be processed
        # TODO: maybe not calculate this here, but instead return,
        #  and have a separate multithreaded implementation?
        for f in list_dbfs_ignore_error(wc, dir_info.full_path, recursive=True):
            size += f.file_size
            last_update_time = max(last_update_time, f.modification_time)

    results["size"] = size
    if last_update_time > 0:
        results["last_update_time"] = datetime.fromtimestamp(last_update_time/1000,
                                                             tz=timezone.utc).isoformat()

    return should_process_nested, results


