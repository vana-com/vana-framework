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
import copy
import os
from typing import Optional, Union, Tuple, Dict, overload

from eth_account import Account
from eth_account.signers.local import (
    LocalAccount,
)
from eth_keys.datatypes import PublicKey

from rich.panel import Panel

import vana
from vana.utils.wallet_utils import is_valid_vana_address_or_public_key


def display_private_key_msg(private_key: str, key_type: str):
    """
    Display the private key and a warning message about its sensitivity.

    Args:
        private_key (str): The private key to display.
        key_type (str): Type of the key (coldkey or hotkey).
    """
    vana.__console__.print(Panel.fit(
        f"[bold green]Your {key_type} private key:[/bold green]\n\n"
        f"[yellow]{private_key}[/yellow]\n\n"
        "[bold red]IMPORTANT:[/bold red] Store this private key in a secure (preferably offline) place.\n"
        "Anyone with this private key has full control over the associated account.\n\n"
        f"You can use this private key to import your {key_type} into other wallets.\n"
        "The command to regenerate the key using this private key is:\n"
        f"[cyan]vanacli w regen_{key_type} --seed {private_key}[/cyan]"
    ))

def display_mnemonic_msg(mnemonic: str, key_type: str):
    """
    Display the mnemonic and a warning message to keep the mnemonic safe.

    Args:
        mnemonic (str): Mnemonic string.
        key_type (str): Type of the key (coldkey or hotkey).
    """
    vana.__console__.print(Panel.fit(
        f"[bold green]Your {key_type} mnemonic phrase:[/bold green]\n\n"
        f"[yellow]{mnemonic}[/yellow]\n\n"
        "[bold red]IMPORTANT:[/bold red] Store this mnemonic in a secure (preferably offline) place.\n"
        "Anyone with this mnemonic can regenerate the key and access your tokens.\n\n"
        f"You can use this mnemonic to recreate the {key_type} in case it gets lost.\n"
        "The command to regenerate the key using this mnemonic is:\n"
        f"[cyan]vanacli w regen_{key_type} --mnemonic {mnemonic}[/cyan]"
    ))


