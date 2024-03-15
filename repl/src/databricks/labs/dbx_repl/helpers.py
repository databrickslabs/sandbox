from typing import Optional, List, Tuple
from databricks.sdk import WorkspaceClient
from enum import Enum
from databricks.sdk.service.compute import CommandStatusResponse
from cli_helpers.tabular_output import TabularOutputFormatter
import base64
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


def cluster_ready(client: WorkspaceClient, cluster_id: str) -> str:
    cluster_info = client.clusters.get(cluster_id)
    print(f"Connecting to '{cluster_id}'...")
    if cluster_id and cluster_info:
        client.clusters.ensure_cluster_is_running(cluster_id)
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


def display_image_from_base64_string(encoded_image: str) -> Image:
    # Assuming `encoded_image` is the Base64 string and has a prefix like 'data:image/png;base64,'
    # Remove the prefix and decode the Base64 string
    base64_str = encoded_image.split(",", 1)[1]
    image_data = base64.b64decode(base64_str)

    # Read the decoded data into an image
    img = Image.open(BytesIO(image_data))
    img.show()
    return img


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


def parse_cmd_image(command_result: CommandStatusResponse) -> Image:
    result_type = command_result.results.result_type.value
    if result_type == "images":
        base64_str = command_result.results.file_names[0]
    else:
        base64_str = command_result.results.file_name
    image = display_image_from_base64_string(base64_str)
    return image


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
        ("class:bracket", "]>"),
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
    return ">"