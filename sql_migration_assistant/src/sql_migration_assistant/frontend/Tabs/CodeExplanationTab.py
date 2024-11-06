import gradio as gr

from sql_migration_assistant.frontend.callbacks import llm_intent_wrapper


class CodeExplanationTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self):
        with gr.Tab(label="Code Explanation") as tab:
            self.tab = tab
            self.header = gr.Markdown(
                """
                ## An AI tool to generate the intent of your code.
        
                In this panel you need to iterate on the system prompt to refine the intent the AI generates for your code.
                This intent will be stored in Unity Catalog, and can be used for finding similar code, for documentation, 
                 and to help with writing new code in Databricks to achieve the same goal.
                """
            )
            with gr.Accordion(label="Advanced Intent Settings", open=True):
                gr.Markdown(
                    """ ### Advanced settings for the generating the intent of the input code.

                    The *Temperature* paramater controls the randomness of the AI's response. Higher values will result in 
                    more creative responses, while lower values will result in more predictable responses.
                    """
                )

                with gr.Row():
                    self.intent_temperature = gr.Number(
                        label="Temperature. Float between 0.0 and 1.0", value=0.0
                    )
                    self.intent_max_tokens = gr.Number(
                        label="Max tokens. Check your LLM docs for limit.", value=3500
                    )
                with gr.Row():
                    self.intent_system_prompt = gr.Textbox(
                        label="System prompt of the LLM to generate the intent.",
                        value="""Your job is to explain intent of the provided SQL code.
                                """.strip(),
                    )

            with gr.Accordion(label="Intent Pane", open=True):
                gr.Markdown(
                    """ ## AI generated intent of what your code aims to do. 
                            """
                )
                self.explain_button = gr.Button("Explain")
                with gr.Row():
                    with gr.Column():
                        gr.Markdown(""" ## Input Code.""")

                        # input box for SQL code with nice formatting
                        self.intent_input_code = gr.Code(
                            label="Input SQL",
                            language="sql-msSQL",
                        )
                        # a button labelled translate

                    with gr.Column():
                        # divider subheader
                        gr.Markdown(""" ## Code intent""")
                        # output box of the T-SQL translated to Spark SQL
                        self.explained = gr.Textbox(label="AI generated intent of your code.")

                # reset hidden chat history and prompt
                # do translation
                self.explain_button.click(
                    fn=llm_intent_wrapper,
                    inputs=[
                        self.intent_system_prompt,
                        self.intent_input_code,
                        self.intent_max_tokens,
                        self.intent_temperature,
                    ],
                    outputs=self.explained,
                )
