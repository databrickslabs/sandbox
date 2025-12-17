"""
Message classes for the chatbot application.

This module contains the message classes used throughout the app.
By keeping them in a separate module, they remain stable across
Streamlit app reruns, avoiding isinstance comparison issues.
"""
import streamlit as st
from abc import ABC, abstractmethod


class Message(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def to_input_messages(self):
        """Convert this message into a list of dicts suitable for the model API."""
        pass

    @abstractmethod
    def render(self, idx):
        """Render the message in the Streamlit app."""
        pass


class UserMessage(Message):
    def __init__(self, content):
        super().__init__()
        self.content = content

    def to_input_messages(self):
        return [{
            "role": "user",
            "content": self.content
        }]

    def render(self, _):
        with st.chat_message("user"):
            st.markdown(self.content)


class AssistantResponse(Message):
    def __init__(self, messages, request_id):
        super().__init__()
        self.messages = messages
        # Request ID tracked to enable submitting feedback on assistant responses via the feedback endpoint
        self.request_id = request_id

    def to_input_messages(self):
        return self.messages

    def render(self, idx):
        with st.chat_message("assistant"):
            for msg in self.messages:
                render_message(msg)

            if self.request_id is not None:
                render_assistant_message_feedback(idx, self.request_id)


def render_message(msg):
    """Render a single message with enhanced formatting for ABAC content."""
    if msg["role"] == "assistant":
        # Render content first if it exists
        if msg.get("content"):
            st.markdown(msg["content"])
        
        # Then render tool calls if they exist
        if "tool_calls" in msg and msg["tool_calls"]:
            for call in msg["tool_calls"]:
                fn_name = call["function"]["name"]
                args = call["function"]["arguments"]
                
                # Databricks-themed display for function calls
                st.markdown(f"""
                <div style="background: #E3F2FD; border-left: 4px solid #FF6B35; padding: 0.75rem; margin: 0.5rem 0; border-radius: 6px; box-shadow: 0 1px 3px rgba(30, 58, 95, 0.05);">
                    <div style="color: #1E3A5F; font-weight: 500; font-size: 0.95rem;">
                        🔍 {fn_name.replace('enterprise_gov__gov_admin__', '').replace('_', ' ').title()}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Only show parameters if they're not empty
                try:
                    import json
                    parsed_args = json.loads(args)
                    if parsed_args:
                        with st.expander("View parameters", expanded=False):
                            st.json(parsed_args)
                except:
                    pass
                    
    elif msg["role"] == "tool":
        # Clean, minimal tool response display
        try:
            import json
            parsed = json.loads(msg["content"])
            
            # Show results in an expandable section for cleaner UI
            with st.expander("📊 View Results", expanded=True):
                st.json(parsed)
        except:
            # If not JSON, show as code
            with st.expander("📊 View Results", expanded=True):
                st.text(msg["content"])


@st.fragment
def render_assistant_message_feedback(i, request_id):
    """Render feedback UI for assistant messages."""
    from model_serving_utils import submit_feedback
    import os
    
    def save_feedback(index):
        serving_endpoint = os.getenv('SERVING_ENDPOINT')
        if serving_endpoint:
            submit_feedback(
                endpoint=serving_endpoint,
                request_id=request_id,
                rating=st.session_state[f"feedback_{index}"]
            )
    
    st.feedback("thumbs", key=f"feedback_{i}", on_change=save_feedback, args=[i])