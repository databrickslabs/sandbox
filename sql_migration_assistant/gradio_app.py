import json
import os
import datetime
from databricks.labs.lsql.core import StatementExecutionExt
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat, Language
import base64
import gradio as gr

from openai import OpenAI
from app.llm import LLMCalls
from app.similar_code import SimilarCode
from app.prompt_helper import PromptHelper
import logging  # For printing translation attempts in console (debugging)

# Setting up logger
logging.basicConfig
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# # personal access token necessary for authenticating API requests. Stored using a secret

FOUNDATION_MODEL_NAME = os.environ.get("SERVED_FOUNDATION_MODEL_NAME")
MAX_TOKENS = os.environ.get("MAX_TOKENS")
SQL_WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID")
VECTOR_SEARCH_ENDPOINT_NAME = os.environ.get("VECTOR_SEARCH_ENDPOINT_NAME")
VS_INDEX_NAME = os.environ.get("VS_INDEX_NAME")
CODE_INTENT_TABLE_NAME = os.environ.get("CODE_INTENT_TABLE_NAME")
PROMPT_HISTORY_TABLE_NAME = os.environ.get("PROMPT_HISTORY_TABLE_NAME")
CATALOG = os.environ.get("CATALOG")
SCHEMA = os.environ.get("SCHEMA")
VOLUME_NAME_INPUT_PATH = os.environ.get("VOLUME_NAME_INPUT_PATH")
VOLUME_NAME = os.environ.get("VOLUME_NAME")
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
DATABRICKS_TOKEN = os.environ.get('DATABRICKS_TOKEN')
TRANSFORMATION_JOB_ID = os.environ.get("TRANSFORMATION_JOB_ID")
WORKSPACE_LOCATION = os.environ.get("WORKSPACE_LOCATION")
w = WorkspaceClient(product="sql_migration_assistant", product_version="0.0.1")
openai_client = OpenAI(
  api_key=DATABRICKS_TOKEN,
  base_url=f"{DATABRICKS_HOST}/serving-endpoints"
)

see = StatementExecutionExt(w, warehouse_id=SQL_WAREHOUSE_ID)
translation_llm = LLMCalls(openai_client, foundation_llm_name=FOUNDATION_MODEL_NAME)
intent_llm = LLMCalls(openai_client, foundation_llm_name=FOUNDATION_MODEL_NAME)
similar_code_helper = SimilarCode(
    workspace_client=w,
    see=see,
    catalog=CATALOG,
    schema=SCHEMA,
    code_intent_table_name=CODE_INTENT_TABLE_NAME,
    VS_index_name=VS_INDEX_NAME,
    VS_endpoint_name=VECTOR_SEARCH_ENDPOINT_NAME,
)
prompt_helper = PromptHelper(see=see, catalog=CATALOG, schema=SCHEMA, prompt_table=PROMPT_HISTORY_TABLE_NAME)


################################################################################
################################################################################

