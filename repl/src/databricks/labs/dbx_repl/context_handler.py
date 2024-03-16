import os
from databricks.sdk import WorkspaceClient
from .helpers import (
    Language,
    parse_command_output,
    validate_language,
    get_lexer,
    repl_styled_prompt,
    prompt_continuation,
)
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.patch_stdout import patch_stdout


class ContextHandler:
    def __init__(
        self,
        client: WorkspaceClient,
        cluster_id: str,
        language: Language,
        # multiline: str,
    ):

        # Create context
        self._client = client
        self._language = language
        self._cluster_id = cluster_id
        self._context_id = client.command_execution.create_and_wait(
            cluster_id=self._cluster_id, language=self._language
        ).id
        # self._multiline = multiline

        os.makedirs(os.path.expanduser("~/.databricks"), exist_ok=True)
        self._history = FileHistory(os.path.expanduser("~/.databricks/repl_history"))

        # Setup keybinds and prompt session
        self._prompt_session = PromptSession(
            lexer=PygmentsLexer(get_lexer(self._language)),
            history=self._history,
            # multiline=self._multiline
        )

    def close(self):
        self._client.command_execution.destroy(self._cluster_id, self._context_id)
        pass

    def prompt(self) -> str:
        message, style = repl_styled_prompt(self._cluster_id, self._language)
        with patch_stdout():
            result = self._prompt_session.prompt(
                message=message,
                style=style,
                prompt_continuation=prompt_continuation,
                # multiline=True,
            )
            return result

    def is_language_switch_command(self, cmd: str):
        cmd = cmd.strip().lower()
        if not cmd.startswith(":"):
            return False

        try:
            validate_language(cmd[1:])
        except ValueError:
            return False
        return True

    def set_language(self, new_language):
        new_language = new_language.strip().lower().split(":")[1]

        if new_language != self._language.value:
            try:
                self._language = validate_language(new_language)
                self._prompt_session.lexer = PygmentsLexer(get_lexer(self._language))
            except ValueError as e:
                print(e)

    def execute(self, cmd: str) -> str:
        if self.is_language_switch_command(cmd):
            self.set_language(cmd)
            return None

        try:
            result_raw = self._client.command_execution.execute_and_wait(
                cluster_id=self._cluster_id,
                command=cmd,
                context_id=self._context_id,
                language=self._language,
            )
            result_parsed = parse_command_output(result_raw, self._language)
            if result_parsed is not None:
                print(result_parsed)
            return result_parsed
        except Exception as e:
            return None

    def prompt_and_execute(self) -> str:
        text = self.prompt()
        return self.execute(text)
