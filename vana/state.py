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

import fnmatch
import json
import os
import time
from dataclasses import asdict
from os.path import join
from typing import List, Optional, Set, Dict

import vana


def get_save_dir(network: str, dlp_uid: int) -> str:
    """
    Return directory path of the state file from ``network`` and ``dlp_uid``.
    """
    return os.path.expanduser(
        f"~/.vana/state/network-{str(network)}/dlpuid-{str(dlp_uid)}/"
    )


def latest_block_path(dir_path: str) -> str:
    """
    Get the latest block path from the directory.

    Args:
        dir_path (str): Directory path.

    Returns:
        str: Latest block path.
    """
    latest_block = -1
    latest_file_full_path = None
    for filename in os.listdir(dir_path):
        full_path_filename = os.path.expanduser(join(dir_path, filename))
        try:
            block_number = int(filename.split("-")[1].split(".")[0])
            if block_number > latest_block:
                latest_block = block_number
                latest_file_full_path = full_path_filename
        except Exception as e:
            pass
    if not latest_file_full_path:
        raise ValueError(f"State not found at: {dir_path}")
    else:
        return latest_file_full_path


class State:
    """
    Dynamic representation of the network's state, capturing the interconnectedness and attributes of nodes (participants) in the Vana ecosystem.
    This class is constantly updated and synchronized with the state of the blockchain.
    """

    def __init__(
            self, dlp_uid: int, network: str = "test", lite: bool = True, sync: bool = True
    ):
        self.dlp_uid = dlp_uid
        self.network = network
        self.node_servers: Set[vana.NodeServerInfo] = set()
        self._hotkeys: Set[str] = set()
        self.weights: Dict[str, float] = {}
        self.last_update = 0
        self.block = 0
        if self.can_load_state():
            self.load()

        if sync:
            self.sync(block=None, lite=lite)

    def sync(
            self,
            block: Optional[int] = None,
            lite: bool = True,
            chain_manager: Optional["vana.ChainManager"] = None,
    ):
        """
        Synchronizes the state with the network's current state.
        """
        self.node_servers = chain_manager.get_active_node_servers()
        self.last_update = time.time()
        self.block = chain_manager.get_current_block()

    def set_hotkeys(self, hotkeys: List[str]):
        """
        Set the hotkeys of the state.
        """
        self._hotkeys = hotkeys
        for hotkey in self._hotkeys:
            self.weights.setdefault(hotkey, 0)

    @property
    def addresses(self) -> List[str]:
        """
        Provides a list of IP addresses for each node in the network.
        """
        return [node_server.ip_str() for node_server in self.node_servers]

    def save(self) -> "State":
        """
        Saves the current state to a file on disk.
        """
        save_directory = get_save_dir(self.network, self.dlp_uid)
        os.makedirs(save_directory, exist_ok=True)
        state_file = save_directory + f"/block-{self.block}.json"
        state_dict = {
            "block": self.block,
            "node_servers": [asdict(node_server) for node_server in self.node_servers],
            "hotkeys": list(self._hotkeys),
            "weights": self.weights,
            "last_update": self.last_update,
        }
        with open(state_file, 'w') as f:
            json.dump(state_dict, f)
        return self

    def load(self):
        """
        Loads the state from the default save directory
        """
        dir_path = get_save_dir(self.network, self.dlp_uid)
        state_file = latest_block_path(dir_path)
        with open(state_file, 'r') as f:
            state_dict = json.load(f)
            self.block = state_dict.get("block", 0)
            self.node_servers = state_dict.get("node_servers", [])
            self._hotkeys = state_dict.get("hotkeys", [])
            self.weights = state_dict.get("weights", {})
            self.last_update = state_dict.get("last_update", 0)
        return self

    def can_load_state(self) -> bool:
        """
        Checks if an old state file exists and can be loaded
        """
        dir_path = get_save_dir(self.network, self.dlp_uid)
        if not os.path.isdir(dir_path):
            return False
        for filename in os.listdir(dir_path):
            if fnmatch.fnmatch(filename, 'block-*.json') and os.path.isfile(os.path.join(dir_path, filename)):
                return True
        return False

    def add_weight(self, hotkey: str, weight: float):
        """
        Update the exponential moving average (EMA) weight of a validator with a new data point
        """
        # Calculate the smoothing factor based on the number of periods
        ema_periods = 5
        smoothing_factor = 2 / (ema_periods + 1)

        # Apply the EMA formula to update the average
        previous_ema = self.weights.get(hotkey, 0.0)
        updated_ema = (smoothing_factor * weight) + ((1 - smoothing_factor) * previous_ema)
        self.weights[hotkey] = updated_ema
