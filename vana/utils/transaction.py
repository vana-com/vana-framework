from typing import Optional, Tuple, Dict, Any
from web3 import Web3
from web3.types import TxReceipt, HexBytes
from eth_account.signers.local import LocalAccount
import time
import vana

class TransactionManager:
    def __init__(self, web3: Web3, account: LocalAccount):
        self.web3 = web3
        self.account = account
        self._nonce_cache: Dict[str, int] = {}
        self._last_nonce_refresh = 0
        self.nonce_refresh_interval = 60
        self.chain_id = self.web3.eth.chain_id

    def _get_safe_nonce(self) -> int:
        """
        Get the next safe nonce, accounting for pending transactions
        """
        current_time = time.time()
        cache_key = self.account.address

        # Refresh nonce cache if expired
        if current_time - self._last_nonce_refresh > self.nonce_refresh_interval:
            # Get the latest confirmed nonce
            confirmed_nonce = self.web3.eth.get_transaction_count(self.account.address, 'latest')
            # Get pending nonce
            pending_nonce = self.web3.eth.get_transaction_count(self.account.address, 'pending')
            # Use the higher of the two to avoid nonce conflicts
            self._nonce_cache[cache_key] = max(confirmed_nonce, pending_nonce)
            self._last_nonce_refresh = current_time

        # Get and increment the cached nonce
        nonce = self._nonce_cache.get(cache_key, 0)
        self._nonce_cache[cache_key] = nonce + 1
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
            value: int = 0,
            max_retries: int = 3,
            base_gas_multiplier: float = 1.5,
            timeout: int = 180
    ) -> Tuple[HexBytes, TxReceipt]:
        """
        Send a transaction with improved retry logic and gas price management
        """
        retry_count = 0
        last_error = None

        # Check for too many pending transactions
        pending_count = (self.web3.eth.get_transaction_count(self.account.address, 'pending') -
                         self.web3.eth.get_transaction_count(self.account.address, 'latest'))

        if pending_count > 5:
            vana.logging.warning(f"Found {pending_count} pending transactions, attempting to clear...")
            self._clear_pending_transactions()

        while retry_count < max_retries:
            try:
                # Estimate gas with buffer
                gas_limit = function.estimate_gas({
                    'from': self.account.address,
                    'value': value,
                    'chainId': self.chain_id  # Add chain ID for estimation
                }) * 2

                # Calculate gas price with exponential backoff
                base_gas_price = self.web3.eth.gas_price
                gas_multiplier = base_gas_multiplier * (1.5 ** retry_count)
                gas_price = int(base_gas_price * gas_multiplier)

                # Get a safe nonce
                nonce = self._get_safe_nonce()

                tx = function.build_transaction({
                    'from': self.account.address,
                    'value': value,
                    'gas': gas_limit,
                    'gasPrice': gas_price,
                    'nonce': nonce,
                    'chainId': self.chain_id  # Add chain ID for EIP-155
                })

                signed_tx = self.web3.eth.account.sign_transaction(tx, self.account.key)
                vana.logging.info(
                    f"Sending transaction with nonce {nonce}, "
                    f"gas price {gas_price} ({gas_multiplier:.1f}x base) "
                    f"(retry {retry_count})"
                )

                tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

                # Wait for transaction with timeout
                start_time = time.time()
                while True:
                    try:
                        tx_receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                        if tx_receipt is not None:
                            if tx_receipt.status == 1:  # Check if transaction was successful
                                vana.logging.info(f"Transaction successful in block {tx_receipt['blockNumber']}")
                                return tx_hash, tx_receipt
                            else:
                                raise Exception("Transaction failed")
                    except Exception:
                        pass

                    if time.time() - start_time > timeout:
                        raise TimeoutError(f"Transaction not mined within {timeout} seconds")

                    time.sleep(2)

            except Exception as e:
                last_error = e
                retry_count += 1

                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    vana.logging.warning(
                        f"Transaction failed, waiting {wait_time} seconds before retry "
                        f"(attempt {retry_count}/{max_retries}): {str(e)}"
                    )
                    time.sleep(wait_time)
                else:
                    vana.logging.error(f"Transaction failed after {max_retries} attempts: {str(last_error)}")
                    raise

        raise Exception(f"Failed to send transaction after {max_retries} attempts: {str(last_error)}")