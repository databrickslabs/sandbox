import json
import logging
import sys
import os
import webbrowser

logger = logging.getLogger("databricks.labs.sandbox")


def ip_access_list_analyzer(**args):
    import ip_access_list_analyzer.ip_acl_analyzer as analyzer
    analyzer.main(args)

def repl(**args):
    from repl.src.databricks.labs.dbx_repl import labs_main
    labs_main.labs_main(args["lang"], args["cluster_id"])

MAPPING = {
    "ip-access-list-analyzer": ip_access_list_analyzer,
    "repl": repl
}

def main(raw):
    print("raw: ", raw)

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
