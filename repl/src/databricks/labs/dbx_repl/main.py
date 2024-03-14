import click
from .repl import repl
from .helpers import cluster_setup, validate_language
from databricks.sdk import WorkspaceClient


@click.group()
def databricks():
    """Databricks CLI group."""
    pass

@databricks.command(name='repl')
@click.argument("language")
@click.option("--cluster-id", default=None, help="Cluster ID to use")
@click.option("--profile", default="DEFAULT", help="Profile to use from .databrickscfg")
def main(language, cluster_id, profile):

    client = WorkspaceClient(profile=profile)
    
    language = validate_language(language)
    cluster_id = cluster_setup(client, cluster_id, language)

    repl(client, language, cluster_id)


if __name__ == "__main__":
    main()
