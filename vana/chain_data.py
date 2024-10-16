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

import json
from dataclasses import dataclass, asdict
from typing import Optional

from eth_account.messages import encode_defunct
from pydantic import BaseModel
from web3 import Web3

import vana
from vana.utils import networking
from vana.utils.web3 import as_wad


@dataclass
class NodeServerInfo:
    version: int
    ip: str
    port: int
    ip_type: int
    hotkey: str
    coldkey: str

    @property
    def is_serving(self) -> bool:
        """True if the endpoint is serving."""
        if self.ip == "0.0.0.0":
            return False
        else:
            return True

    def ip_str(self) -> str:
        """Return the whole IP as string"""
        return networking.ip__str__(self.ip_type, self.ip, self.port)

    def __eq__(self, other: "NodeServerInfo"):
        if other == None:
            return False
        if (
                self.version == other.version
                and self.ip == other.ip
                and self.port == other.port
                and self.ip_type == other.ip_type
                and self.coldkey == other.coldkey
                and self.hotkey == other.hotkey
        ):
            return True
        else:
            return False

    def __str__(self):
        return "NodeServerInfo( {}, {}, {}, {} )".format(
            str(self.ip_str()), str(self.hotkey), str(self.coldkey), self.version
        )

    def __hash__(self):
        return hash((self.version, self.ip, self.port, self.ip_type, self.hotkey, self.coldkey))

    def __repr__(self):
        return self.__str__()

    def to_string(self) -> str:
        """Converts the NodeServerInfo object to a string representation using JSON."""
        try:
            return json.dumps(asdict(self))
        except (TypeError, ValueError) as e:
            vana.logging.error(f"Error converting NodeServerInfo to string: {e}")
            return NodeServerInfo(0, "", 0, 0, "", "").to_string()

    @classmethod
    def from_string(cls, s: str) -> "NodeServerInfo":
        """Creates an NodeServerInfo object from its string representation using JSON."""
        try:
            data = json.loads(s)
            return cls(**data)
        except json.JSONDecodeError as e:
            vana.logging.error(f"Error decoding JSON: {e}")
        except TypeError as e:
            vana.logging.error(f"Type error: {e}")
        except ValueError as e:
            vana.logging.error(f"Value error: {e}")
        return NodeServerInfo(0, "", 0, 0, "", "")


class ProofData(BaseModel):
    file_url: str
    score: float
    dlp_id: int
    metadata: Optional[str] = ""
    proof_url: Optional[str] = ""
    instruction: str


class Proof(BaseModel):
    signature: Optional[str] = ""
    data: ProofData

    def sign(self, wallet):
        packed_data = Web3().solidity_keccak(
            ['string', 'uint256', 'uint256', 'string', 'string', 'string'],
            [
                self.data.file_url,
                as_wad(self.data.score),
                self.data.dlp_id,
                self.data.metadata,
                self.data.proof_url,
                self.data.instruction
            ]
        )

        message = encode_defunct(packed_data)
        self.signature = wallet.hotkey.sign_message(message).signature.hex()
        return self
