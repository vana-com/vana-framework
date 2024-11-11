#!/usr/bin/env python3

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
import shtab
import sys
import os
from pathlib import Path
import vana
from importlib.metadata import entry_points
from typing import List, Optional

from .commands import (
    GetWalletHistoryCommand,
    NewColdkeyCommand,
    NewHotkeyCommand,
    RegenColdkeyCommand,
    RegenColdkeypubCommand,
    RegenHotkeyCommand,
    TransferCommand,
    UpdateWalletCommand,
    WalletBalanceCommand,
    WalletCreateCommand,
    ExportPrivateKeyCommand,
    RegisterCommand
)

# Create a console instance for CLI display.
console = vana.__console__

ALIAS_TO_COMMAND = {
    "root": "root",
    "wallet": "wallet",
    "stake": "stake",
    "satya": "satya",
    "r": "root",
    "w": "wallet",
    "st": "stake",
    "roots": "root",
    "wallets": "wallet",
    "stakes": "stake",
    "dlp": "dlp",
    "d": "dlp",
    "i": "info",
    "info": "info",
}
COMMANDS = {
    "root": {
        "name": "root",
        "aliases": ["r", "roots"],
        "help": "Commands for managing and viewing the root network.",
        "commands": {

        },
    },
    "wallet": {
        "name": "wallet",
        "aliases": ["w", "wallets"],
        "help": "Commands for managing and viewing wallets.",
        "commands": {
            "transfer": TransferCommand,
            "balance": WalletBalanceCommand,
            "create": WalletCreateCommand,
            "new_hotkey": NewHotkeyCommand,
            "new_coldkey": NewColdkeyCommand,
            "regen_coldkey": RegenColdkeyCommand,
            "regen_coldkeypub": RegenColdkeypubCommand,
            "regen_hotkey": RegenHotkeyCommand,
            "update": UpdateWalletCommand,
            "history": GetWalletHistoryCommand,
            "export_private_key": ExportPrivateKeyCommand,
        },
    },
    "stake": {
        "name": "stake",
        "aliases": ["st", "stakes"],
        "help": "Commands for staking and removing stake from hotkey accounts.",
        "commands": {

        },
    },
    "dlp": {
        "name": "dlp",
        "aliases": ["d"],
        "help": "DLP-specific commands for DLP management",
        "commands": {

        },
    },
    "info": {
        "name": "info",
        "aliases": ["i"],
        "help": "Instructions for enabling autocompletion for the CLI.",
        "commands": {
        },
    },
    "satya": {
        "name": "satya",
        "aliases": ["s"],
        "help": "Commands for interacting with the Satya protocol.",
        "commands": {
            "register": RegisterCommand,
        },
    },
}


def ensure_local_bin_in_path():
    """Ensures ~/.local/bin is in PATH for the current session"""
    local_bin = str(Path.home() / ".local" / "bin")
    if local_bin not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")


def update_shell_config():
    """Updates shell config to include ~/.local/bin in PATH"""
    local_bin = str(Path.home() / ".local" / "bin")

    # Check if already in PATH
    if local_bin in os.environ.get("PATH", "").split(os.pathsep):
        return

    # Determine shell config file
    shell = os.environ.get("SHELL", "")
    home = str(Path.home())

    if "zsh" in shell:
        rc_file = os.path.join(home, ".zshrc")
    else:  # default to bash
        rc_file = os.path.join(home, ".bashrc")

    if os.path.exists(rc_file):
        with open(rc_file, 'r') as f:
            content = f.read()

        if "PATH=\"$HOME/.local/bin:$PATH\"" not in content:
            with open(rc_file, 'a') as f:
                f.write('\n# Added by vana installation\nexport PATH="$HOME/.local/bin:$PATH"\n')


def load_external_commands():
    """
    Load external commands from entry points.
    Used to extend CLI functionality
    """
    eps = entry_points(group='vanacli.commands')
    COMMANDS["dlp"]["commands"] = {}
    for entry_point in eps:
        try:
            command = entry_point.load()
            COMMANDS["dlp"]["commands"][entry_point.name] = command
        except Exception as e:
            pass


class CLIErrorParser(argparse.ArgumentParser):
    """
    Custom ArgumentParser for better error messages.
    """

    def error(self, message):
        """
        This method is called when an error occurs. It prints a custom error message.
        """
        sys.stderr.write(f"Error: {message}\n")
        self.print_help()
        sys.exit(2)


