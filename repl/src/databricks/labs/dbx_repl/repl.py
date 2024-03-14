from prompt_toolkit import PromptSession
from databricks.labs.dbx_repl.context_handler import ContextHandler

def repl(client, language, cluster_id):
    prompt = f"[{cluster_id}][{language.value}]>"
    session = PromptSession()

    handler = ContextHandler(client, cluster_id, language)

    while True:
        try:
            text = session.prompt(prompt)
            handler.execute(text)
        except (EOFError, KeyboardInterrupt):
            break  # Exit the loop if Ctrl-D or Ctrl-C is pressed
            # TODO: add exit hook to close context via handler.close()
    print("Exiting REPL...")