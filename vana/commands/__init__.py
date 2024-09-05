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

from munch import Munch, munchify

defaults: Munch = munchify(
    {
        "chain": {"network": "vana", "chain_endpoint": None, "_mock": False},
        "priority": {"max_workers": 5, "maxsize": 10},
        "wallet": {
            "name": "default",
            "hotkey": "default",
            "path": "~/.vana/wallets/",
        },
        "logging": {
            "debug": False,
            "trace": False,
            "record_log": False,
            "logging_dir": "~/.vana/miners",
        },
    }
)

from .wallets import (
    NewColdkeyCommand,
    NewHotkeyCommand,
    RegenColdkeyCommand,
    RegenColdkeypubCommand,
    RegenHotkeyCommand,
    UpdateWalletCommand,
    WalletCreateCommand,
    WalletBalanceCommand,
    GetWalletHistoryCommand,
    ExportPrivateKeyCommand,
)
from .transfer import TransferCommand
from .satya import RegisterCommand
