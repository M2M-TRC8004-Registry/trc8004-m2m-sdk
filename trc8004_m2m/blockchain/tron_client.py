"""
TRC-8004-M2M TRON Blockchain Client

Handles all smart contract interactions on TRON.
Function signatures match the deployed contracts exactly.

Contract interfaces:
- EnhancedIdentityRegistry: register, exists, ownerOf, tokenURI, setAgentWallet, totalAgents
- ValidationRegistry: validationRequest, completeValidation, rejectValidation, cancelRequest, getRequest
- ReputationRegistry: giveFeedback, revokeFeedback, appendResponse, getFeedback, getSummary
"""

import logging
from typing import Optional, Dict, Any, List

from tronpy import Tron
from tronpy.providers import HTTPProvider

from ..exceptions import ContractError, ConfigurationError, NetworkError
from ..utils.retry import retry_async

logger = logging.getLogger("trc8004_m2m.blockchain")

# Network RPC endpoints
NETWORK_URLS = {
    "mainnet": "https://api.trongrid.io",
    "shasta": "https://api.shasta.trongrid.io",
    "nile": "https://nile.trongrid.io",
}

# Sentiment enum: Neutral(0), Positive(1), Negative(2)
SENTIMENT_TO_INT = {"neutral": 0, "positive": 1, "negative": 2}
INT_TO_SENTIMENT = {0: "neutral", 1: "positive", 2: "negative"}


