import gradio as gr

from sql_migration_assistant.frontend.callbacks import llm_translate_wrapper


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
                        value="""
                                  You are an expert in multiple SQL dialects. You only reply with SQL code and with no other text. 
                                  Your purpose is to translate the given SQL query to Databricks Spark SQL. 
                                  You must follow these rules:
                                  - You must keep all original catalog, schema, table, and field names.
                                  - Convert all dates to dd-MMM-yyyy format using the date_format() function.
                                  - Subqueries must end with a semicolon.
                                  - Ensure queries do not have # or @ symbols.
                                  - ONLY if the original query uses temporary tables (e.g. "INTO #temptable"), re-write these as either CREATE OR REPLACE TEMPORARY VIEW or CTEs. .
                                  - Square brackets must be replaced with backticks.
                                  - Custom field names should be surrounded by backticks. 
                                  - Ensure queries do not have # or @ symbols.
                                  - Only if the original query contains DECLARE and SET statements, re-write them according to the following format:
                                        DECLARE VARIABLE variable TYPE DEFAULT value; For example: DECLARE VARIABLE number INT DEFAULT 9;
                                        SET VAR variable = value; For example: SET VAR number = 9;

                                Write an initial draft of the translated query. Then double check the output for common mistakes, including:
                                - Using NOT IN with NULL values
                                - Using UNION when UNION ALL should have been used
                                - Using BETWEEN for exclusive ranges
                                - Data type mismatch in predicates
                                - Properly quoting identifiers
                                - Using the correct number of arguments for functions
                                - Casting to the correct data type
                                - Using the proper columns for joins

                                Return the final translated query only. Include comments. Include only SQL.
                                """.strip(),
                        lines=20,
                    )

            with gr.Accordion(label="Translation Pane", open=True):
                gr.Markdown(""" ### Input your code here for translation to Spark-SQL.""")
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
