import gradio as gr


class InteractiveInputCodeTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self):
        with gr.Tab(label="Input code", visible=True) as tab:
            self.header = gr.Markdown(
                f"""## Paste in some code to test your agents on.   
                """
            )
            self.interactive_code_button = gr.Button("Ingest code")
            self.interactive_code = gr.Code(
                label="Paste your code in here", language="sql-msSQL"
            )
            self.interactive_code_button.click(fn=lambda: gr.Info("Code ingested!"))

            self.tab = tab
