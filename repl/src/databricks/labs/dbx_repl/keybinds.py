from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.application import run_in_terminal



def bottom_toolbar():
    return HTML(
        'This is a <b><style bg="ansired">Choose Language: (1) Python (2) SQL (3) Scala (4) R</style></b>!'
    )


def repl_keybinds(handler):

    kb = KeyBindings()

    @kb.add("c-l")
    def _(event):
        """
        Change Language via toolbar selection
        """
        try:
            raise KeyboardInterrupt
        except Exception as e:
            handler.switch_language()

    return kb
