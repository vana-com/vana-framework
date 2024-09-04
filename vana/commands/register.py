# The MIT License (MIT)
# Copyright © 2024 Corsali, Inc. dba Vana

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import argparse
import vana
from vana.commands.base_command import BaseCommand
from rich.prompt import Prompt, Confirm


class RegisterCommand(BaseCommand):
    """
    Executes the `register` command to register a validator node on the Vana network using TEE Pool Contract.

    This command allows users to register a validator node with a specified name, URL, and wallet.
    It interacts with the TeePoolImplementation smart contract to add the validator as a TEE.

    Usage:
        The command requires specifying the validator name, URL, and wallet name.

    Args:
        name (str): The name of the validator to register.
        url (str): The URL of the validator node.
        wallet (str): The name of the wallet to use for registration.

    Example usage:
        vanacli register satya --url=https://teenode.com --wallet=validator_4000
    """

    @staticmethod
    def run(cli: "vana.cli"):
        try:
            chain_manager: "vana.ChainManager" = vana.ChainManager(config=cli.config)
            wallet = vana.Wallet(config=cli.config)

            # Connect to the contract
            contract_address = vana.__satori_tee_pool_contract_address
            contract_abi = [
                {
                    "inputs": [
                        {
                            "internalType": "address",
                            "name": "teeAddress",
                            "type": "address"
                        },
                        {
                            "internalType": "string",
                            "name": "url",
                            "type": "string"
                        }
                    ],
                    "name": "addTee",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
            contract = chain_manager.web3.eth.contract(address=contract_address, abi=contract_abi)

            # Prepare transaction
            transaction = contract.functions.addTee(
                wallet.hotkey.address,
                cli.config.url
            ).build_transaction({
                'from': wallet.hotkey.address,
                'nonce': chain_manager.web3.eth.get_transaction_count(wallet.hotkey.address),
            })

            # Sign and send transaction
            signed_txn = wallet.hotkey.sign_transaction(transaction)
            tx_hash = chain_manager.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

            # Wait for transaction receipt
            tx_receipt = chain_manager.web3.eth.wait_for_transaction_receipt(tx_hash)

            if tx_receipt['status'] == 1:
                vana.__console__.print(f"[bold green]Successfully registered validator node '{cli.config.name}' with URL '{cli.config.url}'[/bold green]")
                vana.__console__.print(f"Transaction hash: {tx_hash.hex()}")
            else:
                vana.__console__.print("[bold red]Transaction failed. Please check the contract state and try again.[/bold red]")

        except Exception as e:
            vana.__console__.print(f"[bold red]Error:[/bold red] {str(e)}")
        finally:
            if "chain_manager" in locals():
                chain_manager.close()
                vana.logging.debug("closing chain_manager connection")

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        register_parser = parser.add_parser(
            "register", help="Register a validator node on the Vana network."
        )
        register_parser.add_argument("name", type=str, help="The name of the validator to register")
        register_parser.add_argument("--url", type=str, required=True, help="The URL of the validator node")
        register_parser.add_argument("--wallet", type=str, required=True, help="The name of the wallet to use for registration")

        vana.Wallet.add_args(register_parser)
        vana.ChainManager.add_args(register_parser)

    @staticmethod
    def check_config(config: "vana.Config"):
        if not config.is_set("name") and not config.no_prompt:
            config.name = Prompt.ask("Enter validator name")
        if not config.is_set("url") and not config.no_prompt:
            config.url = Prompt.ask("Enter validator URL")
        if not config.is_set("wallet") and not config.no_prompt:
            config.wallet = Prompt.ask("Enter wallet name")

        # Confirm registration details
        if not config.no_prompt:
            vana.__console__.print("\nRegistration Details:")
            vana.__console__.print(f"Validator Name: {config.name}")
            vana.__console__.print(f"URL: {config.url}")
            vana.__console__.print(f"Wallet: {config.wallet}")

            if not Confirm.ask("Do you want to proceed with the registration?"):
                vana.__console__.print("Registration cancelled.")
                exit(0)