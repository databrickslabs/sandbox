# Tool Registration

For agents built with the `@app_agent` decorator, tools and functionality are defined within the agent function itself. The agent receives requests and returns responses directly.

For agents using plain FastAPI with helpers, you can define tools in your agent function or as separate endpoints.

## Basic usage with @app_agent

```python
from dbx_agent_app import app_agent, AgentRequest, AgentResponse

@app_agent(
    name="my_agent",
    description="My agent with search capability",
    capabilities=["search"],
)
async def my_agent(request: AgentRequest) -> AgentResponse:
    user_message = request.last_user_message
    # Implement your search logic here
    return AgentResponse.text(f"Searching for: {user_message}")
```

The agent function receives an `AgentRequest` and returns an `AgentResponse`.

## Supported return types

The agent function can return:

```python
# Direct response text
return AgentResponse.text("Hello!")

# Response from dict
return AgentResponse.from_dict({"message": "Hello"})

# Streaming response (if needed)
return AgentResponse.streaming(...)
```

## Accessing request information

The `AgentRequest` object provides access to:

```python
@app_agent(name="my_agent", description="...", capabilities=[])
async def my_agent(request: AgentRequest) -> AgentResponse:
    # Get the last user message
    last_message = request.last_user_message

    # Get all messages
    messages = request.messages  # List[InputItem]

    # Each message has role and content
    for item in messages:
        print(f"{item.role}: {item.content}")

    return AgentResponse.text(f"Processing: {last_message}")
```

## Plain FastAPI with add_agent_card()

For agents that need full control over their FastAPI app:

```python
from fastapi import FastAPI
from dbx_agent_app import add_agent_card, AgentRequest, AgentResponse

app = FastAPI()

@app.post("/invocations")
async def invocations(request: AgentRequest) -> AgentResponse:
    return AgentResponse.text(f"You said: {request.last_user_message}")

# Add the agent card endpoint
add_agent_card(
    app,
    name="my_agent",
    description="My agent",
    capabilities=["search"],
)
```

This gives you `/invocations`, `/.well-known/agent.json`, `/health`, and other standard endpoints without the decorator.
