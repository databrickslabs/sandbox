"""
Example: Communicate with an Agent

Demonstrates how to use the A2A client to communicate with a discovered agent.
"""

import asyncio
from databricks_agents.discovery import AgentDiscovery, A2AClient


async def main():
    # First, discover agents in the workspace
    print("Discovering agents...")
    discovery = AgentDiscovery(profile="my-profile")
    result = await discovery.discover_agents()
    
    if not result.agents:
        print("No agents found in workspace")
        return
    
    # Pick the first agent
    agent = result.agents[0]
    print(f"\nCommunicating with: {agent.name}")
    print(f"URL: {agent.endpoint_url}")
    print(f"Capabilities: {agent.capabilities}\n")
    
    # Fetch the agent's card to see available tools
    async with A2AClient() as client:
        print("Fetching agent card...")
        card = await client.fetch_agent_card(agent.endpoint_url)
        
        print(f"\nAgent: {card.get('name')}")
        print(f"Description: {card.get('description')}")
        print(f"Tools available: {len(card.get('tools', []))}")
        
        for tool in card.get('tools', []):
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Send a message to the agent
        print("\nSending message to agent...")
        a2a_endpoint = agent.endpoint_url + "/api/a2a"
        
        try:
            response = await client.send_message(
                a2a_endpoint,
                "What are your capabilities?"
            )
            print(f"\nAgent response: {response}")
        except Exception as e:
            print(f"\nFailed to send message: {e}")
            print("(This is expected if the agent doesn't implement message/send)")


if __name__ == "__main__":
    asyncio.run(main())
