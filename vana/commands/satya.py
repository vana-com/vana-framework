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
from rich.prompt import Prompt
import vana
from vana.commands.base_command import BaseCommand


class SatyaCommand(BaseCommand):
    """
    Implements the 'satya register' command for the Vana CLI.
    """

    @staticmethod
    def run(cli: "vana.cli"):
        """Register a URL with the Satya protocol."""
        url = cli.config.satya.url
        vana.__console__.print(f"Registering URL with Satya: [bold]{url}[/bold]")
        # TODO: Implement actual registration logic

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        satya_parser = parser.add_parser(
            "register", help="Register a URL with the Satya protocol."
        )
        satya_parser.add_argument("--url", type=str, required=False, help="The URL to register.")

    @staticmethod
    def check_config(config: "vana.Config"):
        if not config.get("satya"):
            config.satya = vana.Config()
        if not config.satya.get("url") and not config.no_prompt:
            url = Prompt.ask("Enter the URL to register")
            config.satya.url = url