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
import traceback

from rich.prompt import Prompt

import vana
from vana.commands.base_command import BaseCommand


class RegisterCommand(BaseCommand):
    """
    Executes the `register` command to register a validator node on the Vana network using TEE Pool Contract.

    This command allows users to register a validator node with a specified URL and wallet.
    It interacts with the TeePoolImplementation smart contract to add the validator as a TEE.

    Usage:
        The command requires specifying the validator URL and wallet name.

    Args:
        url (str): The URL of the validator node
        tee_address (str): The hotkey address of the TEE node to register
        wallet (str): The name of the wallet to use for registration, should have neccessary permissions

    Example usage:
        vanacli satya register --url=https://teenode.com --wallet.name=dlp-owner --chain.network=moksha --tee_address=0x123...
    """

    @staticmethod
    def run(cli: "vana.cli"):
        """Register a URL with the Satya protocol."""
        url = cli.config.url
        vana.__console__.print(f"Registering URL with Satya: [bold]{url}[/bold]")
        try:
            vana_client = vana.Client(config=cli.config)
            wallet = vana.Wallet(config=cli.config if cli.config.wallet else None)

            tee_address = cli.config.get('tee_address', wallet.hotkey.address)
            public_key = cli.config.get('public_key', wallet.get_hotkey_public_key())

            tx_hash, tx_receipt = vana_client.register_tee(
                url=cli.config.url,
                public_key=public_key,
                tee_address=tee_address
            )

            if tx_receipt['status'] == 1:
                vana.__console__.print(
                    f"[bold green]Successfully registered validator node with:"
                    f"\n- URL: '{cli.config.url}'"
                    f"\n- TEE Address: '{tee_address}'"
                    f"\n- Public Key: '{public_key}'[/bold green]"
                )
                vana.__console__.print(f"Transaction hash: {tx_hash.hex()}")
            else:
                vana.__console__.print(
                    "[bold red]Transaction failed. Please check the contract state and try again.[/bold red]")

        except Exception as e:
            vana.__console__.print(f"[bold red]Error:[/bold red] {str(e)}")
            traceback.print_exc()

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        satya_parser = parser.add_parser(
            "register", help="Register a URL with the Satya protocol."
        )
        satya_parser.add_argument("--url", type=str, required=False, help="The URL to register.")
        satya_parser.add_argument("--wallet.name", type=str, required=False,
                                  help="The name of the wallet to use for registration.")
        satya_parser.add_argument("--chain.network", type=str, required=False,
                                  help="The network to use for registration.")
        satya_parser.add_argument("--tee_address", type=str, required=False,
                                  help="The hotkey address of the TEE node to register.")
        satya_parser.add_argument("--public_key", type=str, required=False,
                                    help="The public key of the TEE node to register.")

    @staticmethod
    def check_config(config: "vana.Config"):
        if not config.get("url") and not config.no_prompt:
            url = Prompt.ask("Enter the URL to register")
            config.url = url
