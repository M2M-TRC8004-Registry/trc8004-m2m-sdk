"""
Example: Agent-to-Agent (A2A) Communication

This script demonstrates how to use the Agent Protocol client
to communicate with another agent.
"""

import asyncio
from trc8004_m2m import AgentProtocolClient


async def main():
    # Get an agent from the registry first
    from trc8004_m2m import AgentRegistry
    
    registry = AgentRegistry(network="mainnet")
    
    print("🔍 Searching for trading agents...")
    agents = await registry.search_agents(
        skills=["trading"],
        min_reputation=80,
        limit=1
    )
    
    if not agents:
        print("❌ No trading agents found")
        return
    
    agent = agents[0]
    print(f"✅ Found agent: {agent.name}")
    print(f"   Reputation: {agent.avg_reputation_score}/100")
    
    # Get agent's API endpoint
    if not agent.endpoints:
        print("❌ Agent has no endpoints configured")
        return
    
    endpoint = agent.endpoints[0]
    print(f"\n🔌 Connecting to: {endpoint.url}")
    
    # Create Agent Protocol client
    client = AgentProtocolClient(base_url=endpoint.url)
    
    try:
        # Example 1: Get market quote
        print("\n📊 Requesting market analysis...")
        
        result = await client.run({
            "skill": "market_analysis",
            "params": {
                "asset": "BTC/USDT",
                "timeframe": "1h"
            }
        })
        
        print("✅ Analysis received:")
        print(f"   Output: {result.get('output')}")
        
        # Example 2: Multi-step task
        print("\n🔄 Creating multi-step trading task...")
        
        # Step 1: Create task
        task = await client.create_task(input_text="Initialize trading session")
        task_id = task["task_id"]
        print(f"   Task created: {task_id}")
        
        # Step 2: Get quote
        step1 = await client.execute_step(
            task_id,
            '{"action": "quote", "asset": "ETH/USDT", "amount": 1.0}'
        )
        print(f"   Quote: {step1.get('output')}")
        
        # Step 3: Execute trade (if quote acceptable)
        step2 = await client.execute_step(
            task_id,
            '{"action": "execute", "confirm": true}'
        )
        print(f"   Execution: {step2.get('output')}")
        
        print("\n✅ A2A communication successful!")
        
    except Exception as e:
        print(f"❌ Communication failed: {e}")
    finally:
        await client.close()
        await registry.close()


if __name__ == "__main__":
    asyncio.run(main())
