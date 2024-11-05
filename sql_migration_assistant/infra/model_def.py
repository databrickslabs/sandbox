import os
from operator import itemgetter

import mlflow
from langchain_community.chat_models import ChatDatabricks
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.runnables import RunnableLambda, RunnableBranch, RunnablePassthrough
from mlflow.tracking import MlflowClient


def create_langchain_chat_model():
    # ## Enable MLflow Tracing
    mlflow.login()
    mlflow.langchain.autolog()
    mlflow.set_registry_uri("databricks-uc")
    ############

    FOUNDATION_MODEL = os.environ.get("SERVED_FOUNDATION_MODEL_NAME")
    experiment_name = os.environ.get("MLFLOW_EXPERIMENT_NAME")
    catalog = os.environ.get("CATALOG")
    schema = os.environ.get("SCHEMA")
    UC_MODEL_NAME = os.environ.get("MLFLOW_MODEL_NAME")
    fully_qualified_name = f"{catalog}.{schema}.{UC_MODEL_NAME}"

    # check if the model already exists and if so, return
    client = MlflowClient()
    model_version_infos = client.search_model_versions(
        "name = '%s'" % fully_qualified_name
    )
    if len(model_version_infos) > 0:
        return

    # Helper functions
    ############
    # Return the string contents of the most recent message from the user
    def extract_user_query_string(chat_messages_array):
        return chat_messages_array[-1]["content"]

    # Extract system prompt from the messages

    def extract_system_prompt_string(chat_messages_array):
        return chat_messages_array[0]["content"]

    # Return the chat history, which is everything before the last question
    def extract_chat_history(chat_messages_array):
        return chat_messages_array[1:-1]

    ############
    # Prompt Template for generation
    ############
    prompt = ChatPromptTemplate.from_messages(
        [
            (  # System prompt contains the instructions
                "system",
                "{system}",
            ),
            # If there is history, provide it.
            # Note: This chain does not compress the history, so very long converastions can overflow the context window.
            MessagesPlaceholder(variable_name="formatted_chat_history"),
            # User's most current question
            ("user", "{question}"),
        ]
    )
    is_question_about_sql_str = """
    You are classifying Questions to know if this question is related to Databricks and SQL in general

    Question: Convert to Spark SQL SELECT * from table 1?
    Expected Response: Yes

    Question: Knowing this followup history: Convert to Spark SQL SELECT * from table 1?, classify this question: Summarize the query.
    Expected Response: Yes

    Only answer with "yes" or "no". 

    Knowing this followup history:"""

    is_question_relevant_prompt = ChatPromptTemplate.from_messages(
        [
            (  # System prompt contains the instructions
                "system",
                is_question_about_sql_str,
            ),
            # If there is history, provide it.
            # Note: This chain does not compress the history, so very long converastions can overflow the context window.
            MessagesPlaceholder(variable_name="formatted_chat_history"),
            # User's most current question
            ("user", "classify this question: {question}"),
        ]
    )

    # Format the converastion history to fit into the prompt template above.
    def format_chat_history_for_prompt(chat_messages_array):
        history = extract_chat_history(chat_messages_array)
        formatted_chat_history = []
        if len(history) > 0:
            for chat_message in history:
                if chat_message["role"] == "user":
                    formatted_chat_history.append(
                        HumanMessage(content=chat_message["content"])
                    )
                elif chat_message["role"] == "assistant":
                    formatted_chat_history.append(
                        AIMessage(content=chat_message["content"])
                    )
        return formatted_chat_history

    ############
    # FM for generation
    ############
    model = ChatDatabricks(endpoint=FOUNDATION_MODEL)

    ############
    # Guard Rail chain
    ############

    ############
    # RAG Chain
    ############
    is_question_about_sql_chain = (
            {
                "question": itemgetter("messages")
                            | RunnableLambda(extract_user_query_string),
                "formatted_chat_history": itemgetter("messages")
                                          | RunnableLambda(extract_chat_history),
            }
            | is_question_relevant_prompt
            | model
            | StrOutputParser()
    )

    irrelevant_question_chain = RunnableLambda(
        lambda x: {
            "id": "null",
            "object": "mock.chat.completion",
            "created": 1722193932,
            "model": "irrelevant_call",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "I cannot answer questions that are not about Databricks or Spark SQL",
                    },
                    "finish_reason": "Standard response",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    )

    chain = (
            RunnablePassthrough()
            | {
                "system": itemgetter("system"),
                "question": itemgetter("question"),
                "formatted_chat_history": itemgetter("chat_history"),
            }
            | prompt
            | model
            | StrOutputParser()
    )

    branch_node = RunnableBranch(
        (
            lambda x: "yes" in x["question_is_relevant"].lower(),
            RunnablePassthrough() | chain,
        ),
        (
            lambda x: "no" in x["question_is_relevant"].lower(),
            irrelevant_question_chain,
        ),
        irrelevant_question_chain,
    )

    full_chain = {
                     "question_is_relevant": is_question_about_sql_chain,
                     "question": itemgetter("messages") | RunnableLambda(extract_user_query_string),
                     "system": itemgetter("messages") | RunnableLambda(extract_system_prompt_string),
                     "chat_history": itemgetter("messages")
                                     | RunnableLambda(format_chat_history_for_prompt),
                 } | branch_node

    mlflow.models.set_model(model=full_chain)

    # Log the model to MLflow
    try:
        mlflow.create_experiment(experiment_name)
        mlflow.set_experiment(experiment_name)
    except:
        mlflow.set_experiment(experiment_name)
    with mlflow.start_run():
        logged_chain_info = mlflow.langchain.log_model(
            lc_model=full_chain,
            artifact_path="chain",  # Required by MLflow
            input_example={
                "messages": [
                    {
                        "role": "System",
                        "content": "You are a helpful assistant",
                    },
                    {
                        "role": "user",
                        "content": "What is RAG?",
                    },
                ]
            },
        )

    mlflow.set_registry_uri("databricks-uc")

    # Register the model
    uc_registered_model_info = mlflow.register_model(
        model_uri=logged_chain_info.model_uri, name=fully_qualified_name
    )