class cli:
    """
    Implementation of the Command Line Interface (CLI) class for the Vana protocol.
    This class handles operations like key management (hotkey and coldkey) and token transfer.
    """

    def __init__(
            self,
            config: Optional["vana.config"] = None,
            args: Optional[List[str]] = None,
    ):
        """
        Initializes a CLI object.

        Args:
            config (vana.config, optional): The configuration settings for the CLI.
            args (List[str], optional): List of command line arguments.
        """
        # Turns on console for cli.
        # TODO: this is not working, so it has been turned on by default in __init__.py
        vana.turn_console_on()

        # If no config is provided, create a new one from args.
        if config is None:
            config = cli.create_config(args)

        self.config = config
        if self.config.command in ALIAS_TO_COMMAND:
            self.config.command = ALIAS_TO_COMMAND[self.config.command]
        else:
            console.print(
                f":cross_mark:[red]Unknown command: {self.config.command}[/red]"
            )
            sys.exit()

        # Check if the config is valid.
        cli.check_config(self.config)

        # Ensure ~/.local/bin is in PATH
        ensure_local_bin_in_path()

        # If no_version_checking is not set or set as False in the config, version checking is done.
        if not self.config.get("no_version_checking", d=True):
            try:
                vana.utils.version_checking()
            except:
                # If version checking fails, inform user with an exception.
                raise RuntimeError(
                    "To avoid internet-based version checking, pass --no_version_checking while running the CLI."
                )

    @staticmethod
    def __create_parser__() -> "argparse.ArgumentParser":
        """
        Creates the argument parser for the CLI.

        Returns:
            argparse.ArgumentParser: An argument parser object for CLI.
        """
        # Define the basic argument parser.
        parser = CLIErrorParser(
            description=f"vana cli v{vana.__version__}",
            usage="vanacli <command> <command args>",
            add_help=True,
        )
        # Add shtab completion
        parser.add_argument(
            "--print-completion",
            choices=shtab.SUPPORTED_SHELLS,
            help="Print shell tab completion script",
        )
        parser.add_argument(
            "--post-install",
            action="store_true",
            help=argparse.SUPPRESS,  # Hide from help output
        )
        # Add arguments for each sub-command.
        cmd_parsers = parser.add_subparsers(dest="command")
        # Add argument parsers for all available commands.
        for command in COMMANDS.values():
            if isinstance(command, dict):
                subcmd_parser = cmd_parsers.add_parser(
                    name=command["name"],
                    aliases=command["aliases"],
                    help=command["help"],
                )
                subparser = subcmd_parser.add_subparsers(
                    help=command["help"], dest="subcommand", required=True
                )

                for subcommand in command["commands"].values():
                    subcommand.add_args(subparser)
            else:
                command.add_args(cmd_parsers)

        return parser

    @staticmethod
    def create_config(args: List[str]) -> "vana.config":
        """
        From the argument parser, add config to executor and local config

        Args:
            args (List[str]): List of command line arguments.

        Returns:
            config: The configuration object for Vana CLI.
        """
        parser = cli.__create_parser__()

        # If no arguments are passed, print help text and exit the program.
        if len(args) == 0:
            parser.print_help()
            sys.exit()

        return vana.Config(parser, args=args)

    @staticmethod
    def check_config(config: "vana.Config"):
        """
        Checks if the essential configuration exists under different command

        Args:
            config (config): The configuration settings for the CLI.
        """
        # Check if command exists, if so, run the corresponding check_config.
        # If command doesn't exist, inform user and exit the program.
        if config.command in COMMANDS:
            command = config.command
            command_data = COMMANDS[command]

            if isinstance(command_data, dict):
                if config["subcommand"] != None:
                    command_data["commands"][config["subcommand"]].check_config(config)
                else:
                    console.print(
                        f":cross_mark:[red]Missing subcommand for: {config.command}[/red]"
                    )
                    sys.exit(1)
            else:
                command_data.check_config(config)
        else:
            console.print(f":cross_mark:[red]Unknown command: {config.command}[/red]")
            sys.exit(1)

    def run(self):
        """
        Executes the command from the configuration.
        """
        # Check for print-completion argument
        if self.config.print_completion:
            parser = cli.__create_parser__()
            shell = self.config.print_completion
            print(shtab.complete(parser, shell))
            return

        # Check if command exists, if so, run the corresponding method.
        # If command doesn't exist, inform user and exit the program.
        command = self.config.command
        if command in COMMANDS:
            command_data = COMMANDS[command]

            if isinstance(command_data, dict):
                command_data["commands"][self.config["subcommand"]].run(self)
            else:
                command_data.run(self)
        else:
            console.print(
                f":cross_mark:[red]Unknown command: {self.config.command}[/red]"
            )
            sys.exit()


def main():
    load_external_commands()

    # Create the parser with shtab support
    parser = cli.__create_parser__()
    args, unknown = parser.parse_known_args()

    # Handle post-install PATH setup
    if getattr(args, 'post_install', False):
        update_shell_config()
        ensure_local_bin_in_path()
        return

    if args.print_completion:  # Check for print-completion argument
        print(shtab.complete(parser, args.print_completion))
        return

    try:
        cli_instance = cli(args=sys.argv[1:])
        cli_instance.run()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
    except RuntimeError as e:
        print(f'RuntimeError: {e}')


if __name__ == '__main__':
    main()
