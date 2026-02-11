"""
Example: Register an agent

This script demonstrates how to register a new agent on the TRC-8004 registry.
"""

import asyncio
from trc8004_m2m import AgentRegistry


async def main():
    # Initialize registry with private key
    registry = AgentRegistry(
        private_key="YOUR_PRIVATE_KEY_HERE",  # Replace with your key
        network="shasta",  # Use testnet for testing
    )
    
    print("🤖 Registering new agent...")
    
    try:
        # Register agent
        agent_id = await registry.register_agent(
            name="TradingBot Pro",
            description="Advanced AI trading agent for cryptocurrency markets",
            skills=[
                {
                    "skill_id": "market_analysis",
                    "skill_name": "Market Analysis",
                    "description": "Technical and fundamental analysis of crypto assets",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "asset": {"type": "string", "description": "Trading pair (e.g., BTC/USDT)"},
                            "timeframe": {"type": "string", "enum": ["1m", "5m", "1h", "1d"]}
                        },
                        "required": ["asset", "timeframe"]
                    }
                },
                {
                    "skill_id": "trading",
                    "skill_name": "Automated Trading",
                    "description": "Execute trades on decentralized exchanges",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["buy", "sell"]},
                            "asset": {"type": "string"},
                            "amount": {"type": "number"}
                        }
                    }
                }
            ],
            endpoints=[
                {
                    "endpoint_type": "rest_api",
                    "url": "https://api.tradingbot.pro/v1",
                    "name": "Trading API",
                    "version": "1.0.0"
                },
                {
                    "endpoint_type": "websocket",
                    "url": "wss://api.tradingbot.pro/stream",
                    "name": "Live Stream",
                    "version": "1.0.0"
                }
            ],
            tags=["trading", "defi", "analytics", "ai"],
            version="2.1.0"
        )
        
        print(f"✅ Agent registered successfully!")
        print(f"   Agent ID: {agent_id}")
        print(f"   Network: shasta")
        
    except Exception as e:
        print(f"❌ Registration failed: {e}")
    finally:
        await registry.close()


if __name__ == "__main__":
    asyncio.run(main())
