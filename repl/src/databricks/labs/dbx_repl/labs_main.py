from .repl import repl
from .helpers import cluster_setup, validate_language
from databricks.sdk import WorkspaceClient
from .__version__ import __version__ as product_version
from .__version__ import __name__ as product_name


def labs_main(language, cluster_id):
    client = WorkspaceClient(product=product_name, product_version=product_version)
    
    language = validate_language(language)
    cluster_id = cluster_setup(client, cluster_id, language)

    repl(client, language, cluster_id)
