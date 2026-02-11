"""
TRC-8004-M2M Agent Registry SDK

Main entry point for the SDK. Provides unified interface to:
- TRON blockchain contracts (write operations)
- REST API backend (fast read operations)
- IPFS storage (metadata)

Contract alignment:
- EnhancedIdentityRegistry: register, exists, ownerOf, tokenURI, setAgentWallet
- ValidationRegistry: validationRequest, completeValidation, rejectValidation, cancelRequest
- ReputationRegistry: giveFeedback (sentiment-based), revokeFeedback, appendResponse
"""

import logging
from typing import List, Optional, Dict, Any

from .blockchain.tron_client import TronClient
from .api.client import RegistryAPI
from .storage.ipfs import IPFSStorage
from .models.agent import Agent, Validation, Feedback
from .utils.crypto import canonical_json, keccak256_bytes, compute_metadata_hash
from .utils.chain_utils import parse_agent_registered_event
from .exceptions import RegistryError, ConfigurationError

logger = logging.getLogger("trc8004_m2m")


class AgentRegistry:
    """
    Unified interface to TRON Agent Registry.

    Handles both on-chain (contracts) and off-chain (API) operations.

    Usage:
        registry = AgentRegistry(
            private_key="your_key",
            network="shasta",
            api_url="http://localhost:8000",
        )

        # Register an agent (on-chain)
        agent_id = await registry.register_agent(
            name="MyAgent",
            description="AI trading agent",
            skills=[...],
            endpoints=[...],
        )

        # Search agents (fast API query)
        agents = await registry.search_agents(query="trading")
    """

    def __init__(
        self,
        private_key: Optional[str] = None,
        network: str = "mainnet",
        api_url: Optional[str] = None,
        identity_address: Optional[str] = None,
        validation_address: Optional[str] = None,
        reputation_address: Optional[str] = None,
    ):
        """
        Initialize the Agent Registry SDK.

        Args:
            private_key: TRON private key for write operations (optional for read-only)
            network: TRON network ("mainnet", "shasta", "nile")
            api_url: Backend API URL for fast queries
            identity_address: EnhancedIdentityRegistry contract address
            validation_address: ValidationRegistry contract address
            reputation_address: ReputationRegistry contract address
        """
        self.chain = TronClient(
            private_key=private_key,
            network=network,
            identity_address=identity_address,
            validation_address=validation_address,
            reputation_address=reputation_address,
        )

        api_base = api_url or self._default_api_url(network)
        self.api = RegistryAPI(api_base)
        self.storage = IPFSStorage()

        logger.info(f"AgentRegistry initialized: network={network}, api={api_base}")

    async def close(self):
        """Close all connections."""
        await self.api.close()
        await self.storage.close()

    # ==========================================================================
    # WRITE OPERATIONS (Blockchain)
    # ==========================================================================

    async def register_agent(
        self,
        name: str,
        description: str,
        skills: Optional[List[dict]] = None,
        endpoints: Optional[List[dict]] = None,
        tags: Optional[List[str]] = None,
        version: str = "1.0.0",
        **kwargs,
    ) -> int:
        """
        Register a new agent on-chain.

        1. Builds metadata JSON
        2. Uploads to IPFS via API
        3. Computes metadata hash (keccak256)
        4. Calls IdentityRegistry.register(uri, metadataHash)
        5. Parses agent_id from transaction events

        Args:
            name: Agent name
            description: Agent description
            skills: List of skill dicts
            endpoints: List of endpoint dicts
            tags: Search tags
            version: Agent version

        Returns:
            agent_id (on-chain NFT token ID)
        """
        # Build metadata
        metadata = {
            "name": name,
            "description": description,
            "version": version,
            "skills": skills or [],
            "endpoints": endpoints or [],
            "tags": tags or [],
            **kwargs,
        }

        # Upload to IPFS
        token_uri = await self.api.upload_to_ipfs(metadata)

        # Compute metadata hash
        metadata_hash = keccak256_bytes(canonical_json(metadata))

        # Register on-chain
        tx_id = await self.chain.register_agent(token_uri, metadata_hash)

        # Parse agent_id from events
        # Note: May need to wait for confirmation
        logger.info(f"Agent registration tx: {tx_id}")

        # Trigger API sync
        try:
            await self.api.sync_agent(tx_id)
        except Exception:
            pass  # Non-critical

        return tx_id

    async def set_agent_wallet(self, agent_id: int, wallet: str) -> str:
        """
        Set delegated wallet for an agent.

        Calls IdentityRegistry.setAgentWallet(agentId, wallet).
        Only callable by agent owner.

        Args:
            agent_id: Agent token ID
            wallet: Delegated wallet address

        Returns:
            Transaction ID
        """
        return await self.chain.set_agent_wallet(agent_id, wallet)

    async def submit_validation(
        self,
        agent_id: int,
        validator_address: str,
        request_uri: str,
        request_data: Optional[dict] = None,
    ) -> str:
        """
        Submit a validation request for an agent.

        Calls ValidationRegistry.validationRequest(agentId, validator, requestURI, requestDataHash).

        Args:
            agent_id: Agent to validate
            validator_address: Validator's TRON address
            request_uri: URI pointing to request details
            request_data: Optional data to hash for integrity check

        Returns:
            Transaction ID
        """
        if request_data:
            data_hash = keccak256_bytes(canonical_json(request_data))
        else:
            data_hash = b"\x00" * 32  # Zero hash = auto-compute in contract

        return await self.chain.validation_request(
            agent_id=agent_id,
            validator=validator_address,
            request_uri=request_uri,
            request_data_hash=data_hash,
        )

    async def complete_validation(
        self,
        request_id: str,
        result_uri: str,
        result_data: Optional[dict] = None,
    ) -> str:
        """
        Complete a validation request (validators only).

        Calls ValidationRegistry.completeValidation(requestId, resultURI, resultHash).

        Args:
            request_id: Validation request ID (hex string)
            result_uri: URI pointing to result data
            result_data: Optional data to hash for integrity check

        Returns:
            Transaction ID
        """
        request_id_bytes = bytes.fromhex(request_id.replace("0x", ""))

        if result_data:
            result_hash = keccak256_bytes(canonical_json(result_data))
        else:
            result_hash = b"\x00" * 32

        return await self.chain.complete_validation(
            request_id=request_id_bytes,
            result_uri=result_uri,
            result_hash=result_hash,
        )

    async def reject_validation(
        self,
        request_id: str,
        result_uri: str = "",
        reason_data: Optional[dict] = None,
    ) -> str:
        """
        Reject a validation request (validators only).

        Calls ValidationRegistry.rejectValidation(requestId, resultURI, reasonHash).

        Args:
            request_id: Validation request ID (hex string)
            result_uri: URI pointing to rejection reason
            reason_data: Optional data to hash

        Returns:
            Transaction ID
        """
        request_id_bytes = bytes.fromhex(request_id.replace("0x", ""))

        if reason_data:
            reason_hash = keccak256_bytes(canonical_json(reason_data))
        else:
            reason_hash = b"\x00" * 32

        return await self.chain.reject_validation(
            request_id=request_id_bytes,
            result_uri=result_uri,
            reason_hash=reason_hash,
        )

    async def cancel_validation(self, request_id: str) -> str:
        """
        Cancel a validation request (requesters only).

        Calls ValidationRegistry.cancelRequest(requestId).

        Args:
            request_id: Validation request ID (hex string)

        Returns:
            Transaction ID
        """
        request_id_bytes = bytes.fromhex(request_id.replace("0x", ""))
        return await self.chain.cancel_validation(request_id_bytes)

    async def give_feedback(
        self,
        agent_id: int,
        feedback_text: str,
        sentiment: str,
    ) -> str:
        """
        Submit reputation feedback for an agent.

        Calls ReputationRegistry.giveFeedback(agentId, feedbackText, sentiment).

        Args:
            agent_id: Agent token ID
            feedback_text: Feedback text (stored on-chain)
            sentiment: "positive", "neutral", or "negative"

        Returns:
            Transaction ID
        """
        return await self.chain.give_feedback(
            agent_id=agent_id,
            feedback_text=feedback_text,
            sentiment=sentiment,
        )

    async def revoke_feedback(self, agent_id: int, feedback_index: int) -> str:
        """
        Revoke previously submitted feedback.

        Calls ReputationRegistry.revokeFeedback(agentId, feedbackIndex).
        Only callable by original feedback author.

        Args:
            agent_id: Agent token ID
            feedback_index: Feedback index to revoke

        Returns:
            Transaction ID
        """
        return await self.chain.revoke_feedback(agent_id, feedback_index)

    async def respond_to_feedback(
        self,
        agent_id: int,
        feedback_index: int,
        response_text: str,
    ) -> str:
        """
        Respond to feedback as agent owner.

        Calls ReputationRegistry.appendResponse(agentId, feedbackIndex, responseText).
        Only callable by agent owner or delegated wallet.

        Args:
            agent_id: Agent token ID
            feedback_index: Feedback index to respond to
            response_text: Response text (stored on-chain)

        Returns:
            Transaction ID
        """
        return await self.chain.append_response(
            agent_id=agent_id,
            feedback_index=feedback_index,
            response_text=response_text,
        )

    # ==========================================================================
    # READ OPERATIONS (API - Fast)
    # ==========================================================================

    async def get_agent(self, agent_id: int) -> Agent:
        """Get agent by ID (from API cache)."""
        return await self.api.get_agent(agent_id)

    async def search_agents(
        self,
        query: Optional[str] = None,
        skills: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        min_feedback_positive: Optional[int] = None,
        verified_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Agent]:
        """Search agents with filters (fast API query)."""
        return await self.api.search_agents(
            query=query,
            skills=skills,
            tags=tags,
            min_feedback_positive=min_feedback_positive,
            verified_only=verified_only,
            limit=limit,
            offset=offset,
        )

    async def get_agent_reputation(self, agent_id: int) -> dict:
        """Get detailed reputation stats (sentiment breakdown)."""
        return await self.api.get_reputation(agent_id)

    async def get_agent_validations(self, agent_id: int) -> List[dict]:
        """Get validation history."""
        return await self.api.get_validations(agent_id)

    async def get_stats(self) -> dict:
        """Get global registry statistics."""
        return await self.api.get_stats()

    # ==========================================================================
    # VERIFICATION (Blockchain - Trustless)
    # ==========================================================================

    async def verify_ownership(self, agent_id: int) -> str:
        """Verify agent ownership on-chain. Returns owner address."""
        return await self.chain.get_agent_owner(agent_id)

    async def verify_agent_exists(self, agent_id: int) -> bool:
        """Check if agent exists on-chain."""
        return await self.chain.agent_exists(agent_id)

    # ==========================================================================
    # Private helpers
    # ==========================================================================

    @staticmethod
    def _default_api_url(network: str) -> str:
        """Get default API URL for network."""
        urls = {
            "mainnet": "https://registry-api.trc8004.io",
            "shasta": "http://localhost:8000",
            "nile": "http://localhost:8000",
        }
        return urls.get(network, "http://localhost:8000")
