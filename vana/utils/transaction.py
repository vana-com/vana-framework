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
        self._nonce_cache: Dict[str, int] = {}
        self._last_nonce_refresh = 0
        self.nonce_refresh_interval = 60
        self.chain_id = self.web3.eth.chain_id
        self._nonce_lock = Lock()

    def _get_safe_nonce(self) -> Nonce:
        """
        Get the next safe nonce, accounting for pending transactions.
        Thread-safe implementation for concurrent transaction submissions.

        Returns:
            Nonce: Next safe nonce to use for transaction
        """
        with self._nonce_lock:
            current_time = time.time()
            cache_key = self.account.address

            should_refresh = (
                    current_time - self._last_nonce_refresh > self.nonce_refresh_interval or
                    cache_key not in self._nonce_cache
            )

            if should_refresh:
                try:
                    # Get both confirmed and pending nonces
                    confirmed_nonce: Nonce = self.web3.eth.get_transaction_count(self.account.address, 'latest')
                    pending_nonce: Nonce = self.web3.eth.get_transaction_count(self.account.address, 'pending')

                    # Use max to account for pending transactions
                    new_nonce: Nonce = Nonce(max(int(confirmed_nonce), int(pending_nonce)))

                    # Only update if new nonce is higher than cached
                    cached_nonce: Nonce = Nonce(self._nonce_cache.get(cache_key, 0))
                    self._nonce_cache[cache_key] = Nonce(max(int(new_nonce), int(cached_nonce)))

                    self._last_nonce_refresh = current_time

                    vana.logging.debug(
                        f"Nonce cache refreshed - Latest: {confirmed_nonce}, "
                        f"Pending: {pending_nonce}, "
                        f"Using: {self._nonce_cache[cache_key]}"
                    )
                except Exception as e:
                    vana.logging.error(f"Error refreshing nonce: {str(e)}")
                    if cache_key not in self._nonce_cache:
                        raise

            # Get and increment the cached nonce atomically
            nonce = self._nonce_cache[cache_key]
            self._nonce_cache[cache_key] = Nonce(int(nonce) + 1)

            return nonce

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
            max_gas_multiplier: float = 5.0,
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
            max_gas_multiplier: Maximum allowed gas price multiplier (default: 5.0)
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
                # Estimate gas with conservative buffer
                gas_estimate = function.estimate_gas({
                    'from': account.address,
                    'value': value,
                    'chainId': self.chain_id
                })
                gas_limit = int(gas_estimate * 1.5)

                # Calculate gas price - use base price for first attempt
                base_gas_price = self.web3.eth.gas_price
                if retry_count == 0:
                    gas_price = base_gas_price
                else:
                    gas_multiplier = min(
                        base_gas_multiplier * (1.2 ** (retry_count - 1)),
                        max_gas_multiplier
                    )
                    gas_price = int(base_gas_price * gas_multiplier)

                # Log gas details
                vana.logging.debug(
                    f"Gas details - Base price: {self.web3.from_wei(base_gas_price, 'gwei')} Gwei, " +
                    (f"Multiplier: {gas_multiplier:.2f}x, " if retry_count > 0 else "") +
                    f"Final price: {self.web3.from_wei(gas_price, 'gwei')} Gwei"
                )

                # Get safe nonce and build transaction
                nonce = self._get_safe_nonce()
                tx = function.build_transaction({
                    'from': account.address,
                    'value': value,
                    'gas': gas_limit,
                    'gasPrice': gas_price,
                    'nonce': nonce,
                    'chainId': self.chain_id
                })

                try:
                    # Simulate transaction first to catch reverts
                    self.web3.eth.call({
                        'from': tx['from'],
                        'to': tx['to'],
                        'data': tx['data'],
                        'value': tx['value'],
                        'gas': tx['gas'],
                        'gasPrice': tx['gasPrice'],
                    })
                except ContractLogicError as e:
                    vana.logging.error(f"Transaction would revert: {str(e)}")
                    raise Exception(f"Transaction would revert: {str(e)}")

                signed_tx = self.web3.eth.account.sign_transaction(tx, account.key)

                vana.logging.info(
                    f"Sending transaction with nonce {nonce}, "
                    f"gas price {self.web3.from_wei(gas_price, 'gwei')} Gwei "
                    f"(retry {retry_count if retry_count > 0 else 'initial attempt'})"
                )

                tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

                # Wait for receipt with timeout
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