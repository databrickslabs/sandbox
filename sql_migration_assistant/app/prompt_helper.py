import gradio as gr
class PromptHelper:
    def __init__(self, see, catalog, schema, prompt_table):
        self.see = see
        self.CATALOG = catalog
        self.SCHEMA = schema
        self.PROMPT_TABLE = prompt_table

    def get_prompts(self, agent):
        gr.Info("Retrieving Prompts...")
        response = self.see.execute(
            f"SELECT id, prompt, temperature, token_limit, save_time FROM {self.CATALOG}.{self.SCHEMA}.{self.PROMPT_TABLE} "
            f"WHERE agent = '{agent}' "
            f"ORDER BY save_time DESC "
        )
        return response.result.data_array

    def save_prompt(self, agent, prompt, temperature, token_limit):
        gr.Info("Saving prompt...")
        self.see.execute(
            f"INSERT INTO {self.CATALOG}.{self.SCHEMA}.{self.PROMPT_TABLE} "
            f"(agent, prompt, temperature, token_limit, save_time) "
            f"VALUES ('{agent}', '{prompt}',{temperature}, {token_limit}, CURRENT_TIMESTAMP())"
        )
        gr.Info("Prompt saved")
