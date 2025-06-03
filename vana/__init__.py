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

__version__ = "0.47.0"

import rich

from .config import Config

version_split = __version__.split(".")
__version_as_int__: int = (
        (100 * int(version_split[0]))
        + (10 * int(version_split[1]))
        + (1 * int(version_split[2]))
)

# Rich console.
__console__ = rich.get_console()
__use_console__ = True


def turn_console_off():
    global __use_console__
    global __console__
    from io import StringIO

    __use_console__ = False
    rich.reconfigure(file=StringIO(), stderr=False)


def turn_console_on():
    global __use_console__
    global __console__
    __use_console__ = True
    __console__ = rich.get_console()


# TODO: turn_console_on() isn't working so this is commented out for now.
# turn_console_off()

from .errors import (
    BlacklistedException,
    ChainConnectionError,
    ChainError,
    ChainQueryError,
    ChainTransactionError,
    IdentityError,
    InternalServerError,
    InvalidRequestNameError,
    KeyFileError,
    MetadataError,
    NominationError,
    NotDelegateError,
    NotRegisteredError,
    NotVerifiedException,
    PostProcessException,
    PriorityException,
    RegistrationError,
    RunException,
    StakeError,
    TransferError,
    UnstakeError,
)
from .keyfile import (
    serialized_keypair_to_keyfile_data,
    deserialize_keypair_from_keyfile_data,
    validate_password,
    ask_password_to_encrypt,
    keyfile_data_is_encrypted_nacl,
    keyfile_data_is_encrypted_ansible,
    keyfile_data_is_encrypted_legacy,
    keyfile_data_is_encrypted,
    keyfile_data_encryption_method,
    legacy_encrypt_keyfile_data,
    encrypt_keyfile_data,
    get_coldkey_password_from_environment,
    decrypt_keyfile_data,
    keyfile,
    Mockkeyfile,
)
from .wallet import Wallet
from .utils import (
    hash,
    wallet_utils,
)
from .chain_data import (
    NodeServerInfo
)
from .chain_manager import ChainManager
from .cli import cli as cli, COMMANDS as ALL_COMMANDS
from .logging import logging
from .state import State
from .message import Message, TerminalInfo
from .node_server import NodeServer
from .node_client import NodeClient
from .client import Client


# Logging helpers.
def trace(on: bool = True):
    logging.set_trace(on)


def debug(on: bool = True):
    logging.set_debug(on)


__networks__ = ["vana", "islander", "maya", "satori", "moksha", "local", "test", "archive"]

__vana_entrypoint__ = "https://rpc.vana.org"

__islander_entrypoint__ = "https://rpc.islander.vana.org"

__maya_entrypoint__ = "https://rpc.maya.vana.org"

__satori_entrypoint__ = "https://rpc.satori.vana.org"

__moksha_entrypoint__ = "https://rpc.moksha.vana.org"

__archive_entrypoint__ = "wss://archive.vana.org:443"

__local_entrypoint__ = "ws://127.0.0.1:9944"

block_explorer_tx_templates = {
    "vana": "https://vanascan.io/tx/{}",
    "moksha": "https://moksha.vanascan.io/tx/{}",
    "satori": "https://satori.vanascan.io/tx/{}",
    "islander": "https://islander.vanascan.io/tx/{}",
    "maya": "https://maya.vanascan.io/tx/{}",
}

configs = [
    NodeServer.config(),
    Wallet.config(),
    ChainManager.config(),
    logging.get_config(),
]
defaults = Config.merge_all(configs)

banner = r"""_/\\\________/\\\_____/\\\\\\\\\_____/\\\\\_____/\\\_____/\\\\\\\\\\\___
_\/\\\_______\/\\\___/\\\\\\\\\\\\\__\/\\\\\\___\/\\\___/\\\\\\\\\\\\\__
_\//\\\______/\\\___/\\\/////////\\\_\/\\\/\\\__\/\\\__/\\\/////////\\\_
__\//\\\____/\\\___\/\\\_______\/\\\_\/\\\//\\\_\/\\\_\/\\\_______\/\\\_
___\//\\\__/\\\____\/\\\\\\\\\\\\\\\_\/\\\\//\\\\/\\\_\/\\\\\\\\\\\\\\\_
____\//\\\/\\\_____\/\\\/////////\\\_\/\\\_\//\\\/\\\_\/\\\/////////\\\_
_____\//\\\\\______\/\\\_______\/\\\_\/\\\__\//\\\\\\_\/\\\_______\/\\\_
______\//\\\_______\/\\\_______\/\\\_\/\\\___\//\\\\\_\/\\\_______\/\\\_
_______\///________\///________\///__\///_____\/////__\///________\///__
"""

import sys
import os


def is_cli_context():
    """
    Determine if the current context is a CLI invocation by checking how the script is being executed.
    """
    if sys.argv[0] == '-c':
        return True

    main_module = sys.modules.get('__main__')
    if main_module:
        module_name = getattr(main_module, '__name__', '')
        file_name = os.path.basename(getattr(main_module, '__file__', ''))
        return 'cli' in module_name.lower() or 'cli' in file_name.lower()

    return False


if not is_cli_context():
    print(banner)
