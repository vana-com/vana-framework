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
        Note: This method should be called within the context of _nonce_lock to prevent
        concurrent clearing attempts from multiple threads.

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

                # Start with current gas price and use increasing multiplier for each retry
                base_gas_price = self.web3.eth.gas_price
                gas_multiplier = 5  # Higher initial multiplier to ensure replacement

                # Send replacement transactions with higher gas price
                for nonce in range(confirmed_nonce, pending_nonce):
                    # For each failed attempt, increase the multiplier
                    for attempt in range(3):  # Try up to 3 times with increasing gas price
                        replacement_tx = {
                            'from': self.account.address,
                            'to': self.account.address,
                            'value': 0,
                            'nonce': nonce,
                            'gas': eth_transfer_gas,
                            'gasPrice': int(base_gas_price * (gas_multiplier + attempt * 2)),  # Increase gas price on each attempt
                            'chainId': self.chain_id
                        }

                        try:
                            signed_tx = self.web3.eth.account.sign_transaction(replacement_tx, self.account.key)
                            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                            vana.logging.info(f"Sent replacement transaction for nonce {nonce}: {tx_hash.hex()}")
                            break  # Success, break the retry loop
                        except Exception as e:
                            if 'replacement transaction underpriced' in str(e) and attempt < 2:
                                vana.logging.warning(f"Attempt {attempt+1}: Transaction with nonce {nonce} needs higher gas price: {str(e)}")
                                continue  # Try again with higher gas price
                            else:
                                vana.logging.warning(f"Failed to replace transaction with nonce {nonce}: {str(e)}")
                                break  # Give up on this nonce after max attempts or different error

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
            max_pending_transactions: int = 10
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
            max_pending_transactions: Clear transactions when pending count exceeds this threshold; set to 0 to disable (default: 10)

        Returns:
            Tuple[HexBytes, TxReceipt]: Transaction hash and receipt

        Raises:
            ContractLogicError: If transaction would revert (no retries)
            TimeoutError: If transaction is not mined within timeout period
            Exception: If transaction fails after all retry attempts
        """
        # Check for a gap between pending and latest nonce
        pending_count = (self.web3.eth.get_transaction_count(self.account.address, 'pending') -
                         self.web3.eth.get_transaction_count(self.account.address, 'latest'))

        # Clear pending transactions if count exceeds threshold (disable by setting threshold to 0)
        if max_pending_transactions > 0 and pending_count > max_pending_transactions:
            # Use the existing nonce_lock to prevent multiple threads from clearing transactions simultaneously
            with self._nonce_lock:
                # Check again inside the lock in case another thread already cleared transactions
                current_pending_count = (self.web3.eth.get_transaction_count(self.account.address, 'pending') -
                                        self.web3.eth.get_transaction_count(self.account.address, 'latest'))
                if current_pending_count > max_pending_transactions:
                    vana.logging.warning(
                        f"Found {current_pending_count} pending transactions (threshold: {max_pending_transactions}), attempting to clear..."
                    )
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