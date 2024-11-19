import gradio as gr

from sql_migration_assistant.config import DATABRICKS_HOST, CATALOG, SCHEMA, VOLUME_NAME, VOLUME_NAME_INPUT_PATH
from sql_migration_assistant.frontend.callbacks import list_files


class BatchInputCodeTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self):
        with gr.Tab(label="Select code", visible=False) as tab:
            self.tab = tab
            self.header = gr.Markdown(
                f"""## Select a file to test your agents on.   

               Legion can batch process a Volume of files to generate Databricks notebooks. The files to translate must be 
               added to the *Input Code* folder in the UC Volume [here]({DATABRICKS_HOST}/explore/data/volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}). 

               Here you can select a file to fine tune your agent prompts against. 
                """
            )
            self.volume_path = gr.Textbox(value=VOLUME_NAME_INPUT_PATH, visible=False)

            self.load_files = gr.Button("Load Files from Volume")
            self.select_code_file = gr.Radio(label="Select Code File")
            self.selected_file = gr.Code(label="Selected Code File", language="sql-msSQL")

            self.load_files.click(list_files, self.volume_path, self.select_code_file)
