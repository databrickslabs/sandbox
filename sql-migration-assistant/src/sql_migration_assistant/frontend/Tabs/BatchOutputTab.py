import gradio as gr

from sql_migration_assistant.frontend.callbacks import make_status_box_visible


class BatchOutputTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self):
        with gr.Tab(label="Execute Job", visible=False) as tab:
            self.tab = tab
            self.header = gr.Markdown(
                """ ## Execute Job
    
                This tab is for executing the job to covert the code files in the Unity Catalog Volume to Databricks 
                Notebooks. Once you are happy with your system prompts and and the explanation and translation outputs, 
                click the execute button below. 
                
                This will kick off a Workflow which will ingest the code files, write them to a Delta Table, apply the AI
                agents, and output a Databricks Notebook per input code file. This notebook will have the intent at the top 
                of the notebook in a markdown cell, and the translated code in the cell below. These notebooks are found in 
                the workspace at *{WORKSPACE_LOCATION}/outputNotebooks* and in the *Output Code* folder in the UC Volume
                
                The intent will also be stored in a Unity Catalog table and vector search index for finding similar code. 
                """
            )
            self.execute = gr.Button(
                value="EXECUTE CODE TRANSFORMATION",
                size="lg",
            )
            self.run_status = gr.Markdown(label="Job Status Page", visible=False)

            self.execute.click(fn=make_status_box_visible, outputs=self.run_status)
