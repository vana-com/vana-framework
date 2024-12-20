# The MIT License (MIT)
# Copyright © 2024 Corsali, Inc. dba Vana

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import argparse
import copy
import logging as native_logging
import os
import time
from decimal import Decimal
from typing import Optional, List, Union

from eth_account.signers.local import LocalAccount
from retry import retry
from rich.prompt import Confirm
from web3 import Web3
from web3.contract.contract import ContractFunction
from web3.exceptions import ContractCustomError
from web3.exceptions import TransactionNotFound
from web3.middleware import geth_poa_middleware

import vana
from vana.utils.transaction import TransactionManager
from vana.utils.web3 import decode_custom_error

logger = native_logging.getLogger("vana")

Balance = Union[int, Decimal]


class ChainManager:
    """
    The ChainManager class is an interface for interacting with the Vana blockchain.
    """

    @staticmethod
    def setup_config(network: str, config: vana.Config):
        chain_endpoint = config.chain.get("chain_endpoint")

        if network is not None:
            (
                evaluated_network,
                evaluated_endpoint,
            ) = ChainManager.determine_chain_endpoint_and_network(network, chain_endpoint)
        else:
            if config.get("__is_set", {}).get("chain.chain_endpoint"):
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = ChainManager.determine_chain_endpoint_and_network(
                    config.chain.chain_endpoint, chain_endpoint
                )
            elif config.get("__is_set", {}).get("chain.network"):
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = ChainManager.determine_chain_endpoint_and_network(
                    config.chain.network, chain_endpoint
                )
            elif config.chain.get("chain_endpoint"):
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = ChainManager.determine_chain_endpoint_and_network(
                    config.chain.chain_endpoint, chain_endpoint
                )
            elif config.chain.get("network"):
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = ChainManager.determine_chain_endpoint_and_network(
                    config.chain.network
                )
            else:
                (
                    evaluated_network,
                    evaluated_endpoint,
                ) = ChainManager.determine_chain_endpoint_and_network(
                    vana.defaults.chain.network, chain_endpoint
                )
        return (
            evaluated_endpoint,
            evaluated_network,
        )

    def __init__(
            self,
            config: Optional[vana.Config] = None,
    ) -> None:
        """
        Initializes a ChainManager interface for interacting with the Vana blockchain.
        """
        if config is None:
            config = self.config()
        self.config = copy.deepcopy(config)

        self.config.chain.chain_endpoint, self.config.chain.network = ChainManager.setup_config(
            self.config.chain.network, config)

        vana.logging.debug(
            f"Connected to {self.config.chain.network} network and {self.config.chain.chain_endpoint}."
        )
        self.web3 = Web3(Web3.HTTPProvider(self.config.chain.chain_endpoint))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.wallet = vana.Wallet(config=self.config)
        self.tx_manager = TransactionManager(self.web3, self.wallet.hotkey)

    @staticmethod
    def config() -> "config":
        parser = argparse.ArgumentParser()
        ChainManager.add_args(parser)
        return vana.Config(parser, args=[])

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser, prefix: Optional[str] = None):
        prefix_str = "" if prefix is None else f"{prefix}."
        try:
            default_network = os.getenv("CHAIN_NETWORK") or "vana"
            default_chain_endpoint = (
                    os.getenv("CHAIN_NETWORK_ENDPOINT")
                    or vana.__vana_entrypoint__
            )
            parser.add_argument(
                "--" + prefix_str + "chain.network",
                default=default_network,
                type=str,
                help="""The chain network flag. The likely choices are:
                                            -- vana (main network)
                                            -- satori (satori test network)
                                            -- test (test network)
                                            -- local (local running network)
                                        """,
            )
            parser.add_argument(
                "--" + prefix_str + "chain.chain_endpoint",
                default=default_chain_endpoint,
                type=str,
                help="""The chain endpoint flag. If set, overrides the --network flag.""")
        except argparse.ArgumentError:
            # re-parsing arguments.
            pass

    def serve_node_server(
            self,
            dlp_uid: int,
            node_server: "vana.NodeServer"
    ) -> bool:
        """
        Registers a NodeServer endpoint on the network for a specific Node.
        TODO: this could be implemented via a smart contract.
        """
        return True

    def remove_node_server(
            self,
            dlp_uid: int,
            node_server: "vana.NodeServer"
    ) -> bool:
        """
        De-registers a NodeServer endpoint on the network for a specific Node.
        TODO: this could be implemented via to a smart contract.
        """
        return True

    def get_active_node_servers(self, omit: List[vana.NodeServerInfo] = []) -> List["vana.NodeServerInfo"]:
        """
        Returns a list of active NodeServers on the network.
        TODO: this could be implemented via a smart contract.
        """
        return []

    def state(
            self,
            dlp_uid: int,
            lite: bool = True,
            block: Optional[int] = None,
    ) -> "State":
        """
        Returns a synced state for a specified DLP within the Vana network. The state
        represents the network's structure, including node connections and interactions.
        """
        state_ = vana.State(
            network=self.config.chain.network, dlp_uid=dlp_uid, lite=lite, sync=False
        )
        state_.sync(block=block, lite=lite, chain_manager=self)

        return state_

    def send_transaction(self,
         function: ContractFunction,
         account: LocalAccount,
         value=0,
         max_retries=3,
         base_gas_multiplier=1.5,
     ):
        """
        Send a transaction using the TransactionManager
        """
        return self.tx_manager.send_transaction(
            function=function,
            value=self.web3.to_wei(value, 'ether'),
            account=account,
            max_retries=max_retries,
            base_gas_multiplier=base_gas_multiplier
        )

    def read_contract_fn(self, function: ContractFunction):
        try:
            return function.call()
        except ContractCustomError as e:
            decoded_error = decode_custom_error(function.contract_abi, e.data)
            vana.logging.error(f"Failed to read from contract function: {decoded_error}")
        except Exception as e:
            vana.logging.error(f"Failed to read from contract function: {e}")

    def get_current_block(self) -> int:
        """
        Returns the current block number on the blockchain. This function provides the latest block
        number, indicating the most recent state of the blockchain.

        Returns:
            int: The current chain block number.

        Knowing the current block number is essential for querying real-time data and performing time-sensitive
        operations on the blockchain. It serves as a reference point for network activities and data synchronization.
        """
        return self.web3.eth.block_number

    def close(self):
        """
        Cleans up resources for this ChainManager instance like active websocket connection and active extensions
        """
        pass

    def get_total_stake_for_coldkey(
            self, h160_address: str, block: Optional[int] = None
    ) -> Optional["Balance"]:
        return 0

        # """Returns the total stake held on a coldkey across all hotkeys including delegates"""
        # _result = self.query_subtensor("TotalColdkeyStake", block, [h160_address])
        # if not hasattr(_result, "value") or _result is None:
        #     return None
        # return Balance.from_rao(_result.value)

    @staticmethod
    def determine_chain_endpoint_and_network(network: str, chain_endpoint=None):
        """Determines the chain endpoint and network from the passed network or chain_endpoint.

        Args:
            network (str): The network flag. The choices are: ``-- vana`` (main network), ``-- archive`` (archive network +300 blocks), ``-- local`` (local running network), ``-- test`` (test network).
            chain_endpoint (str): The chain endpoint flag. If set, overrides the network argument.
        Returns:
            network (str): The network flag.
            chain_endpoint (str): The chain endpoint flag. If set, overrides the ``network`` argument.
        """
        if network is None:
            return None, None
        if network in vana.__networks__:
            if network == "vana":
                return network, chain_endpoint if chain_endpoint is not None else vana.__vana_entrypoint__
            if network == "islander":
                return network, chain_endpoint if chain_endpoint is not None else vana.__islander_entrypoint__
            if network == "maya":
                return network, chain_endpoint if chain_endpoint is not None else vana.__maya_entrypoint__
            if network == "moksha":
                return network, chain_endpoint if chain_endpoint is not None else vana.__moksha_entrypoint__
            if network == "satori":
                return network, chain_endpoint if chain_endpoint is not None else vana.__satori_entrypoint__
            elif network == "local":
                return network, chain_endpoint if chain_endpoint is not None else vana.__local_entrypoint__
            elif network == "archive":
                return network, chain_endpoint if chain_endpoint is not None else vana.__archive_entrypoint__
        else:
            if (
                    network == vana.__vana_entrypoint__
                    or "rpc.vana" in network
            ):
                return "vana", chain_endpoint if chain_endpoint is not None else vana.__vana_entrypoint__
            elif (
                    network == vana.__islander_entrypoint__
                    or "rpc.islander.vana" in network
            ):
                return "islander", chain_endpoint if chain_endpoint is not None else vana.__islander_entrypoint__
            elif (
                    network == vana.__maya_entrypoint__
                    or "rpc.maya.vana" in network
            ):
                return "maya", chain_endpoint if chain_endpoint is not None else vana.__maya_entrypoint__
            elif (
                    network == vana.__moksha_entrypoint__
                    or "rpc.moksha.vana" in network
            ):
                return "moksha", chain_endpoint if chain_endpoint is not None else vana.__moksha_entrypoint__
            elif (
                    network == vana.__satori_entrypoint__
                    or "rpc.satori.vana" in network
            ):
                return "satori", chain_endpoint if chain_endpoint is not None else vana.__satori_entrypoint__
            elif (
                    network == vana.__archive_entrypoint__
                    or "archive.vana" in network
            ):
                return "archive", chain_endpoint if chain_endpoint is not None else vana.__archive_entrypoint__
            elif "127.0.0.1" in network or "localhost" in network:
                return "local", network
            else:
                return "unknown", network

    ################
    #### Legacy ####
    ################

    def get_balance(self, address: str, block: Optional[int] = None) -> Balance:
        """
        Retrieves the token balance of a specific address within the Vana network. This function queries
        the blockchain to determine the amount of tokens held by a given account.

        Args:
            address (str): The EVM-compatible address.
            block (int, optional): The blockchain block number at which to perform the query.

        Returns:
            Balance: The account balance at the specified block, represented as a Balance object.

        This function is important for monitoring account holdings and managing financial transactions
        within the Vana ecosystem. It helps in assessing the economic status and capacity of network participants.
        """
        vana.logging.info(f"Fetching balance for address {address}")
        try:
            @retry(delay=2, tries=3, backoff=2, max_delay=4, logger=logger)
            def make_web3_call_with_retry():
                vana.logging.info(f"Fetching balance for address {address}")
                return self.web3.eth.get_balance(address, block_identifier=block)

            result = make_web3_call_with_retry()
        except Exception as e:
            vana.logging.error(f"Error fetching balance for address {address}: {e}")
            return 0

        vana.logging.info(f"Balance for address {address}: {result}")
        return Web3.from_wei(result, "ether")

    def transfer(
            self,
            wallet: "vana.Wallet",
            dest: str,
            amount: Union[Balance, float],
            wait_for_inclusion: bool = True,
            wait_for_finalization: bool = False,
            prompt: bool = False,
    ) -> bool:
        """
        Executes a transfer of funds from the provided wallet to the specified destination address.
        This function is used to move tokens within the Vana blockchain network, facilitating transactions
        between nodes.

        Args:
            wallet (vana.Wallet): The wallet from which funds are being transferred.
            dest (str): The destination public key address.
            amount (Union[Balance, float]): The amount to be transferred.
            wait_for_inclusion (bool, optional): Waits for the transaction to be included in a block.
            wait_for_finalization (bool, optional): Waits for the transaction to be finalized on the blockchain.
            prompt (bool, optional): If ``True``, prompts for user confirmation before proceeding.

        Returns:
            bool: ``True`` if the transfer is successful, False otherwise.
        """
        # TODO: Beware of allowing this to be switched to the hotkey
        signer = wallet.coldkey

        if not Web3.is_address(dest):
            logger.error(f"Invalid destination address: {dest}")
            return False

        # Convert amount to Wei.
        amount_in_wei = Web3.to_wei(amount, 'ether') if not isinstance(amount, int) else amount

        # Check balance.
        logger.info("Checking balance...")
        account_balance = self.get_balance(signer.address)
        gas_price = self.web3.eth.gas_price
        gas_limit = 21000  # Gas limit for a standard ETH transfer
        fee_in_wei = gas_price * gas_limit
        fee_in_eth = Web3.from_wei(fee_in_wei, 'ether')

        # Check if we have enough balance.
        if account_balance < (Decimal(amount) + fee_in_eth):
            logger.error(f"Not enough balance: balance: {account_balance}, amount: {amount}, fee: {fee_in_eth}")
            return False

        # Ask before moving on.
        if prompt:
            if not Confirm.ask(
                    f"Do you want to transfer: amount: {amount}, from: {signer.address}, to: {dest}, for fee: {fee_in_eth} ETH"):
                return False

        # Create and sign the transaction.
        transaction = {
            'to': dest,
            'value': amount_in_wei,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'nonce': self.web3.eth.get_transaction_count(signer.address),
            'chainId': self.web3.eth.chain_id
        }

        signed_txn = self.web3.eth.account.sign_transaction(transaction, signer.key)

        # Send the transaction.
        logger.info("Sending transaction...")
        txn_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

        # Wait for transaction inclusion.
        if wait_for_inclusion:
            try:
                receipt = self.web3.eth.wait_for_transaction_receipt(txn_hash, timeout=120)
                if receipt.status == 1:
                    logger.info(f"Transaction included in block {receipt.blockNumber}. Hash: {txn_hash.hex()}")
                else:
                    logger.error("Transaction failed.")
                    return False
            except TransactionNotFound:
                logger.error("Transaction not found within timeout period.")
                return False

        # Wait for transaction finalization.
        if wait_for_finalization:
            try:
                while True:
                    receipt = self.web3.eth.get_transaction_receipt(txn_hash)
                    if receipt.blockNumber is not None:
                        logger.info(f"Transaction finalized in block {receipt.blockNumber}. Hash: {txn_hash.hex()}")
                        break
                    time.sleep(2)
            except TransactionNotFound:
                logger.error("Transaction not found within timeout period.")
                return False

        return True
