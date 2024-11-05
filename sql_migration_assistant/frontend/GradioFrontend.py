import gradio as gr

from sql_migration_assistant.frontend.Tabs.BatchInputCodeTab import BatchInputCodeTab
from sql_migration_assistant.frontend.Tabs.CodeExplanationTab import CodeExplanationTab
from sql_migration_assistant.frontend.Tabs.BatchOutputTab import BatchOutputTab
from sql_migration_assistant.frontend.Tabs.InteractiveInputCodeTab import InteractiveInputCodeTab
from sql_migration_assistant.frontend.Tabs.SimilarCodeTab import SimilarCodeTab
from sql_migration_assistant.frontend.Tabs.TranslationTab import TranslationTab
from sql_migration_assistant.frontend.Tabs.InteractiveOutputTab import InteractiveOutputTab
from sql_migration_assistant.frontend.callbacks import (
    read_code_file,
    produce_preview,
    exectute_workflow,
    save_intent_wrapper,
)


class GradioFrontend:
    intro = """<img align="right" src="https://asset.brandfetch.io/idSUrLOWbH/idm22kWNaH.png" alt="logo" width="120">

# Databricks Legion Migration Accelerator

Legion is an AI powered tool that aims to accelerate the migration of code to Databricks for low cost and effort. It 
does this by using AI to translate, explain, and make discoverable your code. 

This interface is the Legion Control Panel. Here you are able to configure the AI agents for translation and explanation
to fit your needs, incorporating your expertise and knowledge of the codebase by adjusting the AI agents' instructions.

Legion can work in a batch or interactive fashion.

*Interactive operation*
Fine tune the AI agents on a single file and output the result as a Databricks notebook. 
Use this UI to adjust the system prompts and instructions for the AI agents to generate the best translation and intent.

*Batch operation*
Process a Volume of files to generate Databricks notebooks. Use this UI to fine tune your agent prompts against selected
 files before executing a Workflow to transform all files in the Volume, outputting Databricks notebooks with the AI
 generated intent and translation.


Please select your mode of operation to get started.   

"""

    def __init__(self):
        with gr.Blocks(theme=gr.themes.Soft()) as self.app:
            self.intro_markdown = gr.Markdown(self.intro)
            self.operation = gr.Radio(
                label="Select operation mode",
                choices=["Interactive mode", "Batch mode"],
                value="Interactive mode",
                type="value",
                interactive=True,
            )

            self.interactive_input_code_tab = InteractiveInputCodeTab()
            self.batch_input_code_tab = BatchInputCodeTab()
            self.code_explanation_tab = CodeExplanationTab()
            self.translation_tab = TranslationTab()
            self.similar_code_tab = SimilarCodeTab()
            self.batch_output_tab = BatchOutputTab()
            self.interactive_output_tab = InteractiveOutputTab()

            self.similar_code_tab.submit.click(save_intent_wrapper, inputs=[self.translation_tab.translation_input_code,
                                                                            self.code_explanation_tab.explained])
            self.batch_output_tab.execute.click(
                exectute_workflow,
                inputs=[
                    self.code_explanation_tab.intent_system_prompt,
                    self.code_explanation_tab.intent_temperature,
                    self.code_explanation_tab.intent_max_tokens,
                    self.translation_tab.translation_system_prompt,
                    self.translation_tab.translation_temperature,
                    self.translation_tab.translation_max_tokens,
                ],
                outputs=self.batch_output_tab.run_status,
            )
            self.interactive_output_tab.produce_preview_button.click(
                produce_preview, inputs=[self.code_explanation_tab.explained, self.translation_tab.translated],
                outputs=self.interactive_output_tab.preview
            )
            self.add_logic_loading_batch_mode()
            self.add_logic_loading_interactive_mode()
            self.change_tabs_based_on_operation_mode()

    def add_logic_loading_batch_mode(self):
        for output in [
            self.batch_input_code_tab.selected_file,
            self.translation_tab.translation_input_code,
            self.code_explanation_tab.intent_input_code,
            self.similar_code_tab.similar_code_input,
        ]:
            self.batch_input_code_tab.select_code_file.select(
                fn=read_code_file,
                inputs=[self.batch_input_code_tab.volume_path, self.batch_input_code_tab.select_code_file],
                outputs=output
            )

    def add_logic_loading_interactive_mode(self):
        for output in [
            self.translation_tab.translation_input_code,
            self.code_explanation_tab.intent_input_code,
            self.similar_code_tab.similar_code_input,
        ]:
            self.interactive_input_code_tab.interactive_code_button.click(
                fn=lambda x: gr.update(value=x), inputs=self.interactive_input_code_tab.interactive_code, outputs=output
            )

    def change_tabs_based_on_operation_mode(self):
        for tab in [self.batch_input_code_tab, self.batch_output_tab]:
            self.operation.change(
                lambda x: (
                    gr.update(visible=(x != "Interactive mode"))
                ),
                self.operation,
                tab.tab,
            )
        for tab in [self.interactive_input_code_tab, self.interactive_output_tab]:
            self.operation.change(
                lambda x: (
                    gr.update(visible=(x == "Interactive mode"))
                ),
                self.operation,
                tab.tab,
            )
