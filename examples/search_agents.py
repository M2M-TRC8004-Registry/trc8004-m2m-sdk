"""
Example: Search for agents

This script demonstrates how to search for agents in the registry.
"""

import asyncio
from trc8004_m2m import AgentRegistry


async def main():
    # Initialize registry (no private key needed for reading)
    registry = AgentRegistry(
        network="mainnet"
    )
    
    print("🔍 Searching for agents...\n")
    
    try:
        # Example 1: Search by skills
        print("=" * 60)
        print("Search 1: Trading agents with high reputation")
        print("=" * 60)
        
        agents = await registry.search_agents(
            skills=["trading"],
            min_reputation=80,
            verified_only=True,
            limit=5
        )
        
        print(f"Found {len(agents)} agents:\n")
        for agent in agents:
            print(f"📊 {agent.name}")
            print(f"   ID: {agent.agent_id}")
            print(f"   Owner: {agent.owner_address}")
            print(f"   Reputation: {agent.avg_reputation_score:.1f}/100")
            print(f"   Validations: {agent.total_validations}")
            print(f"   Skills: {', '.join([s.skill_name for s in agent.skills])}")
            print(f"   Tags: {', '.join(agent.tags)}")
            print()
        
        # Example 2: Full-text search
        print("\n" + "=" * 60)
        print("Search 2: Full-text search for 'AI trading bot'")
        print("=" * 60)
        
        agents = await registry.search_agents(
            query="AI trading bot",
            limit=3
        )
        
        print(f"Found {len(agents)} agents:\n")
        for agent in agents:
            print(f"🤖 {agent.name}")
            print(f"   {agent.description[:100]}...")
            print(f"   Reputation: {agent.avg_reputation_score:.1f}/100")
            print()
        
        # Example 3: Get specific agent
        if agents:
            print("\n" + "=" * 60)
            print(f"Details for: {agents[0].name}")
            print("=" * 60)
            
            agent = await registry.get_agent(agents[0].agent_id)
            
            print(f"\n📋 Basic Info:")
            print(f"   Name: {agent.name}")
            print(f"   Version: {agent.version}")
            print(f"   Verified: {agent.verified}")
            print(f"   Active: {agent.active}")
            
            print(f"\n🎯 Skills:")
            for skill in agent.skills:
                print(f"   - {skill.skill_name}: {skill.description}")
            
            print(f"\n🔌 Endpoints:")
            for endpoint in agent.endpoints:
                print(f"   - {endpoint.endpoint_type}: {endpoint.url}")
            
            print(f"\n📊 Statistics:")
            print(f"   Average Reputation: {agent.avg_reputation_score:.1f}/100")
            print(f"   Total Validations: {agent.total_validations}")
            print(f"   Total Feedback: {agent.total_feedback}")
            print(f"   Registered: {agent.registered_at}")
        
        # Example 4: Get global stats
        print("\n" + "=" * 60)
        print("Global Registry Statistics")
        print("=" * 60)
        
        stats = await registry.get_stats()
        print(f"\n   Total Agents: {stats.get('total_agents', 'N/A')}")
        print(f"   Total Validations: {stats.get('total_validations', 'N/A')}")
        print(f"   Total Feedback: {stats.get('total_feedback', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
    finally:
        await registry.close()


if __name__ == "__main__":
    asyncio.run(main())
