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

from typing import Union

from eth_abi import decode
from web3 import Web3
from web3.types import ABI


def decode_custom_error(contract_abi: ABI, error_data: Union[str, bytes]) -> str:
    """
    Decodes a custom contract error using the contract ABI.

    Parameters:
    contract_abi (ABI): The ABI of the contract containing error definitions.
    error_data (Union[str, bytes]): The error data returned from a contract call. This can be a hex string or bytes.

    Returns:
    str: A human-readable string representing the decoded error message, or "Unknown error" if the error cannot be decoded.
    """
    if isinstance(error_data, str):
        error_data = Web3.to_bytes(hexstr=error_data)

    # Extract the error signature (first 4 bytes of the error data)
    error_sig = error_data[:4].hex()

    for item in contract_abi:
        if item['type'] == 'error':
            # Construct the full error signature from the ABI definition
            inputs = ','.join(input['type'] for input in item['inputs'])
            full_signature = f"{item['name']}({inputs})"
            calculated_sig = Web3.keccak(text=full_signature)[:4].hex()

            # Compare and match the calculated signature with the error signature from the data
            if calculated_sig[2:] == error_sig:
                error_abi = item
                error_args = error_data[4:]
                error_decoded = decode([input['type'] for input in error_abi['inputs']], error_args)
                error_message = f"{error_abi['name']}({', '.join(map(str, error_decoded))})"
                return error_message

    return f"Unknown error({error_data})"


def as_wad(num: float = 0) -> int:
    """
    Convert a number to its equivalent in wei.
    :param num:
    :return:
    """
    return int(num * 1e18)


def from_wad(num: int = 0) -> float:
    """
    Convert a number from wei to its equivalent.
    :param num:
    :return:
    """
    return num / 1e18
