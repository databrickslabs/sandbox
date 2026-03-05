"""
Minimal agent example — plain FastAPI + discoverability helper.

Build your agent however you want. Call add_agent_card() to make it
discoverable by the Agent Platform.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from databricks_agents import add_agent_card

app = FastAPI()


@app.post("/invocations")
async def invocations(request: Request):
    """Standard Databricks /invocations endpoint."""
    body = await request.json()
    # Extract last user message
    query = ""
    for item in reversed(body.get("input", [])):
        if isinstance(item, dict) and item.get("role") == "user":
            query = item.get("content", "")
            break

    return {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": f"Hello, {query}!"}],
            }
        ]
    }


# Make this app discoverable by the Agent Platform
add_agent_card(app, name="hello", description="A minimal greeting agent", capabilities=["greetings"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
