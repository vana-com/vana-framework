from threading import Lock
from typing import Optional, Tuple, Dict, Any
from web3 import Web3
from web3.exceptions import ContractLogicError, ContractCustomError
from web3.types import TxReceipt, HexBytes, Nonce
from eth_account.signers.local import LocalAccount
import time
import vana
from vana.utils.web3 import decode_custom_error


class TransactionManager:
    def __init__(self, web3: Web3, account: LocalAccount):
        self.web3 = web3
        self.account = account
        self._nonce_lock = Lock()
        self.chain_id = self.web3.eth.chain_id

    def _clear_pending_transactions(self, max_wait_time: int = 180):
        """
        Clear pending transactions by sending zero-value transactions with higher gas price.

        Args:
            max_wait_time: Maximum time to wait for transactions to clear in seconds.
        """
        try:
            # Get all pending transactions for the account
            pending_nonce = self.web3.eth.get_transaction_count(self.account.address, 'pending')
            confirmed_nonce = self.web3.eth.get_transaction_count(self.account.address, 'latest')
            eth_transfer_gas = 21000  # Standard gas cost for basic ETH transfer

            if pending_nonce > confirmed_nonce:
                initial_pending = pending_nonce - confirmed_nonce
                vana.logging.info(f"Clearing {initial_pending} pending transactions")
                highest_nonce = pending_nonce - 1  # Keep track of highest nonce we're replacing

                # Send replacement transactions with higher gas price
                for nonce in range(confirmed_nonce, pending_nonce):
                    replacement_tx = {
                        'from': self.account.address,
                        'to': self.account.address,
                        'value': 0,
                        'nonce': nonce,
                        'gas': eth_transfer_gas,
                        'gasPrice': self.web3.eth.gas_price * 4,
                        'chainId': self.chain_id
                    }

                    signed_tx = self.web3.eth.account.sign_transaction(replacement_tx, self.account.key)
                    try:
                        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                        vana.logging.info(f"Sent replacement transaction for nonce {nonce}: {tx_hash.hex()}")
                    except Exception as e:
                        vana.logging.warning(f"Failed to replace transaction with nonce {nonce}: {str(e)}")

                # Wait for transactions to be processed by monitoring the latest nonce
                pending_remaining = initial_pending
                start_time = time.time()
                while time.time() - start_time < max_wait_time:
                    current_nonce = self.web3.eth.get_transaction_count(self.account.address, 'latest')
                    pending_remaining = (
                            self.web3.eth.get_transaction_count(self.account.address, 'pending') -
                            current_nonce
                    )

                    if current_nonce > highest_nonce:
                        vana.logging.info("All replacement transactions processed successfully")
                        return

                    if pending_remaining == 0:
                        vana.logging.info("No more pending transactions")
                        return

                    if pending_remaining != initial_pending:
                        vana.logging.info(
                            f"Progress: {initial_pending - pending_remaining}/{initial_pending} "
                            f"transactions processed"
                        )

                    time.sleep(5)  # Check every 5 seconds

                vana.logging.warning(
                    f"Timed out waiting for transactions to clear after {max_wait_time} seconds. "
                    f"Remaining pending: {pending_remaining}"
                )

        except Exception as e:
            vana.logging.error(f"Error clearing pending transactions: {str(e)}")

    def send_transaction(
            self,
            function: Any,
            account: LocalAccount,
            value: int = 0,
            max_retries: int = 3,
            base_gas_multiplier: float = 1.5,
            timeout: int = 30,
            clear_pending_transactions: bool = False
    ) -> Tuple[HexBytes, TxReceipt]:
        """
        Send a transaction with retry logic and gas price management.
        First attempt uses network gas price, subsequent retries increase gas price with bounded multiplier.
        Will not retry on contract revert errors as these are deterministic failures.

        Args:
            function: Web3 contract function to call
            account: LocalAccount to sign and send transaction from
            value: Value in wei to send with transaction (default: 0)
            max_retries: Maximum number of retry attempts (default: 3)
            base_gas_multiplier: Base multiplier for gas price on retries (default: 1.5)
            timeout: Timeout in seconds to wait for transaction receipt (default: 30)
            clear_pending_transactions: Attempt to clear pending transactions before sending (default: False)

        Returns:
            Tuple[HexBytes, TxReceipt]: Transaction hash and receipt

        Raises:
            ContractLogicError: If transaction would revert (no retries)
            TimeoutError: If transaction is not mined within timeout period
            Exception: If transaction fails after all retry attempts
        """
        if clear_pending_transactions:
            pending_count = (self.web3.eth.get_transaction_count(self.account.address, 'pending') -
                             self.web3.eth.get_transaction_count(self.account.address, 'latest'))
            if pending_count > 0:
                vana.logging.warning(f"Found {pending_count} pending transactions, attempting to clear...")
                self._clear_pending_transactions()

        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                with self._nonce_lock:
                    # Get nonce directly from chain within lock
                    nonce = self.web3.eth.get_transaction_count(self.account.address, 'pending')

                    # Estimate gas with conservative buffer
                    gas_estimate = function.estimate_gas({
                        'from': account.address,
                        'value': value,
                        'chainId': self.chain_id,
                        'nonce': nonce
                    })
                    gas_limit = int(gas_estimate * 2)

                    # Calculate gas prices for EIP-1559
                    base_fee = self.web3.eth.get_block('latest')['baseFeePerGas']
                    gas_multiplier = base_gas_multiplier * (1.5 ** retry_count)
                    priority_fee = self.web3.eth.max_priority_fee
                    max_fee_per_gas = int(base_fee * gas_multiplier) + priority_fee
                    max_priority_fee_per_gas = priority_fee

                    # Build transaction
                    tx = function.build_transaction({
                        'from': account.address,
                        'value': value,
                        'gas': gas_limit,
                        'maxFeePerGas': max_fee_per_gas,
                        'maxPriorityFeePerGas': max_priority_fee_per_gas,
                        'nonce': nonce,
                        'chainId': self.chain_id,
                        'type': 2
                    })

                    try:
                        # Simulate transaction first to catch reverts
                        self.web3.eth.call({
                            'from': tx['from'],
                            'to': tx['to'],
                            'data': tx['data'],
                            'value': tx['value'],
                            'gas': tx['gas'],
                            'maxFeePerGas': tx['maxFeePerGas'],
                            'maxPriorityFeePerGas': tx['maxPriorityFeePerGas'],
                            'type': 2
                        })
                    except ContractLogicError as e:
                        vana.logging.error(f"Transaction would revert: {str(e)}")
                        raise Exception(f"Transaction would revert: {str(e)}")

                    signed_tx = self.web3.eth.account.sign_transaction(tx, account.key)

                    vana.logging.info(
                        f"Sending transaction with nonce {nonce}, "
                        f"gas limit {gas_limit}, gas price {max_fee_per_gas} ({max_priority_fee_per_gas})"
                        f"(retry {retry_count})"
                    )

                    tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

                # Wait for receipt outside the lock since transaction is already submitted
                start_time = time.time()
                while True:
                    try:
                        tx_receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                        if tx_receipt is not None:
                            if tx_receipt.status == 1:
                                vana.logging.info(
                                    f"Transaction successful in block {tx_receipt['blockNumber']} "
                                    f"(used {tx_receipt['gasUsed']} gas)"
                                )
                                return tx_hash, tx_receipt
                            else:
                                raise Exception(f"Transaction reverted - consumed {tx_receipt['gasUsed']} gas")
                    except Exception as e:
                        if not str(e).startswith("Transaction reverted"):
                            pass  # Ignore receipt fetch errors
                        else:
                            raise  # Re-raise transaction failure

                    if time.time() - start_time > timeout:
                        raise TimeoutError(f"Transaction not mined within {timeout} seconds")

                    time.sleep(2)

            except ContractCustomError as e:
                # Decode custom error if possible
                try:
                    decoded_error = decode_custom_error(function.contract_abi, e.data)
                    error_msg = f"Contract custom error: {decoded_error}"
                except Exception:
                    error_msg = f"Contract custom error: {str(e)}"

                vana.logging.error(error_msg)
                raise Exception(error_msg)  # No retry for contract errors

            except ContractLogicError as e:
                error_msg = f"Transaction would revert: {str(e)}"
                vana.logging.error(error_msg)
                raise Exception(error_msg)  # No retry for reverts

            except Exception as e:
                # Handle other errors (network, timeout etc)
                last_error = e
                retry_count += 1

                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    vana.logging.warning(
                        f"Transaction failed (will retry), waiting {wait_time} seconds: {str(e)}"
                    )
                    time.sleep(wait_time)
                else:
                    vana.logging.error(f"Transaction failed after {max_retries} attempts: {str(last_error)}")
                    raise

        raise Exception(f"Failed to send transaction after {max_retries} attempts: {str(last_error)}")