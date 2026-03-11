"""
Wire protocol types for the Databricks Responses Agent protocol.

These Pydantic models replace the mlflow.types.responses types for agents
deployed as Databricks Apps. The wire format is identical:

    Request:  {"input": [{"role": "user", "content": "..."}]}
    Response: {"output": [{"type": "message", "id": "...", "content": [...]}]}
    Stream:   {"type": "response.output_text.delta", "item_id": "...", "delta": "..."}

Usage:
    from dbx_agent_app import AgentRequest, AgentResponse, StreamEvent

    def predict(request: AgentRequest) -> AgentResponse:
        return AgentResponse.text("Hello!")
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, PrivateAttr


# ---------------------------------------------------------------------------
# User context (on-behalf-of user authorization)
# ---------------------------------------------------------------------------


class UserContext(BaseModel):
    """
    User identity from Databricks Apps on-behalf-of-user authorization.

    When user authorization scopes are configured on a Databricks App,
    the platform injects X-Forwarded-* headers with the calling user's
    identity. The @app_agent decorator extracts these into a UserContext.

    Usage:
        @app_agent(name="research", ...)
        async def research(request: AgentRequest) -> AgentResponse:
            if request.user_context and request.user_context.is_authenticated:
                ws = request.user_context.get_workspace_client()
                # UC queries execute as the user — row-level security applies
    """

    access_token: Optional[str] = Field(default=None, repr=False)
    email: Optional[str] = None
    user: Optional[str] = None

    @property
    def is_authenticated(self) -> bool:
        """True when a user access token is available."""
        return self.access_token is not None

    def get_workspace_client(self, host: Optional[str] = None):
        """
        Create a WorkspaceClient that executes as this user.

        Args:
            host: Databricks workspace URL. Defaults to DATABRICKS_HOST env var.

        Returns:
            WorkspaceClient authenticated with the user's token.

        Raises:
            ValueError: If no access token is available.
        """
        if not self.access_token:
            raise ValueError("No user access token available. Configure user authorization scopes on the Databricks App.")

        from databricks.sdk import WorkspaceClient
        from databricks.sdk.config import Config

        # Force PAT auth and explicitly null out client_id/client_secret
        # to prevent the SDK from picking up service principal env vars
        # (DATABRICKS_CLIENT_ID/SECRET) which would cause a "multiple auth
        # methods" error. Pattern from databricks-genie-workbench.
        cfg = Config(
            host=host or os.environ.get("DATABRICKS_HOST"),
            token=self.access_token,
            auth_type="pat",
            client_id=None,
            client_secret=None,
        )
        return WorkspaceClient(config=cfg)

    # Trusted URL patterns for forwarding user tokens.
    # Only forward access tokens to Databricks-hosted endpoints.
    TRUSTED_DOMAINS = (
        ".cloud.databricks.com",
        ".azuredatabricks.net",
        ".databricks.azure.us",
        ".databricks.azure.cn",
        ".gcp.databricks.com",
    )

    def as_forwarded_headers(self, target_url: str | None = None) -> Dict[str, str]:
        """
        Build X-Forwarded-* headers for forwarding user identity to downstream agents.

        Args:
            target_url: The URL tokens will be sent to. If provided and the domain
                is not a trusted Databricks domain, the access token is omitted
                to prevent token exfiltration via spoofed agent URLs.

        Returns:
            Dict of headers to include in agent-to-agent HTTP calls.
        """
        headers = {}

        # Only forward access token to trusted Databricks domains
        send_token = True
        if target_url and self.access_token:
            from urllib.parse import urlparse
            hostname = urlparse(target_url).hostname or ""
            send_token = any(hostname.endswith(d) for d in self.TRUSTED_DOMAINS)

        if self.access_token and send_token:
            headers["X-Forwarded-Access-Token"] = self.access_token
        if self.email:
            headers["X-Forwarded-Email"] = self.email
        if self.user:
            headers["X-Forwarded-User"] = self.user
        return headers


# ---------------------------------------------------------------------------
# Request types
# ---------------------------------------------------------------------------


class InputItem(BaseModel):
    """A single input message in the Responses Agent protocol."""

    role: str
    content: str


class AgentRequest(BaseModel):
    """
    Incoming request to an agent via /invocations.

    Wire format: {"input": [{"role": "user", "content": "..."}]}
    """

    input: List[InputItem]
    _user_context: Optional[UserContext] = PrivateAttr(default=None)

    @property
    def user_context(self) -> Optional[UserContext]:
        """User identity from on-behalf-of authorization, or None."""
        return self._user_context

    @property
    def messages(self) -> List[InputItem]:
        """All input messages (alias for input)."""
        return self.input

    @property
    def last_user_message(self) -> str:
        """Extract the last user message content, or empty string."""
        for item in reversed(self.input):
            if item.role == "user":
                return item.content
        return ""


# ---------------------------------------------------------------------------
# Response types
# ---------------------------------------------------------------------------


class OutputTextContent(BaseModel):
    """A text content block inside an output item."""

    type: str = "output_text"
    text: str = ""


class OutputItem(BaseModel):
    """A single output item in the Responses Agent protocol."""

    type: str = "message"
    id: str = Field(default_factory=lambda: str(uuid4()))
    content: List[OutputTextContent] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """
    Outgoing response from an agent via /invocations.

    Wire format: {"output": [{"type": "message", "id": "...", "content": [...]}]}

    Use class methods for convenient construction:
        AgentResponse.text("Hello!")
        AgentResponse.from_dict({"response": "...", "metrics": {...}})
    """

    output: List[OutputItem] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def text(cls, text: str, item_id: Optional[str] = None) -> AgentResponse:
        """Create a response with a single text output item."""
        item = OutputItem(
            id=item_id or str(uuid4()),
            content=[OutputTextContent(text=text)],
        )
        return cls(output=[item])

    @classmethod
    def from_dict(cls, data: Dict[str, Any], item_id: Optional[str] = None) -> AgentResponse:
        """
        Create a response from a dict.

        If the dict has a "response" key, uses that as text.
        Otherwise serializes the whole dict as the text content.
        """
        import json

        if "response" in data:
            text = data["response"]
        else:
            text = json.dumps(data)

        return cls.text(text, item_id=item_id)

    def to_wire(self) -> Dict[str, Any]:
        """Serialize to the wire protocol dict, including _metadata when present."""
        wire = self.model_dump(exclude={"metadata"})
        if self.metadata:
            wire["_metadata"] = self.metadata
        return wire


# ---------------------------------------------------------------------------
# Streaming types
# ---------------------------------------------------------------------------


class StreamEvent(BaseModel):
    """
    A single SSE event in the streaming Responses Agent protocol.

    Event types:
        response.output_text.delta  — a text chunk
        response.output_item.done   — final item with full text

    Use class methods for convenient construction:
        StreamEvent.text_delta("chunk", item_id="...")
        StreamEvent.done("full text", item_id="...")
    """

    type: str
    item_id: Optional[str] = None
    delta: Optional[str] = None
    item: Optional[OutputItem] = None

    @classmethod
    def text_delta(cls, delta: str, item_id: Optional[str] = None) -> StreamEvent:
        """Create a text delta event."""
        return cls(
            type="response.output_text.delta",
            item_id=item_id or str(uuid4()),
            delta=delta,
        )

    @classmethod
    def done(cls, text: str, item_id: Optional[str] = None) -> StreamEvent:
        """Create a done event with the final output item."""
        _id = item_id or str(uuid4())
        item = OutputItem(
            id=_id,
            content=[OutputTextContent(text=text)],
        )
        return cls(
            type="response.output_item.done",
            item_id=_id,
            item=item,
        )

    def to_sse(self) -> str:
        """Serialize to SSE data line."""
        import json

        return f"data: {json.dumps(self.model_dump(exclude_none=True))}\n\n"
