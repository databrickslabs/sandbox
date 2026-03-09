"""
Example: Discover Agents

Demonstrates how to discover agent-enabled Databricks Apps in a workspace.
"""

import asyncio
from dbx_agent_app.discovery import AgentDiscovery


async def main():
    # Initialize discovery with your Databricks profile
    discovery = AgentDiscovery(profile="my-profile")
    
    # Discover all agent-enabled apps
    result = await discovery.discover_agents()
    
    print(f"Found {len(result.agents)} agents:\n")
    
    for agent in result.agents:
        print(f"Agent: {agent.name}")
        print(f"  URL: {agent.endpoint_url}")
        print(f"  App: {agent.app_name}")
        if agent.description:
            print(f"  Description: {agent.description}")
        if agent.capabilities:
            print(f"  Capabilities: {agent.capabilities}")
        if agent.protocol_version:
            print(f"  Protocol: {agent.protocol_version}")
        print()
    
    if result.errors:
        print(f"Encountered {len(result.errors)} errors:")
        for error in result.errors:
            print(f"  - {error}")


if __name__ == "__main__":
    asyncio.run(main())
