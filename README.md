<div align="center">

# **Vana Network** <!-- omit in toc -->
[![Discord Chat](https://img.shields.io/discord/308323056592486420.svg)](https://discord.gg/xx98TSE8)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

### The first decentralized network for user-owned data <!-- omit in toc -->

[Discord](https://discord.gg/xx98TSE8) • [Network](https://satori.vanascan.io)

</div>

We believe in an open internet where users own their data and the AI models they contribute to.

AI models should be created more like open source software: iteratively by a community. To make this possible, researchers need access to the world's best datasets that are held captive across walled gardens. Users can break down these walled gardens by exporting their own data.

We are building towards a user-owned foundation model, trained by 100M users who contribute their data and compute.

## Getting Started

To get started interacting with Vana:

1. Clone the repository:
```shell
   git clone https://github.com/vana-com/vana-framework.git
```

2. Install the required dependencies using poetry:
```shell
   poetry install
```
3. Configure the environment variables by copying and modifying the `.env.example` file:

4. Run the application:
```shell
poetry run python -m chatgpt.nodes.validator
```

# Wallets

Wallets are the foundational ownership and identity mechanism facilitating all Vana functions. A Vana wallet consists of a coldkey and associated hotkeys. A coldkey can contain multiple hotkeys, but each hotkey belongs to only one coldkey.

Coldkeys securely store funds and handle transfers and staking. Hotkeys are used for online operations, including signing queries and running validators.

```bash
$ poetry run python -m opendata.cli --no_version_checking wallet --help

usage: vanacli <command> <command args> wallet [-h] {balance,create,new_hotkey,new_coldkey,regen_coldkey,regen_coldkeypub,regen_hotkey,update,history} ...

positional arguments:
  {balance,create,new_hotkey,new_coldkey,regen_coldkey,regen_coldkeypub,regen_hotkey,update,history}
                        Commands for managing and viewing wallets.
    balance             Checks the balance of the wallet.
    create              Creates a new coldkey (for managing balance) under the specified path
    new_hotkey          Creates a new hotkey (for running a validator) under the specified path
    new_coldkey         Creates a new coldkey (for containing balance) under the specified path
    regen_coldkey       Regenerates a coldkey from a passed value
    regen_coldkeypub    Regenerates a coldkeypub from the public part of the coldkey
    regen_hotkey        Regenerates a hotkey from a passed mnemonic
    update              Updates the wallet security by replacing ansible vault with NaCl
    history             Fetch transfer history associated with the provided wallet

options:
  -h, --help            show this help message and exit
```

You should be able to view your keys by navigating to ~/.opendata/wallets or viewed by running ```vanacli wallet list```
```bash
$ tree ~/.opendata/
    .opendata/                  # Root directory.
        wallets/                # The folder containing all opendata wallets.
            default/            # The name of your wallet, "default"
                coldkey         # You encrypted coldkey.
                coldkeypub.txt  # Your coldkey public address
                hotkeys/        # The folder containing all of your hotkeys.
                    default     # You unencrypted hotkey information.
```
Your default wallet ```Wallet (default, default, ~/.opendata/wallets/)``` is used unless you specify otherwise. 
Make sure to store your mnemonic phrase safely. If you lose your password, or access to the machine where the wallet is stored, you can regenerate the coldkey using the mnemonic phrase.
```bash
$ poetry run python -m opendata.cli --no_version_checking wallet regen_coldkey --mnemonic **** *** **** **** ***** **** *** **** **** **** ***** *****
```

## Using the cli
The Opendata command line interface (`opendata.cli`) is the primary command line tool for interacting with the Vana network. It allows you to deploy nodes, manage wallets, stake/unstake, nominate, transfer tokens, and more. 

This is a first python implementation. We welcome new implementations in other languages.

### Basic Usage

To list all available commands:

```bash
poetry run python -m opendata.cli --help

usage: vanacli <command> <command args>

vana cli v0.0.1

positional arguments:
  {root,r,roots,wallet,w,wallets,stake,st,stakes,sudo,su,sudos,info,i}
    root (r, roots)     Commands for managing and viewing the root network.
    wallet (w, wallets)
                        Commands for managing and viewing wallets.
    stake (st, stakes)  Commands for staking and removing stake from hotkey accounts.
    sudo (su, sudos)    Commands for DLP management
    info (i)            Instructions for enabling autocompletion for the CLI.

options:
  -h, --help            show this help message and exit
  --print-completion {bash,zsh,tcsh}
                         Print shell tab completion script
```
## License
The MIT License (MIT)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
