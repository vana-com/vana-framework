import argparse
import vana
from vana.commands.base_command import BaseCommand
from rich.prompt import Prompt, Confirm
from web3 import Web3


class SatyaRegisterCommand(BaseCommand):
    """
    Executes the `satya register` command to register a validator node on the Vana network.

    This command allows users to register a validator node with a specified name, URL, and wallet.
    It interacts with the TeePoolImplementation smart contract to add the validator as a TEE.

    Usage:
        The command requires specifying the validator name, URL, and wallet name.

    Args:
        name (str): The name of the validator to register.
        url (str): The URL of the validator node.
        wallet (str): The name of the wallet to use for registration.

    Example usage:
        vanacli satya register mynode --url=https://teenode.com --wallet=validator_4000
    """

    @staticmethod
    def run(cli: "vana.cli"):
        try:
            chain_manager: "vana.ChainManager" = vana.ChainManager(config=cli.config)
            wallet = vana.Wallet(config=cli.config)

            # Contract details
            contract_address = vana.__satori_tee_pool_contract_address
            contract_abi = [
                {
                    "inputs": [
                        {"internalType": "address", "name": "teeAddress", "type": "address"},
                        {"internalType": "string", "name": "url", "type": "string"}
                    ],
                    "name": "addTee",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]  # This is a simplified ABI, you may need to provide the full ABI

            # Create contract instance
            contract = chain_manager.web3.eth.contract(address=contract_address, abi=contract_abi)

            # Prepare function call
            function_call = contract.functions.addTee(wallet.hotkey.address, cli.config.url)

            # Send transaction using chain_manager
            tx_hash, tx_receipt = chain_manager.send_transaction(
                function=function_call,
                account=wallet.hotkey
            )

            if tx_receipt and tx_receipt['status'] == 1:
                vana.__console__.print(f"[bold green]Successfully registered validator '{cli.config.name}' with URL '{cli.config.url}'[/bold green]")
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
        parser.add_argument("name", type=str, help="The name of the validator to register")
        parser.add_argument("--url", type=str, required=True, help="The URL of the validator node")
        parser.add_argument("--wallet", type=str, required=True, help="The name of the wallet to use for registration")

        vana.Wallet.add_args(parser)
        vana.ChainManager.add_args(parser)

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


class SatyaCommand(BaseCommand):
    """
    Handles 'satya' related commands for the Vana CLI.
    """

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        satya_parser = parser.add_parser("satya", help="Satya-related commands")
        subparsers = satya_parser.add_subparsers(dest="satya_command", required=True)

        # Register command
        register_parser = subparsers.add_parser("register", help="Register a validator node on the Vana network")
        SatyaRegisterCommand.add_args(register_parser)

        # More Satya-related commands can be added here in the future
        # For example:
        # deregister_parser = subparsers.add_parser("deregister", help="Deregister a validator node from the Vana network")
        # SatyaDeregisterCommand.add_args(deregister_parser), etc.

    @staticmethod
    def check_config(config: "vana.Config"):
        if config.satya_command == "register":
            SatyaRegisterCommand.check_config(config)

    @staticmethod
    def run(cli: "vana.cli"):
        if cli.config.satya_command == "register":
            SatyaRegisterCommand.run(cli)