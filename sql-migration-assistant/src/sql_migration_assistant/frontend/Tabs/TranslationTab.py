import gradio as gr

from sql_migration_assistant.frontend.callbacks import llm_translate_wrapper, prompt_helper, get_prompt_details


class TranslationTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self):
        with gr.Tab(label="Translation") as tab:
            self.tab = tab
            self.header = gr.Markdown(
                """
            ## An AI tool to translate your code.
    
            In this panel you need to iterate on the system prompt to refine the translation the AI generates for your code.
          
            """
            )
            with gr.Accordion(label="Translation Advanced Settings", open=True):
                gr.Markdown(
                    """ ### Advanced settings for the translating the input code.

                    The *Temperature* paramater controls the randomness of the AI's response. Higher values will result in 
                    more creative responses, while lower values will result in more predictable responses.
                    """
                )
                with gr.Row():
                    self.translation_temperature = gr.Number(
                        label="Temperature. Float between 0.0 and 1.0", value=0.0
                    )
                    self.translation_max_tokens = gr.Number(
                        label="Max tokens. Check your LLM docs for limit.", value=3500
                    )
                with gr.Row():
                    self.translation_system_prompt = gr.Textbox(
                        label="Instructions for the LLM translation tool.",
                        placeholder="Add your system prompt here, for example:\n"
                                    "Translate this code to Spark SQL.",
                        lines=3
                    )
                with gr.Row():
                    self.save_translation_prompt = gr.Button("Save translation prompt")
                    self.load_translation_prompt = gr.Button("Load translation prompt")
                # hidden button and display box for saved prompts, made visible when the load button is clicked
                self.translation_prompt_id_to_load = gr.Textbox(
                    label="Prompt ID to load",
                    visible=False,
                    placeholder="Enter the ID of the prompt to load from the table below."
                )
                self.loaded_translation_prompts = gr.Dataframe(
                    label='Saved prompts.',
                    visible=False,
                    headers=["id", "Prompt", "Temperature", "Max Tokens", "Save Datetime"],
                    interactive=False,
                    wrap=True
                )
                # get the prompts and populate the table and make it visible
                self.load_translation_prompt.click(
                    fn=lambda: gr.update(visible=True, value=prompt_helper.get_prompts("translation_agent")),
                    inputs=None,
                    outputs=[self.loaded_translation_prompts],
                )
                # make the input box for the prompt id visible
                self.load_translation_prompt.click(
                    fn=lambda: gr.update(visible=True),
                    inputs=None,
                    outputs=[self.translation_prompt_id_to_load],
                )
                # retrive the row from the table and populate the system prompt, temperature, and max tokens
                self.translation_prompt_id_to_load.change(
                    fn=get_prompt_details,
                    inputs=[self.translation_prompt_id_to_load, self.loaded_translation_prompts],
                    outputs=[self.translation_system_prompt, self.translation_temperature, self.translation_max_tokens]
                )
                self.save_translation_prompt.click(
                    fn=lambda prompt, temp, tokens: prompt_helper.save_prompt("translation_agent", prompt, temp,
                                                                              tokens),
                    inputs=[self.translation_system_prompt, self.translation_temperature, self.translation_max_tokens],
                    outputs=None
                )

            with gr.Accordion(label="Translation Pane", open=True):
                gr.Markdown(""" ### Source code for translation to Spark-SQL.""")
                # a button labelled translate
                self.translate_button = gr.Button("Translate")
                with gr.Row():
                    with gr.Column():
                        gr.Markdown(""" ## Input code.""")

                        # input box for SQL code with nice formatting
                        self.translation_input_code = gr.Code(
                            label="Input SQL",
                            language="sql-msSQL",
                        )

                    with gr.Column():
                        # divider subheader
                        gr.Markdown(""" ## Translated Code""")
                        # output box of the T-SQL translated to Spark SQL
                        self.translated = gr.Code(
                            label="Your code translated to Spark SQL",
                            language="sql-sparkSQL",
                        )

                # reset hidden chat history and prompt
                # do translation
                self.translate_button.click(
                    fn=llm_translate_wrapper,
                    inputs=[
                        self.translation_system_prompt,
                        self.translation_input_code,
                        self.translation_max_tokens,
                        self.translation_temperature,
                    ],
                    outputs=self.translated,
                )
