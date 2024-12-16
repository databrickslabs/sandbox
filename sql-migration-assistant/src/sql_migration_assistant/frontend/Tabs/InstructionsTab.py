import gradio as gr


class InstructionsTab:
    header: gr.Markdown
    tab: gr.Tab

    def __init__(self):
        with gr.Tab(label="Instructions") as self.tab:
            self.header = gr.Markdown(
                """
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
            )
            self.operation = gr.Radio(
                label="Select operation mode",
                choices=["Interactive mode", "Batch mode"],
                value="Interactive mode",
                type="value",
                interactive=True,
            )
