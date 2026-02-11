"""
Example: Validation Workflow

This script demonstrates the complete validation workflow:
1. Agent submits execution request for validation
2. Validator fetches request data from URI
3. Validator responds with score
"""

import asyncio
import json
from trc8004_m2m import AgentRegistry
from trc8004_m2m.utils import load_request_data, compute_metadata_hash


async def agent_submit_validation():
    """Agent submits validation request"""
    registry = AgentRegistry(
        private_key="agent_private_key",
        network="shasta"
    )
    
    print("🤖 Agent: Preparing validation request...")
    
    # Build execution request data
    request_data = {
        "skill": "market_order",
        "params": {
            "asset": "TRX/USDT",
            "amount": 100,
            "price": 0.15,
        },
        "result": {
            "order_id": "ord_123456",
            "executed_amount": 100,
            "executed_price": 0.1499,
            "slippage": 0.0007,
            "timestamp": 1707567890,
        },
        "metadata": {
            "execution_time_ms": 234,
            "gas_used": 50000,
        }
    }
    
    # Upload request to IPFS
    request_uri = await registry.api.upload_to_ipfs(request_data)
    print(f"📤 Request uploaded: {request_uri}")
    
    # Compute request hash
    request_hash = compute_metadata_hash(request_data)
    print(f"🔐 Request hash: {request_hash}")
    
    # Submit validation request on-chain
    validator_address = "TValidatorAddress123..."
    agent_id = 42
    
    tx_id = await registry.submit_validation(
        validator_address=validator_address,
        agent_id=agent_id,
        request_uri=request_uri,
        request_hash=request_hash,
    )
    
    print(f"✅ Validation request submitted: {tx_id}")
    print(f"   Validator: {validator_address}")
    print(f"   Agent ID: {agent_id}")
    
    await registry.close()
    return request_hash, request_uri


async def validator_process_request(request_hash: str, request_uri: str):
    """Validator fetches and validates request"""
    registry = AgentRegistry(
        private_key="validator_private_key",
        network="shasta"
    )
    
    print("\n🔍 Validator: Processing validation request...")
    print(f"   Request hash: {request_hash[:18]}...")
    
    # Fetch request data from URI
    print(f"📥 Fetching data from: {request_uri}")
    request_json = await load_request_data(request_uri)
    request_data = json.loads(request_json)
    
    print("✅ Request data fetched:")
    print(f"   Skill: {request_data['skill']}")
    print(f"   Asset: {request_data['params']['asset']}")
    print(f"   Result: {request_data['result']['order_id']}")
    
    # Verify request hash
    computed_hash = compute_metadata_hash(request_data)
    if computed_hash != request_hash:
        print("❌ Hash mismatch! Request may be tampered.")
        return
    
    print("✅ Hash verified - request is authentic")
    
    # Validate execution quality
    result = request_data["result"]
    slippage = result["slippage"]
    execution_time = request_data["metadata"]["execution_time_ms"]
    
    # Score based on performance
    score = 100
    
    if slippage > 0.01:  # >1% slippage
        score -= 20
        print("   ⚠️  High slippage detected")
    
    if execution_time > 1000:  # >1 second
        score -= 10
        print("   ⚠️  Slow execution")
    
    print(f"\n📊 Validation score: {score}/100")
    
    # Build response data
    response_data = {
        "request_hash": request_hash,
        "score": score,
        "analysis": {
            "slippage": slippage,
            "execution_time_ms": execution_time,
            "verified_at": 1707567950,
        },
        "recommendation": "approved" if score >= 80 else "review_needed"
    }
    
    # Upload response to IPFS
    response_uri = await registry.api.upload_to_ipfs(response_data)
    print(f"📤 Response uploaded: {response_uri}")
    
    # Submit validation response on-chain
    tx_id = await registry.respond_to_validation(
        request_hash=request_hash,
        response_score=score,
        response_uri=response_uri,
        tag="market_order_validation"
    )
    
    print(f"✅ Validation response submitted: {tx_id}")
    
    await registry.close()


async def query_validation_result(request_hash: str):
    """Query final validation result"""
    registry = AgentRegistry(network="shasta")
    
    print("\n📋 Querying validation result...")
    
    # Get validation status from blockchain
    validation = await registry.get_validation_status(request_hash)
    
    print(f"✅ Validation complete:")
    print(f"   Request: {request_hash[:18]}...")
    print(f"   Validator: {validation.validator_address}")
    print(f"   Score: {validation.response}/100")
    print(f"   Tag: {validation.tag}")
    print(f"   Timestamp: {validation.timestamp}")
    
    # Fetch detailed response from URI
    if validation.response_uri:
        response_json = await load_request_data(validation.response_uri)
        response_data = json.loads(response_json)
        
        print("\n📊 Detailed analysis:")
        print(f"   Slippage: {response_data['analysis']['slippage']}")
        print(f"   Execution time: {response_data['analysis']['execution_time_ms']}ms")
        print(f"   Recommendation: {response_data['recommendation']}")
    
    await registry.close()


async def main():
    """Run complete validation workflow"""
    print("=" * 60)
    print("VALIDATION WORKFLOW EXAMPLE")
    print("=" * 60)
    
    # Step 1: Agent submits request
    request_hash, request_uri = await agent_submit_validation()
    
    # Step 2: Validator processes request
    await asyncio.sleep(2)  # Simulate blockchain confirmation time
    await validator_process_request(request_hash, request_uri)
    
    # Step 3: Query final result
    await asyncio.sleep(2)
    await query_validation_result(request_hash)
    
    print("\n" + "=" * 60)
    print("✅ WORKFLOW COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
