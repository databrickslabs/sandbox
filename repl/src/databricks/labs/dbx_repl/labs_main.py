from .repl import repl
from .helpers import cluster_setup, validate_language
from databricks.sdk import WorkspaceClient
from .__version__ import __version__ as product_version
from .__version__ import __name__ as product_name
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.styles import Style


def welcome():

    style = Style.from_dict({"welcome": "ansiyellow", "code": "#ff0000"})

    print_formatted_text(
        HTML(
            """<welcome>Welcome to the Databricks REPL!
 * Press Ctrl-D to exit
 * Type <code>:python</code>, <code>:r</code>, <code>:sql</code>, or <code>:scala</code> to switch languages
</welcome>"""
        ),
        style=style,
    )


def labs_main(language, cluster_id):
    client = WorkspaceClient(
        product=product_name, product_version=product_version
    )
    language = validate_language(language)
    welcome()
    cluster_id = cluster_setup(client, cluster_id, language)

    repl(client, language, cluster_id)
