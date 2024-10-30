import gradio as gr
class PromptHelper:
    def __init__(self, see, catalog, schema):
        self.see = see
        self.CATALOG = catalog
        self.SCHEMA = schema

    def get_prompts(self, agent):
        gr.Info("Retrieving Prompts...")
        response = self.see.execute(
            f"SELECT prompt FROM {self.CATALOG}.{self.SCHEMA}.sql_migration_assistant_prompt_history "
            f"WHERE agent = '{agent}' "
            f"ORDER BY save_time DESC "
        )
        return response.result.data_array

    def save_prompt(self, agent, prompt):
        self.see.execute(
            f"INSERT INTO {self.CATALOG}.{self.SCHEMA}.sql_migration_assistant_prompt_history "
            f"(agent, prompt, save_time) "
            f"VALUES ('{agent}', '{prompt}', CURRENT_TIMESTAMP())"
        )
        gr.Info("Prompt saved")
