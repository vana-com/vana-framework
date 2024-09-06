import argparse
import copy
import json
import os
from typing import Optional

import vana
from vana.contracts import contracts


class Client:
    @staticmethod
    def config() -> "config":
        parser = argparse.ArgumentParser()
        vana.ChainManager.add_args(parser)
        return vana.Config(parser, args=[])

    def __init__(self, config: vana.Config):
        if config is None:
            config = self.config()
        self.config = copy.deepcopy(config)

        self.wallet = vana.Wallet(config=self.config)
        self.chain_manager = vana.ChainManager(config=self.config)
        self.network = self.config.chain.network

        # Load contracts
        data_registry_contract_path = os.path.join(
            os.path.dirname(__file__),
            "contracts/DataRegistry.json"
        )
        with open(data_registry_contract_path) as f:
            self.data_registry_contract = self.chain_manager.web3.eth.contract(
                address=contracts[self.network]["DataRegistry"],
                abi=json.load(f)
            )
        tee_pool_contract_path = os.path.join(
            os.path.dirname(__file__),
            "contracts/TeePool.json"
        )
        with open(tee_pool_contract_path) as f:
            self.tee_pool_contract = self.chain_manager.web3.eth.contract(
                address=contracts[self.network]["TeePool"],
                abi=json.load(f)
            )

    # Data Registry

    def get_file(self, file_id: int):
        get_file_fn = self.data_registry_contract.functions.files(file_id)
        file = self.chain_manager.read_contract_fn(get_file_fn)
        (id, ownerAddress, url, addedAtBlock) = file
        if ownerAddress == "0x0000000000000000000000000000000000000000":
            return None
        return file

    def add_file(self, url: str, integrity_hash: Optional[str] = None):
        add_file_fn = self.data_registry_contract.functions.addFile(url)
        return self.chain_manager.send_transaction(add_file_fn, self.wallet.hotkey)

    # TEE Pool Contract

    def register_tee(self, url: str):
        register_fn = self.tee_pool_contract.functions.addTee(self.wallet.hotkey.address, url)
        return self.chain_manager.send_transaction(register_fn, self.wallet.hotkey)
