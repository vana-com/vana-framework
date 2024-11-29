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

from typing import Union, Optional

from eth_keys import keys
from eth_utils import decode_hex
from web3 import Web3


def is_valid_secp256k1_pubkey(public_key: Union[str, bytes]) -> bool:
    """
    Checks if the given public_key is a valid Ethereum secp256k1 key.

    Args:
        public_key (Union[str, bytes]): The public_key to check.

    Returns:
        bool: True if the public_key is a valid secp256k1 key, False otherwise.
    """
    try:
        if isinstance(public_key, str):
            if public_key.startswith("0x04") and len(public_key) == 130:
                public_key = public_key[2:]
            elif len(public_key) != 128:
                return False
            public_key_bytes = decode_hex(public_key)
        elif isinstance(public_key, bytes):
            if len(public_key) != 64:
                return False
            public_key_bytes = public_key
        else:
            return False

        # Attempt to create a public key object
        keys.PublicKey(public_key_bytes)
        return True

    except (ValueError, TypeError):
        return False


def is_valid_vana_address_or_public_key(address: Union[str, bytes]) -> bool:
    """
    Checks if the given address is a valid Ethereum address or public key.

    Args:
        address (Union[str, bytes]): The address to check.

    Returns:
        bool: True if the address is a valid Ethereum address or public key, False otherwise.
    """
    if isinstance(address, str):
        return Web3.is_address(address) or is_valid_secp256k1_pubkey(address)
    elif isinstance(address, bytes):
        return is_valid_secp256k1_pubkey(address)
    return False


def create_identity_dict(
        display: str = "",
        legal: str = "",
        web: str = "",
        riot: str = "",
        email: str = "",
        pgp_fingerprint: Optional[str] = None,
        image: str = "",
        info: str = "",
        twitter: str = "",
) -> dict:
    """
    Creates a dictionary with structure for identity extrinsic. Must fit within 64 bits.

    Args:
    display (str): String to be converted and stored under 'display'.
    legal (str): String to be converted and stored under 'legal'.
    web (str): String to be converted and stored under 'web'.
    riot (str): String to be converted and stored under 'riot'.
    email (str): String to be converted and stored under 'email'.
    pgp_fingerprint (str): String to be converted and stored under 'pgp_fingerprint'.
    image (str): String to be converted and stored under 'image'.
    info (str): String to be converted and stored under 'info'.
    twitter (str): String to be converted and stored under 'twitter'.

    Returns:
    dict: A dictionary with the specified structure and byte string conversions.

    Raises:
    ValueError: If pgp_fingerprint is not exactly 20 bytes long when encoded.
    """
    if pgp_fingerprint and len(pgp_fingerprint.encode()) != 20:
        raise ValueError("pgp_fingerprint must be exactly 20 bytes long when encoded")

    return {
        "info": {
            "additional": [[]],
            "display": {f"Raw{len(display.encode())}": display.encode()},
            "legal": {f"Raw{len(legal.encode())}": legal.encode()},
            "web": {f"Raw{len(web.encode())}": web.encode()},
            "riot": {f"Raw{len(riot.encode())}": riot.encode()},
            "email": {f"Raw{len(email.encode())}": email.encode()},
            "pgp_fingerprint": pgp_fingerprint.encode() if pgp_fingerprint else None,
            "image": {f"Raw{len(image.encode())}": image.encode()},
            "info": {f"Raw{len(info.encode())}": info.encode()},
            "twitter": {f"Raw{len(twitter.encode())}": twitter.encode()},
        }
    }


def decode_hex_identity_dict(info_dictionary):
    for key, value in info_dictionary.items():
        if isinstance(value, dict):
            item = list(value.values())[0]
            if isinstance(item, str) and item.startswith("0x"):
                try:
                    info_dictionary[key] = bytes.fromhex(item[2:]).decode()
                except UnicodeDecodeError:
                    print(f"Could not decode: {key}: {item}")
            else:
                info_dictionary[key] = item
    return info_dictionary
