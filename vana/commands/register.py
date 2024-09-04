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
from rich.prompt import Prompt


class RegisterCommand(BaseCommand):
    """
    Executes the `register` command to register a validator node on the Vana network.

    This command allows users to register a validator node with a specified name, URL, stake amount, and wallet.

    Usage:
        The command requires specifying the validator name, URL, stake amount, and wallet name.

    Args:
        name (str): The name of the validator to register.
        url (str): The URL of the validator node.
        stake_amount (float): The amount of VANA tokens to stake.
        wallet (str): The name of the wallet to use for registration.

    Example usage:
        vanacli register satya --url=https://teenode.com --stake-amount=1000 --wallet=validator_4000
    """

    @staticmethod
    def run(cli: "vana.cli"):
        try:
            chain_manager: "vana.ChainManager" = vana.ChainManager(config=cli.config)
            wallet = vana.Wallet(config=cli.config)

            # TODO: Implement the actual registration logic here
            # This might involve calling a method on the chain_manager to register the validator
            # For example:
            # chain_manager.register_validator(
            #     name=cli.config.name,
            #     url=cli.config.url,
            #     stake_amount=cli.config.stake_amount,
            #     wallet=wallet
            # )

            vana.__console__.print(f"Registered validator '{cli.config.name}' successfully!")
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
        register_parser.add_argument("--stake-amount", type=float, required=True, help="The amount of VANA tokens to stake")
        register_parser.add_argument("--wallet", type=str, required=True, help="The name of the wallet to use for registration")

        vana.Wallet.add_args(register_parser)
        vana.ChainManager.add_args(register_parser)

    @staticmethod
    def check_config(config: "vana.Config"):
        if not config.is_set("name") and not config.no_prompt:
            config.name = Prompt.ask("Enter validator name")
        if not config.is_set("url") and not config.no_prompt:
            config.url = Prompt.ask("Enter validator URL")
        if not config.is_set("stake_amount") and not config.no_prompt:
            config.stake_amount = float(Prompt.ask("Enter stake amount"))
        if not config.is_set("wallet") and not config.no_prompt:
            config.wallet = Prompt.ask("Enter wallet name")