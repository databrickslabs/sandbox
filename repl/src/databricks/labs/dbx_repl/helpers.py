import os
import subprocess
import tempfile
from typing import Optional, List, Tuple
from databricks.sdk import WorkspaceClient
from enum import Enum
from databricks.sdk.service.compute import CommandStatusResponse, State
from databricks.sdk.mixins.compute import ClustersExt
from databricks.sdk.errors.base import DatabricksError
from cli_helpers.tabular_output import TabularOutputFormatter
import base64
import datetime
import time
from PIL import Image
from io import BytesIO
import re
from IPython.display import display, HTML
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.sql import SqlLexer
from pygments.lexers.r import SLexer
from pygments.lexers.python import Python3Lexer
from pygments.lexers.jvm import ScalaLexer
from pygments.lexer import Lexer
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.styles import Style


formatter = TabularOutputFormatter()


# Databricks SDK is missing values needed
class Language(Enum):
    PYTHON = "python"
    SCALA = "scala"
    SQL = "sql"
    R = "r"


def serverless_available(client: WorkspaceClient) -> Optional[str]:
    client = WorkspaceClient()
    current_user = client.current_user.me().emails[0].value

    # TODO: its possible for there to be multiple for a given user (if they exist)
    # returning first serverless cluster for the current user
    for cluster in client.clusters.list():
        if cluster.cluster_name == "" and cluster.creator_user_name == current_user:
            return cluster.cluster_id

    return None

def print_cluster_state(c):
    # clear current line and overwrite it with the state message
    message = f"Starting cluster '{c.cluster_id}' [{c.state}]: {c.state_message}"
    print(f"\033[2K\r{message}", end="")

def ensure_cluster_is_running(clusterClient: ClustersExt, cluster_id: str) -> None:
    """Ensures that given cluster is running, regardless of the current state"""
    timeout = datetime.timedelta(minutes=20)
    deadline = time.time() + timeout.total_seconds()
    while time.time() < deadline:
        try:
            state = State
            info = clusterClient.get(cluster_id)
            if info.state == state.RUNNING:
                return
            elif info.state == state.TERMINATED:
                print(f"Starting cluster '{cluster_id}'...")
                clusterClient.start(cluster_id).result(print_cluster_state)
                return
            elif info.state == state.TERMINATING:
                print(f"Waiting for cluster '{cluster_id}' to terminate...")
                clusterClient.wait_get_cluster_terminated(cluster_id)
                clusterClient.start(cluster_id).result(print_cluster_state)
                return
            elif info.state in (state.PENDING, state.RESIZING, state.RESTARTING):
                print(f"Waiting for cluster '{cluster_id}' to start...")
                clusterClient.wait_get_cluster_running(cluster_id, datetime.timedelta(minutes=20), print_cluster_state)
                return
            elif info.state in (state.ERROR, state.UNKNOWN):
                raise RuntimeError(f'Cluster {cluster_id} is {info.state}: {info.state_message}')
        except DatabricksError as e:
            if e.error_code == 'INVALID_STATE':
                print(f'Cluster was started by other process: {e} Retrying.')
                continue
            raise e
        except ValueError as e:
            continue
        except e:
            print('Operation failed, retrying', e)
        
    raise TimeoutError(f'timed out after {timeout}')


def cluster_ready(client: WorkspaceClient, cluster_id: str) -> str:
    cluster_info = client.clusters.get(cluster_id)
    print(f"Connecting to '{cluster_id}'...")
    if cluster_id and cluster_info:
        ensure_cluster_is_running(client.clusters, cluster_id)
        print()
        return cluster_id
    else:
        raise Exception(f"couldn't connect to {cluster_id}")


# TODO: probably can be reworked
def cluster_setup(
    client: WorkspaceClient, cluster_id: Optional[str], language: Language
) -> str:

    if cluster_id:
        try:
            return cluster_ready(client, cluster_id)
        except Exception:
            pass

    try:
        # Check for a default cluster ID in config
        return cluster_ready(client, client.config.cluster_id)
    except Exception:
        pass

    # Check if serverless is available for SQL/Python
    if language.value in ["sql", "python"]:
        serverless_cluster_id = serverless_available(client)
        if serverless_cluster_id:
            return serverless_cluster_id

    # TODO: ask user to pick a cluster from a list that is compatible

    raise ValueError("No suitable cluster found. Please specify a cluster ID.")


