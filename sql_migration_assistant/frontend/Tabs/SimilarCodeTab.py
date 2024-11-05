import gradio as gr

from sql_migration_assistant.frontend.callbacks import similar_code_helper


class SimilarCodeTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self):
        with gr.Tab(label="Find Similar Code") as tab:
            self.tab = tab
            self.header = gr.Markdown(
                """
            # ** Work in Progress **
            ## An AI tool to find similar code.
            """
            )
            with gr.Accordion(label="Similar Code Pane", open=True):
                gr.Markdown(
                    """ ## Similar code 
                            
                            This code is thought to be similar to what you are doing, based on comparing the intent of your code with the intent of this code.
                            """
                )
                # a button
                self.find_similar_code = gr.Button("Find similar code")
                # a row with an code and text box to show the similar code
                with gr.Row():
                    self.similar_code_input = gr.Code(
                        label="Input Code.", language="sql-sparkSQL"
                    )
                    self.similar_code_output = gr.Code(
                        label="Similar code to yours.", language="sql-sparkSQL"
                    )
                    self.similar_intent = gr.Textbox(label="The similar codes intent.")

                # a button
                self.submit = gr.Button("Save code and intent")

                # assign actions to buttons when clicked.
            self.find_similar_code.click(
                fn=similar_code_helper.get_similar_code,
                inputs=self.similar_code_input,
                outputs=[self.similar_code_output, self.similar_intent],
            )
