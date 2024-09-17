import gradio as gr

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

class LLMCalls:
    def __init__(self, foundation_llm_name):
        self.w = WorkspaceClient()
        self.foundation_llm_name = foundation_llm_name

    def call_llm(self, messages, max_tokens, temperature):
        """
        Function to call the LLM model and return the response.
        :param messages: list of messages like
            messages=[
                       ChatMessage(role=ChatMessageRole.SYSTEM, content="You are an unhelpful assistant"),
                        ChatMessage(role=ChatMessageRole.USER, content="What is RAG?"),
                        ChatMessage(role=ChatMessageRole.ASSISTANT, content="A type of cloth?")
                    ]
        :return: the response from the model
        """

        max_tokens = int(max_tokens)
        temperature = float(temperature)
        # check to make sure temperature is between 0.0 and 2.0
        if temperature < 0.0 or temperature > 2.0:
            raise gr.Error("Temperature must be between 0.0 and 2.0")
        response = self.w.serving_endpoints.query(
            name=self.foundation_llm_name, max_tokens=max_tokens, messages=messages, temperature=temperature
        )
        message = response.choices[0].message.content
        return message

    def convert_chat_to_llm_input(self, system_prompt, chat):
        # Convert the chat list of lists to the required format for the LLM
        messages = [ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt)]
        for q, a in chat:
            messages.extend(
                [
                    ChatMessage(role=ChatMessageRole.USER, content=q),
                    ChatMessage(role=ChatMessageRole.ASSISTANT, content=a),
                ]
            )
        return messages

    ################################################################################
    # FUNCTION FOR TRANSLATING CODE
    ################################################################################

    # this is called to actually send a request and receive response from the llm endpoint.

    def llm_translate(self, system_prompt, input_code, max_tokens, temperature):
        messages = [
            ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=ChatMessageRole.USER, content=input_code),
        ]

        # call the LLM end point.
        llm_answer = self.call_llm(messages=messages, max_tokens=max_tokens, temperature=temperature)
        # Extract the code from in between the triple backticks (```), since LLM often prints the code like this.
        # Also removes the 'sql' prefix always added by the LLM.
        translation = llm_answer  # .split("Final answer:\n")[1].replace(">>", "").replace("<<", "")
        return translation

    def llm_chat(self, system_prompt, query, chat_history):
        messages = self.convert_chat_to_llm_input(system_prompt, chat_history)
        messages.append(ChatMessage(role=ChatMessageRole.USER, content=query))
        # call the LLM end point.
        llm_answer = self.call_llm(messages=messages)
        return llm_answer

    def llm_intent(self, system_prompt, input_code, max_tokens, temperature):
        messages = [
            ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt),
            ChatMessage(role=ChatMessageRole.USER, content=input_code),
        ]

        # call the LLM end point.
        llm_answer = self.call_llm(messages=messages, max_tokens=max_tokens, temperature=temperature)
        return llm_answer