class TronClient:
    """
    TRON blockchain client for TRC-8004 contract interactions.

    All method signatures match the deployed Solidity contracts exactly.
    """

    def __init__(
        self,
        private_key: Optional[str] = None,
        network: str = "mainnet",
        identity_address: Optional[str] = None,
        validation_address: Optional[str] = None,
        reputation_address: Optional[str] = None,
    ):
        rpc_url = NETWORK_URLS.get(network)
        if not rpc_url:
            raise ConfigurationError(f"Unknown network: {network}")

        self.network = network
        self.private_key = private_key

        try:
            self.tron = Tron(provider=HTTPProvider(rpc_url))
            if private_key:
                self.tron.default_address = self.tron.get_address_from_passphrase(private_key)
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize TRON client: {e}")

        self.identity_address = identity_address
        self.validation_address = validation_address
        self.reputation_address = reputation_address

        logger.info(f"TronClient initialized: network={network}")

    # ==========================================================================
    # EnhancedIdentityRegistry
    # ==========================================================================

    @retry_async(operation_name="register_agent")
    async def register_agent(self, token_uri: str, metadata_hash: bytes) -> str:
        """
        Call IdentityRegistry.register(string uri, bytes32 metadataHash).

        Args:
            token_uri: IPFS/HTTP URI for agent metadata
            metadata_hash: 32-byte keccak256 hash of canonical metadata JSON

        Returns:
            Transaction ID
        """
        return await self._send_transaction(
            "identity",
            "register",
            [token_uri, metadata_hash],
        )

    @retry_async(operation_name="set_agent_wallet")
    async def set_agent_wallet(self, agent_id: int, wallet: str) -> str:
        """
        Call IdentityRegistry.setAgentWallet(uint256 agentId, address wallet).

        Args:
            agent_id: Agent token ID
            wallet: Delegated wallet address

        Returns:
            Transaction ID
        """
        return await self._send_transaction(
            "identity",
            "setAgentWallet",
            [agent_id, wallet],
        )

    @retry_async(operation_name="agent_exists")
    async def agent_exists(self, agent_id: int) -> bool:
        """
        Call IdentityRegistry.exists(uint256 tokenId).

        Args:
            agent_id: Agent token ID

        Returns:
            True if agent exists
        """
        return await self._call_contract("identity", "exists", [agent_id])

    @retry_async(operation_name="get_agent_owner")
    async def get_agent_owner(self, agent_id: int) -> str:
        """
        Call IdentityRegistry.ownerOf(uint256 tokenId).

        Args:
            agent_id: Agent token ID

        Returns:
            Owner TRON address
        """
        return await self._call_contract("identity", "ownerOf", [agent_id])

    @retry_async(operation_name="get_token_uri")
    async def get_token_uri(self, agent_id: int) -> str:
        """
        Call IdentityRegistry.tokenURI(uint256 tokenId).

        Args:
            agent_id: Agent token ID

        Returns:
            Token URI string
        """
        return await self._call_contract("identity", "tokenURI", [agent_id])

    @retry_async(operation_name="get_agent_wallet")
    async def get_agent_wallet(self, agent_id: int) -> str:
        """
        Call IdentityRegistry.agentWalletOf(uint256 tokenId).

        Args:
            agent_id: Agent token ID

        Returns:
            Agent wallet address
        """
        return await self._call_contract("identity", "agentWalletOf", [agent_id])

    @retry_async(operation_name="total_agents")
    async def total_agents(self) -> int:
        """
        Call IdentityRegistry.totalAgents().

        Returns:
            Total number of registered agents
        """
        return await self._call_contract("identity", "totalAgents", [])

    # ==========================================================================
    # ValidationRegistry
    # ==========================================================================

    @retry_async(operation_name="validation_request")
    async def validation_request(
        self,
        agent_id: int,
        validator: str,
        request_uri: str,
        request_data_hash: bytes,
    ) -> str:
        """
        Call ValidationRegistry.validationRequest(
            uint256 agentId, address validator, string requestURI, bytes32 requestDataHash
        ).

        Args:
            agent_id: Agent to validate
            validator: Validator address
            request_uri: URI pointing to request details
            request_data_hash: 32-byte hash of request data (or zero bytes for auto)

        Returns:
            Transaction ID
        """
        return await self._send_transaction(
            "validation",
            "validationRequest",
            [agent_id, validator, request_uri, request_data_hash],
        )

    @retry_async(operation_name="complete_validation")
    async def complete_validation(
        self,
        request_id: bytes,
        result_uri: str,
        result_hash: bytes,
    ) -> str:
        """
        Call ValidationRegistry.completeValidation(
            bytes32 requestId, string resultURI, bytes32 resultHash
        ).

        Args:
            request_id: Validation request ID (bytes32)
            result_uri: URI pointing to result data
            result_hash: 32-byte hash of result data

        Returns:
            Transaction ID
        """
        return await self._send_transaction(
            "validation",
            "completeValidation",
            [request_id, result_uri, result_hash],
        )

    @retry_async(operation_name="reject_validation")
    async def reject_validation(
        self,
        request_id: bytes,
        result_uri: str,
        reason_hash: bytes,
    ) -> str:
        """
        Call ValidationRegistry.rejectValidation(
            bytes32 requestId, string resultURI, bytes32 reasonHash
        ).

        Args:
            request_id: Validation request ID (bytes32)
            result_uri: URI pointing to rejection reason
            reason_hash: 32-byte hash of rejection reason

        Returns:
            Transaction ID
        """
        return await self._send_transaction(
            "validation",
            "rejectValidation",
            [request_id, result_uri, reason_hash],
        )

    @retry_async(operation_name="cancel_validation")
    async def cancel_validation(self, request_id: bytes) -> str:
        """
        Call ValidationRegistry.cancelRequest(bytes32 requestId).

        Args:
            request_id: Validation request ID (bytes32)

        Returns:
            Transaction ID
        """
        return await self._send_transaction(
            "validation",
            "cancelRequest",
            [request_id],
        )

    @retry_async(operation_name="get_validation_request")
    async def get_validation_request(self, request_id: bytes) -> Dict[str, Any]:
        """
        Call ValidationRegistry.getRequest(bytes32 requestId).

        Args:
            request_id: Validation request ID (bytes32)

        Returns:
            Dict with request details
        """
        return await self._call_contract("validation", "getRequest", [request_id])

    @retry_async(operation_name="get_agent_requests")
    async def get_agent_validation_ids(self, agent_id: int) -> List[bytes]:
        """
        Call ValidationRegistry.getAgentRequests(uint256 agentId).

        Args:
            agent_id: Agent token ID

        Returns:
            List of request IDs (bytes32)
        """
        return await self._call_contract("validation", "getAgentRequests", [agent_id])

    @retry_async(operation_name="get_validation_summary")
    async def get_validation_summary(self, agent_id: int) -> Dict[str, int]:
        """
        Call ValidationRegistry.getSummaryForAgent(uint256 agentId).

        Args:
            agent_id: Agent token ID

        Returns:
            Dict with keys: total, pending, completed, rejected, cancelled
        """
        result = await self._call_contract("validation", "getSummaryForAgent", [agent_id])
        if isinstance(result, (list, tuple)) and len(result) == 5:
            return {
                "total": int(result[0]),
                "pending": int(result[1]),
                "completed": int(result[2]),
                "rejected": int(result[3]),
                "cancelled": int(result[4]),
            }
        return result

    # ==========================================================================
    # ReputationRegistry
    # ==========================================================================

    @retry_async(operation_name="give_feedback")
    async def give_feedback(
        self,
        agent_id: int,
        feedback_text: str,
        sentiment: str,
    ) -> str:
        """
        Call ReputationRegistry.giveFeedback(
            uint256 agentId, string feedbackText, Sentiment sentiment
        ).

        Args:
            agent_id: Agent token ID
            feedback_text: Feedback text (stored on-chain)
            sentiment: "positive", "neutral", or "negative"

        Returns:
            Transaction ID
        """
        sentiment_int = SENTIMENT_TO_INT.get(sentiment.lower())
        if sentiment_int is None:
            raise ContractError(f"Invalid sentiment: {sentiment}. Must be positive/neutral/negative")

        return await self._send_transaction(
            "reputation",
            "giveFeedback",
            [agent_id, feedback_text, sentiment_int],
        )

    @retry_async(operation_name="revoke_feedback")
    async def revoke_feedback(self, agent_id: int, feedback_index: int) -> str:
        """
        Call ReputationRegistry.revokeFeedback(uint256 agentId, uint256 feedbackIndex).

        Args:
            agent_id: Agent token ID
            feedback_index: Index of feedback to revoke

        Returns:
            Transaction ID
        """
        return await self._send_transaction(
            "reputation",
            "revokeFeedback",
            [agent_id, feedback_index],
        )

    @retry_async(operation_name="append_response")
    async def append_response(
        self,
        agent_id: int,
        feedback_index: int,
        response_text: str,
    ) -> str:
        """
        Call ReputationRegistry.appendResponse(
            uint256 agentId, uint256 feedbackIndex, string responseText
        ).

        Only callable by agent owner or delegated wallet.

        Args:
            agent_id: Agent token ID
            feedback_index: Feedback index to respond to
            response_text: Response text (stored on-chain)

        Returns:
            Transaction ID
        """
        return await self._send_transaction(
            "reputation",
            "appendResponse",
            [agent_id, feedback_index, response_text],
        )

    @retry_async(operation_name="get_feedback")
    async def get_feedback(
        self,
        agent_id: int,
        feedback_index: int,
    ) -> Dict[str, Any]:
        """
        Call ReputationRegistry.getFeedback(uint256 agentId, uint256 feedbackIndex).

        Returns:
            Dict with: client, feedbackText, sentiment, timestamp, revoked, responseCount
        """
        result = await self._call_contract(
            "reputation", "getFeedback", [agent_id, feedback_index]
        )
        if isinstance(result, (list, tuple)) and len(result) == 6:
            return {
                "client": result[0],
                "feedback_text": result[1],
                "sentiment": INT_TO_SENTIMENT.get(int(result[2]), "neutral"),
                "timestamp": int(result[3]),
                "revoked": bool(result[4]),
                "response_count": int(result[5]),
            }
        return result

    @retry_async(operation_name="get_feedback_count")
    async def get_feedback_count(self, agent_id: int) -> int:
        """
        Call ReputationRegistry.getFeedbackCount(uint256 agentId).

        Args:
            agent_id: Agent token ID

        Returns:
            Total feedback count for agent
        """
        return await self._call_contract("reputation", "getFeedbackCount", [agent_id])

    @retry_async(operation_name="get_feedback_summary")
    async def get_feedback_summary(self, agent_id: int) -> Dict[str, int]:
        """
        Call ReputationRegistry.getSummary(uint256 agentId).

        Returns:
            Dict with: total, active, revoked, positive, neutral, negative
        """
        result = await self._call_contract("reputation", "getSummary", [agent_id])
        if isinstance(result, (list, tuple)) and len(result) == 6:
            return {
                "total": int(result[0]),
                "active": int(result[1]),
                "revoked": int(result[2]),
                "positive": int(result[3]),
                "neutral": int(result[4]),
                "negative": int(result[5]),
            }
        return result

    # ==========================================================================
    # Internal helpers
    # ==========================================================================

    def _get_contract_address(self, contract_name: str) -> str:
        """Get contract address by name."""
        addresses = {
            "identity": self.identity_address,
            "validation": self.validation_address,
            "reputation": self.reputation_address,
        }
        addr = addresses.get(contract_name)
        if not addr:
            raise ConfigurationError(f"No address configured for {contract_name} contract")
        return addr

    async def _send_transaction(
        self,
        contract_name: str,
        function_name: str,
        params: list,
    ) -> str:
        """Build, sign, and broadcast a contract call transaction."""
        if not self.private_key:
            raise ConfigurationError("Private key required for write operations")

        address = self._get_contract_address(contract_name)

        try:
            contract = self.tron.get_contract(address)
            func = getattr(contract.functions, function_name)
            txn = func(*params)
            txn = txn.with_owner(self.tron.default_address)
            txn = txn.fee_limit(100_000_000)

            signed = txn.sign(self.private_key)
            result = signed.broadcast()

            tx_id = result.get("txid") or result.get("transaction", {}).get("txID")

            logger.info(f"{contract_name}.{function_name} tx: {tx_id}")
            return tx_id

        except Exception as e:
            raise ContractError(
                f"Transaction failed: {contract_name}.{function_name}: {e}"
            )

    async def _call_contract(
        self,
        contract_name: str,
        function_name: str,
        params: list,
    ):
        """Call a view/pure contract function (no gas)."""
        address = self._get_contract_address(contract_name)

        try:
            contract = self.tron.get_contract(address)
            func = getattr(contract.functions, function_name)
            result = func(*params)
            return result

        except Exception as e:
            raise ContractError(
                f"Call failed: {contract_name}.{function_name}: {e}"
            )