def validate_language(language: str) -> Language:
    language = language.lower()
    for lang in Language:
        if language == lang.value:
            return lang
    raise ValueError(
        f"Invalid language '{language}'. Must be one of {[lang.value for lang in Language]}."
    )


def display_image_from_base64_string(encoded_image: str):
    # Assuming `encoded_image` is the Base64 string and has a prefix like 'data:image/png;base64,'
    # Remove the prefix and decode the Base64 string
    mime, base64_str = encoded_image.split(",", 1)
    image_data = base64.b64decode(base64_str)

    try:
        display_image_vscode(mime, image_data)
    except:
        # Read the decoded data into an image
        img = Image.open(BytesIO(image_data))
        img.show()

def display_image_vscode(mime: str, image_data: BytesIO):
    if os.environ.get("VSCODE_INJECTION") is None:
        raise RuntimeError("This function is only available in VSCode")

    mime = mime.split(":")[1].split(";")[0]
    if mime == "image/png":
        file_extension = ".png"
    elif mime == "image/jpeg":
        file_extension = ".jpeg"
    else:
        raise ValueError(f"Unsupported image type: {mime}")
        
    # write image_data to a temporary file
    tmp = tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix=file_extension)
    tmp.write(image_data)

    is_insiders = os.environ.get("VSCODE_GIT_ASKPASS_MAIN").index("Insiders") != -1
    
    if is_insiders:
        cmd = "code-insiders"
    else:
        cmd = "code"

    command = [cmd, "-r", tmp.name]
    process = subprocess.Popen(command)
    process.wait()


def parse_cmd_error(command_result: CommandStatusResponse, language: Language) -> str:
    summary = command_result.results.summary.strip()
    cause = command_result.results.cause.strip()
    lang = language.value

    # Inconsistencies between languages, handle accordingly
    if lang == "python":
        return cause

    if lang in ["scala", "sql"]:
        return summary

    if lang == "r":
        # R errors can sometimes have a prefix that is unhelpful
        if "DATABRICKS_CURRENT_TEMP_CMD__" in cause:
            return cause[62:]
        else:
            return cause


def parse_cmd_table(command_result: CommandStatusResponse) -> str:
    data = command_result.results.data
    headers = [
        "{}\n{}".format(col["name"], col["type"].replace('"', ""))
        for col in command_result.results.schema
    ]

    table = "\n".join(
        formatter.format_output(iter(data), headers, format_name="fancy_grid")
    )
    return table


def parse_cmd_image(command_result: CommandStatusResponse):
    result_type = command_result.results.result_type.value
    if result_type == "images":
        base64_str = command_result.results.file_names[0]
    else:
        base64_str = command_result.results.file_name
    display_image_from_base64_string(base64_str)


def parse_cmd_result(
    command_result: CommandStatusResponse, language: Language
) -> Optional[str]:
    out = command_result.results.data

    if language.value == "python":
        # Check if the output contains HTML
        is_html = bool(re.search("<html|<div", out, re.IGNORECASE))
        if is_html:
            display(HTML(out))
            out = None

    # For other languages 'out' is simply taken from the command result
    if out == "":
        return None

    return out


def parse_command_output(
    command_result: CommandStatusResponse, language: Language
) -> str:
    result_type = command_result.results.result_type.value

    if result_type == "error":
        return parse_cmd_error(command_result, language)
    if result_type == "table":
        return parse_cmd_table(command_result)
    if result_type in ["image", "images"]:
        parse_cmd_image(command_result)
        return None

    return parse_cmd_result(command_result, language)


def get_lexer(language: Language) -> Optional[Lexer]:
    lexer_map = {
        "python": Python3Lexer,
        "sql": SqlLexer,
        "r": SLexer,
        "scala": ScalaLexer,
    }
    lexer_class = lexer_map.get(language.value)
    return lexer_class if lexer_class else None


def repl_styled_prompt(cluster_id, language: Language) -> Tuple[List[Tuple], Style]:

    message = [
        ("class:bracket", "["),
        ("class:cluster", cluster_id),
        ("class:bracket", "]"),
        ("class:bracket", "["),
        ("class:language", language.value),
        ("class:bracket", "]> "),
    ]

    style = Style.from_dict(
        {
            # User input (default text).
            "": "#fafafa",
            # Prompt.
            "bracket": "#bdbdbd",
            "cluster": "#559c51",
            "language": "#cf215e",
        }
    )

    return (message, style)


def prompt_continuation(width, line_number, is_soft_wrap):
    return "> "
