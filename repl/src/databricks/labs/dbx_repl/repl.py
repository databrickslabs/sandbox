from .context_handler import ContextHandler

def repl(client, language, cluster_id):

    handler = ContextHandler(client, cluster_id, language)

    while True:
        try:
            handler.prompt_and_execute()
        except KeyboardInterrupt:
            continue
        except EOFError:
            handler.close()
            break  # Exit the loop if Ctrl-D or Ctrl-C is pressed
    print("Exiting REPL...")