class Wallet:
    """
    The wallet class in the handles wallet functionality needed for participating in the Vana network.

    It manages two types of keys: coldkey and hotkey, each serving different purposes in network operations.
    Each wallet contains a coldkey and a hotkey.

    The coldkey is the user's primary key for holding stake in their wallet and is the only way that users
    can access VANA. Coldkeys can hold tokens and should be encrypted on your device.

    The coldkey is the primary key used for securing the wallet's stake in the Vana network and
    is critical for financial transactions like staking and unstaking tokens. It's recommended to keep the
    coldkey encrypted and secure, as it holds the actual tokens.

    The hotkey, in contrast, is used for operational tasks like subscribing to and setting weights in the
    network. It's linked to the coldkey through the metagraph and does not directly hold tokens, thereby
    offering a safer way to interact with the network during regular operations.

    Args:
        name (str): The name of the wallet, used to identify it among possibly multiple wallets.
        path (str): File system path where wallet keys are stored.
        hotkey_str (str): String identifier for the hotkey.
        _hotkey, _coldkey, _coldkeypub (LocalAccount): Internal representations of the hotkey and coldkey.

    Methods:
        create_if_non_existent, create, recreate: Methods to handle the creation of wallet keys.
        get_coldkey, get_hotkey, get_coldkeypub: Methods to retrieve specific keys.
        set_coldkey, set_hotkey, set_coldkeypub: Methods to set or update keys.
        hotkey_file, coldkey_file, coldkeypub_file: Properties that return respective key file objects.
        regenerate_coldkey, regenerate_hotkey, regenerate_coldkeypub: Methods to regenerate keys from different sources.
        config, help, add_args: Utility methods for configuration and assistance.

    Example Usage::

        # Create a new wallet with default coldkey and hotkey names
        my_wallet = wallet()

        # Access hotkey and coldkey
        hotkey = my_wallet.get_hotkey()
        coldkey = my_wallet.get_coldkey()

        # Set a new coldkey
        my_wallet.create_new_coldkey(n_words=24) # number of seed words to use

        # Update wallet hotkey
        my_wallet.set_hotkey(new_hotkey)

        # Print wallet details
        print(my_wallet)

        # Access coldkey property, must use password to unlock
        my_wallet.coldkey
    """

    @classmethod
    def config(cls) -> "vana.Config":
        """
        Get config from the argument parser.

        Returns:
            Config: Config object.
        """
        parser = argparse.ArgumentParser()
        cls.add_args(parser)
        return vana.Config(parser, args=[])

    @classmethod
    def help(cls):
        """
        Print help to stdout.
        """
        parser = argparse.ArgumentParser()
        cls.add_args(parser)
        print(cls.__new__.__doc__)
        parser.print_help()

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser, prefix: str = None):
        """
        Accept specific arguments from parser.

        Args:
            parser (argparse.ArgumentParser): Argument parser object.
            prefix (str): Argument prefix.
        """
        prefix_str = "" if prefix is None else prefix + "."
        try:
            default_name = os.getenv("WALLET_NAME") or "default"
            default_hotkey = os.getenv("WALLET_NAME") or "default"
            default_path = os.getenv("WALLET_PATH") or "~/.vana/wallets/"
            parser.add_argument(
                "--no_prompt",
                dest="no_prompt",
                action="store_true",
                help="""Set true to avoid prompting the user.""",
                default=False,
            )
            parser.add_argument(
                "--" + prefix_str + "wallet.name",
                required=False,
                default=default_name,
                help="The name of the wallet to unlock for running vana "
                     "(name mock is reserved for mocking this wallet)",
            )
            parser.add_argument(
                "--" + prefix_str + "wallet.hotkey",
                required=False,
                default=default_hotkey,
                help="The name of the wallet's hotkey.",
            )
            parser.add_argument(
                "--" + prefix_str + "wallet.path",
                required=False,
                default=default_path,
                help="The path to your vana wallets",
            )
        except argparse.ArgumentError as e:
            pass

    def __init__(
            self,
            name: str = None,
            hotkey: str = None,
            path: str = None,
            config: "vana.Config" = None,
    ):
        r"""
        Initialize the vana wallet object containing a hot and coldkey.

        Args:
            name (str, optional): The name of the wallet to unlock for running vana. Defaults to ``default``.
            hotkey (str, optional): The name of hotkey used to running the miner. Defaults to ``default``.
            path (str, optional): The path to your vana wallets. Defaults to ``~/.vana/wallets/``.
            config (Config, optional): Wallet.config(). Defaults to ``None``.
        """
        # Fill config from passed args using command line defaults.
        if config is None:
            config = Wallet.config()
        self.config = copy.deepcopy(config)
        self.config.wallet.name = name or self.config.wallet.get(
            "name", vana.defaults.wallet.name
        )
        self.config.wallet.hotkey = hotkey or self.config.wallet.get(
            "hotkey", vana.defaults.wallet.hotkey
        )
        self.config.wallet.path = path or self.config.wallet.get(
            "path", vana.defaults.wallet.path
        )

        self.name = self.config.wallet.name
        self.path = self.config.wallet.path
        self.hotkey_str = self.config.wallet.hotkey

        self._hotkey = None
        self._coldkey = None
        self._coldkeypub = None
        self._mnemonics = {}

        # Create necessary directories
        self._create_wallet_directories()

        # Check for and handle environment variable based wallet initialization
        self._init_from_environment()

    def _create_wallet_directories(self):
        """Create the necessary wallet directory structure if it doesn't exist."""
        # Create main wallet directory
        wallet_path = os.path.expanduser(os.path.join(self.path, self.name))
        # Create hotkeys directory
        hotkeys_path = os.path.join(wallet_path, "hotkeys")

        # Create directories if they don't exist
        os.makedirs(hotkeys_path, exist_ok=True)

    def _init_from_environment(self):
        """
        Initialize wallet components from environment variables if they exist.
        Currently supports hotkey initialization from HOTKEY_MNEMONIC.
        Creates the wallet files on disk without password protection.
        """
        hotkey_mnemonic = os.getenv("HOTKEY_MNEMONIC")
        if hotkey_mnemonic:
            try:
                vana.logging.info("Found HOTKEY_MNEMONIC environment variable. Initializing hotkey...")

                # Enable mnemonic features
                Account.enable_unaudited_hdwallet_features()

                # Create account from mnemonic
                account = Account.from_mnemonic(hotkey_mnemonic)

                # Create the hotkey file
                wallet_path = os.path.expanduser(os.path.join(self.path, self.name))
                hotkey_path = os.path.join(wallet_path, "hotkeys", self.hotkey_str)

                # Create the keyfile
                keyfile = vana.keyfile(path=hotkey_path)

                # Set the hotkey without password protection
                keyfile.set_keypair(
                    keypair=account,
                    encrypt=False,  # No encryption for environment-based keys
                    overwrite=True  # Always overwrite when using environment variables
                )

                # Update the wallet's hotkey reference
                self._hotkey = account

                vana.logging.success(
                    f"Successfully initialized hotkey from environment variable and created file at {hotkey_path}"
                )

            except Exception as e:
                vana.logging.error(f"Failed to initialize hotkey from environment variable: {str(e)}")
                # Don't raise the exception - allow fallback to normal initialization
                pass

    def __str__(self):
        """
        Returns the string representation of the Wallet object.

        Returns:
            str: The string representation.
        """
        return "wallet({}, {}, {})".format(self.name, self.hotkey_str, self.path)

    def __repr__(self):
        """
        Returns the string representation of the wallet object.

        Returns:
            str: The string representation.
        """
        return self.__str__()

    def create_if_non_existent(
            self, coldkey_use_password: bool = True, hotkey_use_password: bool = False
    ) -> "Wallet":
        """
        Checks for existing coldkeypub and hotkeys, and creates them if non-existent.

        Args:
            coldkey_use_password (bool, optional): Whether to use a password for coldkey. Defaults to ``True``.
            hotkey_use_password (bool, optional): Whether to use a password for hotkey. Defaults to ``False``.

        Returns:
            wallet: The wallet object.
        """
        return self.create(coldkey_use_password, hotkey_use_password)

    def create(
            self, coldkey_use_password: bool = True, hotkey_use_password: bool = False
    ) -> "Wallet":
        """
        Checks for existing coldkeypub and hotkeys, and creates them if non-existent.

        Args:
            coldkey_use_password (bool, optional): Whether to use a password for coldkey. Defaults to ``True``.
            hotkey_use_password (bool, optional): Whether to use a password for hotkey. Defaults to ``False``.

        Returns:
            wallet: The wallet object.
        """
        # ---- Setup Wallet. ----
        if (
                not self.coldkey_file.exists_on_device()
                and not self.coldkeypub_file.exists_on_device()
        ):
            self.create_new_coldkey(n_words=12, use_password=coldkey_use_password)
        if not self.hotkey_file.exists_on_device():
            self.create_new_hotkey(n_words=12, use_password=hotkey_use_password)
        return self

    def recreate(
            self, coldkey_use_password: bool = True, hotkey_use_password: bool = False
    ) -> "Wallet":
        """
        Checks for existing coldkeypub and hotkeys and creates them if non-existent.

        Args:
            coldkey_use_password (bool, optional): Whether to use a password for coldkey. Defaults to ``True``.
            hotkey_use_password (bool, optional): Whether to use a password for hotkey. Defaults to ``False``.

        Returns:
            wallet: The wallet object.
        """
        self.create_new_coldkey(n_words=12, use_password=coldkey_use_password)
        self.create_new_hotkey(n_words=12, use_password=hotkey_use_password)
        return self

    @property
    def hotkey_file(self) -> "vana.keyfile":
        """
        Property that returns the hotkey file.

        Returns:
            keyfile: The hotkey file.
        """
        wallet_path = os.path.expanduser(os.path.join(self.path, self.name))
        hotkey_path = os.path.join(wallet_path, "hotkeys", self.hotkey_str)
        return vana.keyfile(path=hotkey_path)

    @property
    def coldkey_file(self) -> "vana.keyfile":
        """
        Property that returns the coldkey file.

        Returns:
            keyfile: The coldkey file.
        """
        wallet_path = os.path.expanduser(os.path.join(self.path, self.name))
        coldkey_path = os.path.join(wallet_path, "coldkey")
        return vana.keyfile(path=coldkey_path)

    @property
    def coldkeypub_file(self) -> "vana.keyfile":
        """
        Property that returns the coldkeypub file.

        Returns:
            keyfile: The coldkeypub file.
        """
        wallet_path = os.path.expanduser(os.path.join(self.path, self.name))
        coldkeypub_path = os.path.join(wallet_path, "coldkeypub.txt")
        return vana.keyfile(path=coldkeypub_path)

    def set_hotkey(
            self,
            account: LocalAccount,
            encrypt: bool = False,
            overwrite: bool = False,
    ) -> "vana.keyfile":
        """
        Sets the hotkey for the wallet.

        Args:
            account (LocalAccount): The hotkey account.
            encrypt (bool, optional): Whether to encrypt the hotkey. Defaults to ``False``.
            overwrite (bool, optional): Whether to overwrite an existing hotkey. Defaults to ``False``.

        Returns:
            keyfile: The hotkey file.
        """
        self._hotkey = account
        self.hotkey_file.set_keypair(account, encrypt=encrypt, overwrite=overwrite)
        return self.hotkey_file

    def set_coldkeypub(
            self,
            account: LocalAccount,
            encrypt: bool = False,
            overwrite: bool = False,
    ) -> "vana.keyfile":
        """
        Sets the coldkeypub for the wallet.

        Args:
            account (LocalAccount): The coldkeypub account.
            encrypt (bool, optional): Whether to encrypt the coldkeypub. Defaults to ``False``.
            overwrite (bool, optional): Whether to overwrite an existing coldkeypub. Defaults to ``False``.

        Returns:
            keyfile: The coldkeypub file.
        """
        self._coldkeypub = account._key_obj.public_key
        self.coldkeypub_file.set_keypair(
            self._coldkeypub, encrypt=encrypt, overwrite=overwrite
        )
        return self.coldkeypub_file

    def set_coldkey(
            self,
            account: LocalAccount,
            encrypt: bool = True,
            overwrite: bool = False,
    ) -> "vana.keyfile":
        """
        Sets the coldkey for the wallet.

        Args:
            account (LocalAccount): The coldkey account.
            encrypt (bool, optional): Whether to encrypt the coldkey. Defaults to ``True``.
            overwrite (bool, optional): Whether to overwrite an existing coldkey. Defaults to ``False``.

        Returns:
            keyfile: The coldkey file.
        """
        self._coldkey = account
        self.coldkey_file.set_keypair(
            self._coldkey, encrypt=encrypt, overwrite=overwrite
        )
        return self.coldkey_file

    def get_coldkey(self, password: str = None) -> LocalAccount:
        """
        Gets the coldkey from the wallet.

        Args:
            password (str, optional): The password to decrypt the coldkey. Defaults to ``None``.

        Returns:
            LocalAccount: The coldkey account.
        """
        return self.coldkey_file.get_keypair(password=password)

    def get_hotkey(self, password: str = None) -> LocalAccount:
        """
        Gets the hotkey from the wallet.

        Args:
            password (str, optional): The password to decrypt the hotkey. Defaults to ``None``.

        Returns:
            LocalAccount: The hotkey account.
        """
        return self.hotkey_file.get_keypair(password=password)

    def get_hotkey_public_key(self) -> str:
        """
        Gets the public key of the hotkey as a hexadecimal string.

        Returns:
            str: The public key of the hotkey in hexadecimal format.

        Raises:
            AttributeError: If the hotkey is not set.
        """
        if self._hotkey is None:
            self._hotkey = self.hotkey_file.keypair

        if self._hotkey is None:
            raise AttributeError("Hotkey is not set. Please ensure the hotkey is properly initialized.")

        # Get the public key as bytes
        public_key_bytes = self._hotkey._key_obj.public_key.to_bytes()

        # Convert the bytes to a hexadecimal string
        return '0x' + public_key_bytes.hex()

    def get_coldkeypub(self, password: str = None) -> PublicKey:
        """
        Gets the coldkeypub from the wallet.

        Args:
            password (str, optional): The password to decrypt the coldkeypub. Defaults to ``None``.

        Returns:
            LocalAccount: The coldkeypub account.
        """
        return self.coldkeypub_file.get_keypair(password=password)

    @property
    def hotkey(self) -> LocalAccount:
        r"""Loads the hotkey from wallet.path/wallet.name/hotkeys/wallet.hotkey or raises an error.

        Returns:
            hotkey (LocalAccount):
                hotkey loaded from config arguments.
        Raises:
            KeyFileError: Raised if the file is corrupt of non-existent.
            CryptoKeyError: Raised if the user enters an incorrect password for an encrypted keyfile.
        """
        if self._hotkey is None:
            self._hotkey = self.hotkey_file.keypair
        return self._hotkey

    @property
    def coldkey(self) -> LocalAccount:
        r"""Loads the hotkey from wallet.path/wallet.name/coldkey or raises an error.

        Returns:
            coldkey (LocalAccount): coldkey loaded from config arguments.
        Raises:
            KeyFileError: Raised if the file is corrupt of non-existent.
            CryptoKeyError: Raised if the user enters an incorrect password for an encrypted keyfile.
        """
        if self._coldkey is None:
            self._coldkey = self.coldkey_file.keypair
        return self._coldkey

    @property
    def coldkeypub(self) -> PublicKey:
        r"""Loads the coldkeypub from wallet.path/wallet.name/coldkeypub.txt or raises an error.

        Returns:
            coldkeypub (LocalAccount): coldkeypub loaded from config arguments.
        Raises:
            KeyFileError: Raised if the file is corrupt of non-existent.
            CryptoKeyError: Raised if the user enters an incorrect password for an encrypted keyfile.
        """
        if self._coldkeypub is None:
            self._coldkeypub = self.coldkeypub_file.keypair
        return self._coldkeypub

    @property
    def coldkeypub_str(self) -> str | None:
        """
        Returns the coldkeypub address as a string based on its type
        """
        if str(type(self.coldkeypub)) == "<class 'eth_account.signers.local.LocalAccount'>":
            return self.coldkeypub.address
        if str(type(self.coldkeypub)) == "<class 'eth_keys.datatypes.PublicKey'>":
            return str(self.coldkeypub)
        return None

    def create_new_coldkey(
            self,
            n_words: int = 12,
            use_password: bool = True,
            overwrite: bool = False,
            suppress: bool = False,
    ) -> "Wallet":
        """Creates a new coldkey, optionally encrypts it with the user-provided password and saves to disk.

        Args:
            n_words: (int, optional):
                Number of mnemonic words to use.
            use_password (bool, optional):
                Is the created key password protected.
            overwrite (bool, optional):
                Determines if this operation overwrites the coldkey under the same path ``<wallet path>/<wallet name>/coldkey``.
        Returns:
            wallet (Wallet):
                This object with newly created coldkey.
        """
        Account.enable_unaudited_hdwallet_features()
        account, mnemonic = Account.create_with_mnemonic()
        if not suppress:
            display_mnemonic_msg(mnemonic, "coldkey")
        self._mnemonics["coldkey"] = mnemonic
        self.set_coldkey(account, encrypt=use_password, overwrite=overwrite)
        self.set_coldkeypub(account, overwrite=overwrite)
        return self

    def new_hotkey(
            self,
            n_words: int = 12,
            use_password: bool = False,
            overwrite: bool = False,
            suppress: bool = False,
    ) -> "Wallet":
        """Creates a new hotkey, optionally encrypts it with the user-provided password and saves to disk.

        Args:
            n_words: (int, optional):
                Number of mnemonic words to use.
            use_password (bool, optional):
                Is the created key password protected.
            overwrite (bool, optional):
                Determines if this operation overwrites the hotkey under the same path ``<wallet path>/<wallet name>/hotkeys/<hotkey>``.
        Returns:
            wallet (Wallet):
                This object with newly created hotkey.
        """
        return self.create_new_hotkey(n_words, use_password, overwrite, suppress)

    def create_new_hotkey(
            self,
            n_words: int = 12,
            use_password: bool = False,
            overwrite: bool = False,
            suppress: bool = False,
    ) -> "Wallet":
        """Creates a new hotkey, optionally encrypts it with the user-provided password and saves to disk.

        Args:
            n_words: (int, optional):
                Number of mnemonic words to use.
            use_password (bool, optional):
                Is the created key password protected.
            overwrite (bool, optional):
                Will this operation overwrite the hotkey under the same path <wallet path>/<wallet name>/hotkeys/<hotkey>
        Returns:
            wallet (Wallet):
                This object with newly created hotkey.
        """
        Account.enable_unaudited_hdwallet_features()
        account, mnemonic = Account.create_with_mnemonic()
        if not suppress:
            display_mnemonic_msg(mnemonic, "hotkey")
        self._mnemonics["hotkey"] = mnemonic
        self.set_hotkey(account, encrypt=use_password, overwrite=overwrite)
        return self

    def regenerate_coldkeypub(
            self,
            h160_address: Optional[str] = None,
            public_key: Optional[Union[str, bytes]] = None,
            overwrite: bool = False,
            suppress: bool = False,
    ) -> "Wallet":
        """Regenerates the coldkeypub from the passed ``h160_address`` or public_key and saves the file. Requires either ``h160_address`` or public_key to be passed.

        Args:
            h160_address: (str, optional):
                Address as ``h160`` string.
            public_key: (str | bytes, optional):
                Public key as hex string or bytes.
            overwrite (bool, optional) (default: False):
                Determines if this operation overwrites the coldkeypub (if exists) under the same path ``<wallet path>/<wallet name>/coldkeypub``.
        Returns:
            wallet (Wallet):
                Newly re-generated wallet with coldkeypub.

        """
        if h160_address is None and public_key is None:
            raise ValueError("Either h160_address or public_key must be passed")

        if not is_valid_vana_address_or_public_key(
                h160_address if h160_address is not None else public_key
        ):
            raise ValueError(
                f"Invalid {'h160_address' if h160_address is not None else 'public_key'}"
            )

        if h160_address is not None:
            account = Account.from_key(h160_address)
        else:
            account = Account.from_key(public_key)

        # No need to encrypt the public key
        self.set_coldkeypub(account, overwrite=overwrite)

        return self

    # Short name for regenerate_coldkeypub
    regen_coldkeypub = regenerate_coldkeypub

    @overload
    def regenerate_coldkey(
            self,
            mnemonic: Optional[Union[list, str]] = None,
            use_password: bool = True,
            overwrite: bool = False,
            suppress: bool = False,
    ) -> "Wallet":
        ...

    @overload
    def regenerate_coldkey(
            self,
            seed: Optional[str] = None,
            use_password: bool = True,
            overwrite: bool = False,
            suppress: bool = False,
    ) -> "Wallet":
        ...

    @overload
    def regenerate_coldkey(
            self,
            json: Optional[Tuple[Union[str, Dict], str]] = None,
            use_password: bool = True,
            overwrite: bool = False,
            suppress: bool = False,
    ) -> "Wallet":
        ...

    def regenerate_coldkey(
            self,
            use_password: bool = True,
            overwrite: bool = False,
            suppress: bool = False,
            **kwargs,
    ) -> "Wallet":
        """Regenerates the coldkey from the passed mnemonic or seed, or JSON encrypts it with the user's password and saves the file.

        Args:
            mnemonic: (Union[list, str], optional):
                Key mnemonic as list of words or string space separated words.
            seed: (str, optional):
                Seed as hex string.
            json: (Tuple[Union[str, Dict], str], optional):
                Restore from encrypted JSON backup as ``(json_data: Union[str, Dict], passphrase: str)``.
            use_password (bool, optional):
                Is the created key password protected.
            overwrite (bool, optional):
                Determines if this operation overwrites the coldkey under the same path ``<wallet path>/<wallet name>/coldkey``.
        Returns:
            wallet (Wallet):
                This object with newly created coldkey.

        Note:
            Uses priority order: ``mnemonic > seed > json``.

        """
        if len(kwargs) == 0:
            raise ValueError("Must pass either mnemonic, seed, or json")

        # Get from kwargs
        mnemonic = kwargs.get("mnemonic", None)
        seed = kwargs.get("seed", None)
        json = kwargs.get("json", None)

        Account.enable_unaudited_hdwallet_features()

        if mnemonic is None and seed is None and json is None:
            raise ValueError("Must pass either mnemonic, seed, or json")
        if mnemonic is not None:
            if isinstance(mnemonic, str):
                mnemonic = mnemonic.split()
            # TODO: only support EVM-compatible lengths
            if len(mnemonic) not in [12, 15, 18, 21, 24]:
                raise ValueError(
                    "Mnemonic has invalid size. This should be 12,15,18,21 or 24 words"
                )
            account = Account.from_mnemonic(" ".join(mnemonic))
            if not suppress:
                display_mnemonic_msg(" ".join(mnemonic), "coldkey")
        elif seed is not None:
            account = Account.from_key(seed)
        else:
            # json is not None
            if (
                    not isinstance(json, tuple)
                    or len(json) != 2
                    or not isinstance(json[0], (str, dict))
                    or not isinstance(json[1], str)
            ):
                raise ValueError(
                    "json must be a tuple of (json_data: str | Dict, passphrase: str)"
                )

            json_data, passphrase = json
            account = Account.decrypt(json_data, passphrase)

        self.set_coldkey(account, encrypt=use_password, overwrite=overwrite)
        self.set_coldkeypub(account, overwrite=overwrite)
        return self

    # Short name for regenerate_coldkey
    regen_coldkey = regenerate_coldkey

    @overload
    def regenerate_hotkey(
            self,
            mnemonic: Optional[Union[list, str]] = None,
            use_password: bool = False,
            overwrite: bool = False,
            suppress: bool = False,
    ) -> "Wallet":
        ...

    @overload
    def regenerate_hotkey(
            self,
            seed: Optional[str] = None,
            use_password: bool = False,
            overwrite: bool = False,
            suppress: bool = False,
    ) -> "Wallet":
        ...

    @overload
    def regenerate_hotkey(
            self,
            json: Optional[Tuple[Union[str, Dict], str]] = None,
            use_password: bool = False,
            overwrite: bool = False,
            suppress: bool = False,
    ) -> "Wallet":
        ...

    def regenerate_hotkey(
            self,
            use_password: bool = False,
            overwrite: bool = False,
            suppress: bool = False,
            **kwargs,
    ) -> "Wallet":
        """Regenerates the hotkey from the passed mnemonic or seed, or JSON encrypts it with the user's password and saves the file.

        Args:
            mnemonic: (Union[list, str], optional):
                Key mnemonic as list of words or string space separated words.
            seed: (str, optional):
                Seed as hex string.
            json: (Tuple[Union[str, Dict], str], optional):
                Restore from encrypted JSON backup as ``(json_data: Union[str, Dict], passphrase: str)``.
            use_password (bool, optional):
                Is the created key password protected.
            overwrite (bool, optional):
                Determines if this operation overwrites the hotkey under the same path ``<wallet path>/<wallet name>/hotkeys/<hotkey>``.
        Returns:
            wallet (Wallet):
                This object with newly created hotkey.

        """
        if len(kwargs) == 0:
            raise ValueError("Must pass either mnemonic, seed, or json")

        # Get from kwargs
        mnemonic = kwargs.get("mnemonic", None)
        seed = kwargs.get("seed", None)
        json = kwargs.get("json", None)

        Account.enable_unaudited_hdwallet_features()

        if mnemonic is None and seed is None and json is None:
            raise ValueError("Must pass either mnemonic, seed, or json")

        if mnemonic is not None:
            if isinstance(mnemonic, str):
                mnemonic = mnemonic.split()
            # TODO: only support EVM-compatible lengths
            if len(mnemonic) not in [12, 15, 18, 21, 24]:
                raise ValueError(
                    "Mnemonic has invalid size. This should be 12,15,18,21 or 24 words"
                )
            account = Account.from_mnemonic(" ".join(mnemonic))
            if not suppress:
                display_mnemonic_msg(" ".join(mnemonic), "hotkey")
        elif seed is not None:
            account = Account.from_key(seed)
        else:
            # json is not None
            if (
                    not isinstance(json, tuple)
                    or len(json) != 2
                    or not isinstance(json[0], (str, dict))
                    or not isinstance(json[1], str)
            ):
                raise ValueError(
                    "json must be a tuple of (json_data: str | Dict, passphrase: str)"
                )

            json_data, passphrase = json
            account = Account.decrypt(json_data, passphrase)

        self.set_hotkey(account, encrypt=use_password, overwrite=overwrite)
        return self

    # Short name for regenerate_hotkey
    regen_hotkey = regenerate_hotkey
