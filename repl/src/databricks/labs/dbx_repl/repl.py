from .context_handler import ContextHandler
from prompt_toolkit import print_formatted_text, HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText

def welcome():
    
    style = Style.from_dict({
        'welcome': 'ansiyellow',
        'code': '#ff0000'
    })

    print_formatted_text(HTML('''<welcome>Welcome to the Databricks REPL!
 * Press Ctrl-D to exit
 * Type <code>:python</code>, <code>:r</code>, <code>:sql</code>, or <code>:scala</code> to switch languages
</welcome>'''), style=style)


def repl(client, language, cluster_id):

    welcome()
    handler = ContextHandler(client, cluster_id, language)

    while True:
        try:
            handler.prompt_and_execute()
        except KeyboardInterrupt:
            # handler.cancel_active_command()
            continue
        except EOFError:
            handler.close()
            break  # Exit the loop if Ctrl-D is pressed
    print("Exiting REPL...")