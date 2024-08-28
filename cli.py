import json
import logging
import sys
import webbrowser

logger = logging.getLogger("databricks.labs.sandbox")


def ip_access_list_analyzer(**args):
    import ip_access_list_analyzer.ip_acl_analyzer as analyzer
    analyzer.main(args)

def sql_migration_assistant(**args):
    from sql_migration_assistant import hello
    hello()

MAPPING = {
    "ip-access-list-analyzer": ip_access_list_analyzer,
    "sql-migration-assistant": sql_migration_assistant
}


def main(raw):
    payload = json.loads(raw)
    command = payload["command"]
    if command not in MAPPING:
        msg = f"cannot find command: {command}"
        raise KeyError(msg)
    flags = payload["flags"]
    log_level = flags.pop("log_level")
    if log_level != "disabled":
        databricks_logger = logging.getLogger("databricks")
        databricks_logger.setLevel(log_level.upper())

    kwargs = {k.replace("-", "_"): v for k, v in flags.items()}
    MAPPING[command](**kwargs)


if __name__ == "__main__":
    main(*sys.argv[1:])
