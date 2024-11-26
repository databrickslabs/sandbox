import gradio as gr

from sql_migration_assistant.frontend.callbacks import (
    llm_intent_wrapper,
    get_prompt_details,
    prompt_helper,
)


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
                        placeholder="Add your system prompt here, for example:\n"
                        "Explain the intent of this code with an example use case.",
                        lines=3,
                    )
                    # these bits relate to saving and loading of prompts
                    with gr.Row():
                        self.save_intent_prompt = gr.Button("Save intent prompt")
                        self.load_intent_prompt = gr.Button("Load intent prompt")
                    # hidden button and display box for saved prompts, made visible when the load button is clicked
                    self.intent_prompt_id_to_load = gr.Textbox(
                        label="Prompt ID to load",
                        visible=False,
                        placeholder="Enter the ID of the prompt to load from the table below.",
                    )
                    self.loaded_intent_prompts = gr.Dataframe(
                        label="Saved prompts.",
                        visible=False,
                        headers=[
                            "id",
                            "Prompt",
                            "Temperature",
                            "Max Tokens",
                            "Save Datetime",
                        ],
                        interactive=False,
                        wrap=True,
                    )
                    # get the prompts and populate the table and make it visible
                    self.load_intent_prompt.click(
                        fn=lambda: gr.update(
                            visible=True,
                            value=prompt_helper.get_prompts("intent_agent"),
                        ),
                        inputs=None,
                        outputs=[self.loaded_intent_prompts],
                    )
                    # make the input box for the prompt id visible
                    self.load_intent_prompt.click(
                        fn=lambda: gr.update(visible=True),
                        inputs=None,
                        outputs=[self.intent_prompt_id_to_load],
                    )

                    self.intent_prompt_id_to_load.change(
                        fn=get_prompt_details,
                        inputs=[
                            self.intent_prompt_id_to_load,
                            self.loaded_intent_prompts,
                        ],
                        outputs=[
                            self.intent_system_prompt,
                            self.intent_temperature,
                            self.intent_max_tokens,
                        ],
                    )
                    # save the prompt
                    self.save_intent_prompt.click(
                        fn=lambda prompt, temp, tokens: prompt_helper.save_prompt(
                            "intent_agent", prompt, temp, tokens
                        ),
                        inputs=[
                            self.intent_system_prompt,
                            self.intent_temperature,
                            self.intent_max_tokens,
                        ],
                        outputs=None,
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
                        self.explained = gr.Textbox(
                            label="AI generated intent of your code."
                        )

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
