import gradio as gr


class LLMCalls:
    def __init__(self, openai_client, foundation_llm_name):
        self.o = openai_client
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
        # check to make sure temperature is between 0.0 and 1.0
        if temperature < 0.0 or temperature > 1.0:
            raise gr.Error("Temperature must be between 0.0 and 1.0")
        response = self.o.chat.completions.create(
            model=self.foundation_llm_name,
            max_tokens=max_tokens,
            messages=messages,
            temperature=temperature,
        )
        message = response.choices[0].message.content
        return message

    ################################################################################
    # FUNCTION FOR TRANSLATING CODE
    ################################################################################

    # this is called to actually send a request and receive response from the llm endpoint.

    def llm_translate(self, system_prompt, input_code, max_tokens, temperature):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_code},
        ]

        # call the LLM end point.
        llm_answer = self.call_llm(
            messages=messages, max_tokens=max_tokens, temperature=temperature
        )

        translation = llm_answer
        return translation

    def llm_intent(self, system_prompt, input_code, max_tokens, temperature):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_code},
        ]

        # call the LLM end point.
        llm_answer = self.call_llm(
            messages=messages, max_tokens=max_tokens, temperature=temperature
        )
        return llm_answer
