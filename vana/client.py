import argparse
import copy
import json
import os
import vana
from typing import Optional
from vana.chain_data import Proof, ProofData
from vana.contracts import contracts
from vana.utils.web3 import as_wad


class Client:
    @staticmethod
    def config() -> "config":
        parser = argparse.ArgumentParser()
        vana.Client.add_args(parser)
        return vana.Config(parser, args=[])

    @classmethod
    def add_args(cls, parser: argparse.ArgumentParser, prefix: Optional[str] = None):
        prefix_str = "" if prefix is None else f"{prefix}."
        try:
            parser.add_argument(
                "--" + prefix_str + "client.tee_pool_contract_address",
                default=os.getenv("TEE_POOL_CONTRACT_ADDRESS") or None,
                type=str,
                help="""The address for the TEE Pool Contract.""")
            parser.add_argument(
                "--" + prefix_str + "client.data_registry_contract_address",
                default=os.getenv("DATA_REGISTRY_CONTRACT_ADDRESS") or None,
                type=str,
                help="""The address for the Data Registry Contract.""")
            parser.add_argument(
                "--" + prefix_str + "client.dlp_root_contract_address",
                default=os.getenv("DLP_ROOT_CONTRACT_ADDRESS") or None,
                type=str,
                help="""The address for the DLP Root Contract.""")
        except argparse.ArgumentError:
            # re-parsing arguments.
            pass

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
            data_registry_address = contracts[self.network]["DataRegistry"]
            if hasattr(self.config, 'client') and self.config.client is not None:
                data_registry_address = self.config.client.data_registry_contract_address or data_registry_address

            self.data_registry_contract = self.chain_manager.web3.eth.contract(
                address=data_registry_address,
                abi=json.load(f)
            )

        tee_pool_contract_path = os.path.join(
            os.path.dirname(__file__),
            "contracts/TeePool.json"
        )
        with open(tee_pool_contract_path) as f:
            tee_pool_address = contracts[self.network]["TeePool"]
            if hasattr(self.config, 'client') and self.config.client is not None:
                tee_pool_address = self.config.client.tee_pool_contract_address or tee_pool_address

            self.tee_pool_contract = self.chain_manager.web3.eth.contract(
                address=tee_pool_address,
                abi=json.load(f)
            )

    # Data Registry

    def get_file(self, file_id: int):
        """
        Retrieve a file from the Data Registry contract
        :param file_id:
        :return: File<id, ownerAddress, url, addedAtBlock>
        """
        get_file_fn = self.data_registry_contract.functions.files(file_id)
        file = self.chain_manager.read_contract_fn(get_file_fn)
        if file is None:
            return None
        (id, ownerAddress, url, addedAtBlock) = file
        if ownerAddress == "0x0000000000000000000000000000000000000000":
            return None
        return file

    def get_file_permissions(self, file_id: int, account: str) -> str:
        """
        Get the permissions for a specific account on a file.

        :param file_id: ID of the file
        :param account: Address of the account to check permissions for
        :return: The encryption key for the account, or an empty string if no permissions
        """
        get_permissions_fn = self.data_registry_contract.functions.filePermissions(file_id, account)
        permissions = self.chain_manager.read_contract_fn(get_permissions_fn)
        return permissions

    def add_file(self, url: str, integrity_hash: Optional[str] = None):
        """
        Add a file to the Data Registry contract.
        :param url: URL where encrypted file is uploaded
        :param integrity_hash: Optional ETAG, last-modified, or other hash to verify file integrity
        :return: Transaction hex, Transaction receipt
        """
        add_file_fn = self.data_registry_contract.functions.addFile(url)
        return self.chain_manager.send_transaction(add_file_fn, self.wallet.hotkey)

    # TEE Pool Contract

    def get_tee(self, address: str):
        """
        Get the TEE information for a registered TEE
        :param address: Address (hotkey) of TEE
        :return: Transaction hex, Transaction receipt
        """
        get_tee_fn = self.tee_pool_contract.functions.tees(address)
        tee = self.chain_manager.read_contract_fn(get_tee_fn)
        if tee is None:
            return None
        (teeAddress, url, status, amount, withdrawnAmount, jobsCount, publicKey) = tee
        if url == "":
            return None
        return tee

    def register_tee(self, url: str, public_key: str, tee_address: str):
        """
        Register a TEE compute node with the TEE Pool contract.
        @param url: URL where the TEE is reachable
        @param public_key: Public key of the TEE node
        @param tee_address: Address of the TEE to register. If not provided, uses the wallet's hotkey address.
        @return: Transaction hex, Transaction receipt
        """
        register_fn = self.tee_pool_contract.functions.addTee(tee_address, url, public_key)
        return self.chain_manager.send_transaction(register_fn, self.wallet.hotkey)

    def add_proof(self, proof_data: ProofData, file_id: int | None = None, job_id: int | None = None):
        """
        Add a proof for a job to the Data Registry contract.

        :param file_id: Look up a file by File ID from the Data Registry contract
        :param job_id: Look up a file by the Job ID from the TEE Pool contract
        :param proof_data: A dictionary containing the proof data
        :return: Transaction hex, Transaction receipt
        """
        if (job_id is None) == (file_id is None):
            raise ValueError("One of job_id or file_id must be provided, but not both")

        signed_proof = Proof(data=proof_data).sign(self.wallet)
        proof_tuple = (
            signed_proof.signature,
            (
                as_wad(signed_proof.data.score),
                signed_proof.data.dlp_id,
                signed_proof.data.metadata,
                signed_proof.data.proof_url,
                signed_proof.data.instruction,
            )
        )

        if file_id is not None:
            add_proof_fn = self.data_registry_contract.functions.addProof(file_id, proof_tuple)
        else:
            add_proof_fn = self.tee_pool_contract.functions.addProof(job_id, proof_tuple)
        return self.chain_manager.send_transaction(
            function=add_proof_fn,
            account=self.wallet.hotkey,
            value=0,
            max_retries=3,
            base_gas_multiplier=1.5
        )

    def claim(self):
        """
        Claim any rewards for TEE validators for completed jobs
        :return: Transaction hex, Transaction receipt
        """
        claim_fn = self.tee_pool_contract.functions.claim()
        return self.chain_manager.send_transaction(claim_fn, self.wallet.hotkey)

    def get_jobs_count(self) -> int:
        """
        Get the total number of jobs from the TEE Pool contract

        Returns:
            int: Total number of jobs in the queue
        """
        try:
            # Call the TEE Pool contract's jobCount method
            job_count_fn = self.tee_pool_contract.functions.jobsCount()
            job_count = self.chain_manager.read_contract_fn(job_count_fn)
            return job_count
        except Exception as e:
            vana.logging.error(f"Error getting job count: {str(e)}")
            # Return 0 if unable to get count to avoid breaking progress calculation
            return 0
