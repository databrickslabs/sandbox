from .repl import repl
from .helpers import cluster_setup, validate_language
from databricks.sdk import WorkspaceClient

def labs_main(language, cluster_id):

    client = WorkspaceClient()
    
    language = validate_language(language)
    cluster_id = cluster_setup(client, cluster_id, language)

    repl(client, language, cluster_id)