# this is the app UI. it uses gradio blocks https://www.gradio.app/docs/gradio/blocks
# each gr.{} call adds a new element to UI, top to bottom.
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    # title with Databricks image
    gr.Markdown(
        """<img align="right" src="https://asset.brandfetch.io/idSUrLOWbH/idm22kWNaH.png" alt="logo" width="120">

# Databricks Legion Migration Accelerator
""")
    with gr.Tab("Instructions"):
        gr.Markdown("""
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

        operation = gr.Radio(
            label="Select operation mode",
            choices=["Interactive mode", "Batch mode"],
            value="Interactive mode",
            type="value",
            interactive=True,
        )
    ################################################################################
    #### STORAGE SETTINGS TAB
    ################################################################################

    with gr.Tab(label="Input code", visible=True) as interactive_input_code_tab:

        gr.Markdown(
            f"""## Paste in some code to test your agents on.   
            """
        )
        interactive_code_button = gr.Button("Ingest code")
        interactive_code = gr.Code(
            label="Paste your code in here", language="sql-msSQL"
        )
        interactive_code_button.click(fn=lambda: gr.Info("Code ingested!"))

    with gr.Tab(label="Select code", visible=False) as batch_input_code_tab:

        gr.Markdown(
            f"""## Select a file to test your agents on.   

           Legion can batch process a Volume of files to generate Databricks notebooks. The files to translate must be 
           added to the *Input Code* folder in the UC Volume [here]({DATABRICKS_HOST}/explore/data/volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}). 

           Here you can select a file to fine tune your agent prompts against. 
            """
        )
        volume_path = gr.Textbox(value=VOLUME_NAME_INPUT_PATH, visible=False)

        load_files = gr.Button("Load Files from Volume")
        select_code_file = gr.Radio(label="Select Code File")
        selected_file = gr.Code(label="Selected Code File", language="sql-msSQL")

        def list_files(path_to_volume):
            file_infos = w.dbutils.fs.ls(path_to_volume)
            file_names = [x.name for x in file_infos]
            file_name_radio = gr.Radio(label="Select Code File", choices=file_names)
            return file_name_radio

        load_files.click(list_files, volume_path, select_code_file)

        def read_code_file(volume_path, file_name):
            file_name = os.path.join(volume_path, file_name)
            file = w.files.download(file_name)
            code = file.contents.read().decode("utf-8")
            return code

    ################################################################################
    #### EXPLANATION TAB
    ################################################################################
    with gr.Tab(label="Code Explanation"):
        gr.Markdown(
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
                
                The *Temperature* parameter controls the randomness of the AI's response. Higher values will result in 
                more creative responses, while lower values will result in more predictable responses.
                """
            )

            with gr.Row():
                intent_temperature = gr.Number(
                    label="Temperature. Float between 0.0 and 1.0", value=0.0
                )
                intent_max_tokens = gr.Number(
                    label="Max tokens. Check your LLM docs for limit.", value=3500
                )
            with gr.Row():
                intent_system_prompt = gr.Textbox(
                    label="System prompt of the LLM to generate the intent.",
                    placeholder="Add your system prompt here, for example:\n"
                                "Explain the intent of this code with an example use case.",
                )
            # these bits relate to saving and loading of prompts
            with gr.Row():
                save_intent_prompt = gr.Button("Save intent prompt")
                load_intent_prompt = gr.Button("Load intent prompt")
            # hidden button and display box for saved prompts, made visible when the load button is clicked
            intent_prompt_id_to_load = gr.Textbox(
                label="Prompt ID to load",
                visible=False,
                placeholder="Enter the ID of the prompt to load from the table below."
            )
            loaded_intent_prompts = gr.Dataframe(
                label='Saved prompts.',
                visible=False,
                headers=["id", "Prompt", "Temperature", "Max Tokens", "Save Datetime"],
                interactive=False,
                wrap=True
            )
            # get the prompts and populate the table and make it visible
            load_intent_prompt.click(
                fn=lambda : gr.update(visible=True, value=prompt_helper.get_prompts("intent_agent")),
                inputs=None,
                outputs=[loaded_intent_prompts],
            )
            # make the input box for the prompt id visible
            load_intent_prompt.click(
                fn=lambda : gr.update(visible=True),
                inputs=None,
                outputs=[intent_prompt_id_to_load],
            )
            # retrive the row from the table and populate the system prompt, temperature, and max tokens
            def get_prompt_details(prompt_id, prompts):
                prompt = prompts[prompts["id"] == prompt_id]
                return [prompt["Prompt"].values[0], prompt["Temperature"].values[0], prompt["Max Tokens"].values[0]]

            intent_prompt_id_to_load.change(
                fn=get_prompt_details,
                inputs=[intent_prompt_id_to_load, loaded_intent_prompts],
                outputs=[intent_system_prompt, intent_temperature, intent_max_tokens]
            )
            # save the prompt
            save_intent_prompt.click(
                fn=lambda prompt, temp, tokens: prompt_helper.save_prompt("intent_agent", prompt, temp, tokens),
                inputs=[intent_system_prompt, intent_temperature, intent_max_tokens],
                outputs=None
            )


        with gr.Accordion(label="Intent Pane", open=True):
            gr.Markdown(
                """ ## AI generated intent of what your code aims to do. 
                        """
            )
            explain_button = gr.Button("Explain")
            with gr.Row():
                with gr.Column():
                    gr.Markdown(""" ## Input Code.""")

                    # input box for SQL code with nice formatting
                    intent_input_code = gr.Code(
                        label="Input SQL",
                        language="sql-msSQL",
                    )

                with gr.Column():
                    # divider subheader
                    gr.Markdown(""" ## Code intent""")
                    # output box of the T-SQL translated to Spark SQL
                    explained = gr.Textbox(label="AI generated intent of your code.")

            def llm_intent_wrapper(system_prompt, input_code, max_tokens, temperature):
                # call the LLM to translate the code
                intent = intent_llm.llm_intent(
                    system_prompt, input_code, max_tokens, temperature
                )
                return intent

            # reset hidden chat history and prompt
            # do translation
            explain_button.click(
                fn=llm_intent_wrapper,
                inputs=[
                    intent_system_prompt,
                    intent_input_code,
                    intent_max_tokens,
                    intent_temperature,
                ],
                outputs=explained,
            )
    ################################################################################
    #### TRANSLATION TAB
    ################################################################################
    with gr.Tab(label="Translation"):
        gr.Markdown(
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
                translation_temperature = gr.Number(
                    label="Temperature. Float between 0.0 and 1.0", value=0.0
                )
                translation_max_tokens = gr.Number(
                    label="Max tokens. Check your LLM docs for limit.", value=3500
                )
            with gr.Row():
                translation_system_prompt = gr.Textbox(
                    label="Instructions for the LLM translation tool.",
                    placeholder="Add your system prompt here, for example:\n"
                                "Translate this code to Spark SQL.",
                )
            with gr.Row():
                save_translation_prompt = gr.Button("Save translation prompt")
                load_translation_prompt = gr.Button("Load translation prompt")
            # hidden button and display box for saved prompts, made visible when the load button is clicked
            translation_prompt_id_to_load = gr.Textbox(
                label="Prompt ID to load",
                visible=False,
                placeholder="Enter the ID of the prompt to load from the table below."
            )
            loaded_translation_prompts = gr.Dataframe(
                label='Saved prompts.',
                visible=False,
                headers=["id", "Prompt", "Temperature", "Max Tokens", "Save Datetime"],
                interactive=False,
                wrap=True
            )
            # get the prompts and populate the table and make it visible
            load_translation_prompt.click(
                fn=lambda : gr.update(visible=True, value=prompt_helper.get_prompts("translation_agent")),
                inputs=None,
                outputs=[loaded_translation_prompts],
            )
            # make the input box for the prompt id visible
            load_translation_prompt.click(
                fn=lambda : gr.update(visible=True),
                inputs=None,
                outputs=[translation_prompt_id_to_load],
            )
            # retrive the row from the table and populate the system prompt, temperature, and max tokens
            translation_prompt_id_to_load.change(
                fn=get_prompt_details,
                inputs=[translation_prompt_id_to_load, loaded_translation_prompts],
                outputs=[translation_system_prompt, translation_temperature, translation_max_tokens]
            )

            save_translation_prompt.click(
                fn=lambda prompt, temp, tokens: prompt_helper.save_prompt("translation_agent", prompt, temp, tokens),
                inputs=[translation_system_prompt, translation_temperature, translation_max_tokens],
                outputs=None
            )


        with gr.Accordion(label="Translation Pane", open=True):
            gr.Markdown(""" ### Source code for translation to Spark-SQL.""")
            # a button labelled translate
            translate_button = gr.Button("Translate")
            with gr.Row():
                with gr.Column():
                    gr.Markdown(""" ## Input code.""")

                    # input box for SQL code with nice formatting
                    translation_input_code = gr.Code(
                        label="Input SQL",
                        language="sql-msSQL",
                    )

                with gr.Column():
                    # divider subheader
                    gr.Markdown(""" ## Translated Code""")
                    # output box of the T-SQL translated to Spark SQL
                    translated = gr.Code(
                        label="Your code translated to Spark SQL",
                        language="sql-sparkSQL",
                    )

            # helper function to take the output from llm_translate and return outputs for chatbox and textbox
            # chatbox input is a list of lists, each list is a message from the user and the response from the LLM
            # textbox input is a string
            def llm_translate_wrapper(
                system_prompt, input_code, max_tokens, temperature
            ):
                # call the LLM to translate the code
                translated_code = translation_llm.llm_translate(
                    system_prompt, input_code, max_tokens, temperature
                )
                return translated_code

            # reset hidden chat history and prompt
            # do translation
            translate_button.click(
                fn=llm_translate_wrapper,
                inputs=[
                    translation_system_prompt,
                    translation_input_code,
                    translation_max_tokens,
                    translation_temperature,
                ],
                outputs=translated,
            )

    ################################################################################
    #### SIMILAR CODE TAB
    ################################################################################
    with gr.Tab(label="Find Similar Code"):
        gr.Markdown(
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
            find_similar_code = gr.Button("Find similar code")
            # a row with an code and text box to show the similar code
            with gr.Row():
                similar_code_input = gr.Code(
                    label="Input Code.", language="sql-sparkSQL"
                )
                similar_code_output = gr.Code(
                    label="Similar code to yours.", language="sql-sparkSQL"
                )
                similar_intent = gr.Textbox(label="The similar codes intent.")

            # a button
            submit = gr.Button("Save code and intent")

            # assign actions to buttons when clicked.
        find_similar_code.click(
            fn=similar_code_helper.get_similar_code,
            inputs=similar_code_input,
            outputs=[similar_code_output, similar_intent],
        )

        def save_intent_wrapper(input_code, explained):
            gr.Info("Saving intent")
            similar_code_helper.save_intent(input_code, explained)
            gr.Info("Intent saved")

        submit.click(save_intent_wrapper, inputs=[translation_input_code, explained])

    ################################################################################
    #### EXECUTE JOB TAB
    ################################################################################
    with gr.Tab(label="Execute Job", visible=False) as batch_output_tab:
        gr.Markdown(
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
        execute = gr.Button(
            value="EXECUTE CODE TRANSFORMATION",
            size="lg",
        )
        run_status = gr.Markdown(label="Job Status Page", visible=False)

        def exectute_workflow(
            intent_prompt,
            intent_temperature,
            intent_max_tokens,
            translation_prompt,
            translation_temperature,
            translation_max_tokens,
        ):
            gr.Info("Beginning code transformation workflow")
            agent_config_payload = [
                [
                    {
                        "translation_agent": {
                            "system_prompt": translation_prompt,
                            "endpoint": FOUNDATION_MODEL_NAME,
                            "max_tokens": translation_max_tokens,
                            "temperature": translation_temperature,
                        }
                    }
                ],
                [
                    {
                        "explanation_agent": {
                            "system_prompt": intent_prompt,
                            "endpoint": FOUNDATION_MODEL_NAME,
                            "max_tokens": intent_max_tokens,
                            "temperature": intent_temperature,
                        }
                    }
                ],
            ]

            app_config_payload = {
                "VOLUME_NAME_OUTPUT_PATH": os.environ.get("VOLUME_NAME_OUTPUT_PATH"),
                "VOLUME_NAME_INPUT_PATH": os.environ.get("VOLUME_NAME_INPUT_PATH"),
                "VOLUME_NAME_CHECKPOINT_PATH": os.environ.get(
                    "VOLUME_NAME_CHECKPOINT_PATH"
                ),
                "CATALOG": os.environ.get("CATALOG"),
                "SCHEMA": os.environ.get("SCHEMA"),
                "DATABRICKS_HOST": DATABRICKS_HOST,
                "DATABRICKS_TOKEN_SECRET_SCOPE": os.environ.get(
                    "DATABRICKS_TOKEN_SECRET_SCOPE"
                ),
                "DATABRICKS_TOKEN_SECRET_KEY": os.environ.get(
                    "DATABRICKS_TOKEN_SECRET_KEY"
                ),
                "CODE_INTENT_TABLE_NAME": os.environ.get("CODE_INTENT_TABLE_NAME"),
                "WORKSPACE_LOCATION": WORKSPACE_LOCATION,
            }

            app_configs = json.dumps(app_config_payload)
            agent_configs = json.dumps(agent_config_payload)

            response = w.jobs.run_now(
                job_id=int(TRANSFORMATION_JOB_ID),
                job_parameters={
                    "agent_configs": agent_configs,
                    "app_configs": app_configs,
                },
            )
            run_id = response.run_id

            job_url = f"{DATABRICKS_HOST}/jobs/{TRANSFORMATION_JOB_ID}"
            textbox_message = (
                f"Job run initiated. Click [here]({job_url}) to view the job status. "
                f"You just executed the run with run_id: {run_id}\n"
                f"Output notebooks will be written to the Workspace for immediate use at *{WORKSPACE_LOCATION}/outputNotebooks*"
                f", and also in the *Output Code* folder in the UC Volume [here]({DATABRICKS_HOST}/explore/data/volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME})"
            )
            return textbox_message

        def make_status_box_visible():
            return gr.Markdown(label="Job Run Status Page", visible=True)

        execute.click(fn=make_status_box_visible, outputs=run_status)
        execute.click(
            exectute_workflow,
            inputs=[
                intent_system_prompt,
                intent_temperature,
                intent_max_tokens,
                translation_system_prompt,
                translation_temperature,
                translation_max_tokens,
            ],
            outputs=run_status,
        )

    with gr.Tab(label="Write file to Workspace") as interactive_output_tab:
        gr.Markdown(
            f""" ## Write to Workspace

            Write out your explained and translated file to a notebook in the workspace. 
            You must provide a filename for the notebook. The notebook will be written to the workspace, saved to the 
            Output Code location in the Unity Catalog Volume [here]({DATABRICKS_HOST}/explore/data/volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}) 
            , and the intent will be saved to the intent table. 
            """
        )
        template = """
-- Databricks notebook source
-- MAGIC %md
-- MAGIC # This notebook was AI generated. AI can make mistakes. This is provided as a tool to accelerate your migration. 
-- MAGIC
-- MAGIC ### AI Generated Intent
-- MAGIC
-- MAGIC INTENT_GOES_HERE

-- COMMAND ----------

TRANSLATED_CODE_GOES_HERE
          """
        with gr.Row():
            produce_preview_button = gr.Button("Produce Preview")
            with gr.Column():
                file_name = gr.Textbox(label="Filename for the notebook")
                write_to_workspace_button = gr.Button("Write to Workspace")
                adhoc_write_output = gr.Markdown(label="Notebook output location")

        def produce_preview(explanation, translated_code):
            preview_code = template.replace("INTENT_GOES_HERE", explanation).replace(
                "TRANSLATED_CODE_GOES_HERE", translated_code
            )
            return preview_code

        def write_adhoc_to_workspace(file_name, preview):

            if len(file_name) == 0:
                raise gr.Error("Please provide a filename")

            notebook_path_root = f"{WORKSPACE_LOCATION}/outputNotebooks/{str(datetime.datetime.now()).replace(':', '_')}"
            notebook_path = f"{notebook_path_root}/{file_name}"
            content = preview
            w.workspace.mkdirs(notebook_path_root)
            w.workspace.import_(
                content=base64.b64encode(content.encode("utf-8")).decode("utf-8"),
                path=notebook_path,
                format=ImportFormat.SOURCE,
                language=Language.SQL,
                overwrite=True,
            )
            _ = w.workspace.get_status(notebook_path)
            id = _.object_id
            url = f"{w.config.host}/#notebook/{id}"
            output_message = f"Notebook {file_name} written to Databricks [here]({url})"
            return output_message

        preview = gr.Code(label="Preview", language="python")
        produce_preview_button.click(
            produce_preview, inputs=[explained, translated], outputs=preview
        )

        # write file to notebook
        write_to_workspace_button.click(
            fn=write_adhoc_to_workspace,
            inputs=[file_name, preview],
            outputs=adhoc_write_output,
        )

    with gr.Tab(label="Feedback"):
        gr.Markdown(
            """
        ## Comments? Feature Suggestions? Bugs?
        
        Below is the link to the Legion Github repo for you to raise an issue. 
        
        On the right hand side of the Issue page, please assign it to **robertwhiffin**, and select the project **Legion**. 

        Raise the issue on the Github repo for Legion [here](https://github.com/databrickslabs/sandbox/issues/new).        
        """
        )

    # this handles the code loading for batch mode
    # read the selected code file and put it into the other panes
    for output in [
        selected_file,
        translation_input_code,
        intent_input_code,
        similar_code_input,
    ]:
        select_code_file.select(
            fn=read_code_file, inputs=[volume_path, select_code_file], outputs=output
        )

    # this handles the code loading for interative mode
    for output in [
        translation_input_code,
        intent_input_code,
        similar_code_input,
    ]:
        interactive_code_button.click(
            fn=lambda x: gr.update(value=x), inputs=interactive_code, outputs=output
        )

    # change the input tabs based on the operation mode
    operation.change(
        lambda x: (
            gr.update(visible=False)
            if x == "Interactive mode"
            else gr.update(visible=True)
        ),
        operation,
        batch_input_code_tab,
    )
    operation.change(
        lambda x: (
            gr.update(visible=True)
            if x == "Interactive mode"
            else gr.update(visible=False)
        ),
        operation,
        interactive_input_code_tab,
    )

    # change the output tabs based on the operation mode
    operation.change(
        lambda x: (
            gr.update(visible=False)
            if x == "Interactive mode"
            else gr.update(visible=True)
        ),
        operation,
        batch_output_tab,
    )
    operation.change(
        lambda x: (
            gr.update(visible=True)
            if x == "Interactive mode"
            else gr.update(visible=False)
        ),
        operation,
        interactive_output_tab,
    )

# for local dev
try:
    if os.environ["LOCALE"] == "local_dev":
        demo.queue().launch()
except KeyError:
    pass

# this is necessary to get the app to run on databricks
if __name__ == "__main__":
    demo.queue().launch(
        server_name=os.getenv("GRADIO_SERVER_NAME"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT")),
    )
