from .repl import repl
from .helpers import cluster_setup, validate_language
from databricks.sdk import WorkspaceClient

def main(language, cluster_id, profile):

    client = WorkspaceClient(profile=profile)
    
    language = validate_language(language)
    cluster_id = cluster_setup(client, cluster_id, language)

    repl(client, language, cluster_id)
