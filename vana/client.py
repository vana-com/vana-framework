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
            parser.add_argument(
                "--" + prefix_str + "client.compute_engine_contract_address",
                default=os.getenv("COMPUTE_ENGINE_CONTRACT_ADDRESS") or None,
                type=str,
                help="""The address for the Compute Engine Contract.""")
            parser.add_argument(
                "--" + prefix_str + "client.query_engine_contract_address",
                default=os.getenv("QUERY_ENGINE_CONTRACT_ADDRESS") or None,
                type=str,
                help="""The address for the Query Engine Contract.""")
            parser.add_argument(
                "--" + prefix_str + "client.compute_instruction_registry_contract_address",
                default=os.getenv("COMPUTE_INSTRUCTION_REGISTRY_CONTRACT_ADDRESS") or None,
                type=str,
                help="""The address for the Compute Instruction Registry Contract.""")
            parser.add_argument(
                "--" + prefix_str + "client.data_refiner_registry_contract_address",
                default=os.getenv("DATA_REFINER_REGISTRY_CONTRACT_ADDRESS") or None,
                type=str,
                help="""The address for the Data Refiner Registry Contract.""")
            parser.add_argument(
                "--" + prefix_str + "client.compute_engine_tee_pool_contract_address",
                default=os.getenv("COMPUTE_ENGINE_TEE_POOL_CONTRACT_ADDRESS") or None,
                type=str,
                help="""The address for the Compute Engine TEE Pool (ie. ephemeral-standard, ...) Contract.""")
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

        data_refiner_registry_contract_path = os.path.join(
            os.path.dirname(__file__),
            "contracts/DataRefinerRegistry.json"
        )
        with open(data_refiner_registry_contract_path) as f:
            data_refiner_address = contracts[self.network]["DataRefinerRegistry"]
            if hasattr(self.config, 'client') and self.config.client is not None:
                data_refiner_address = self.config.client.data_refiner_registry_contract_address or data_refiner_address

            self.data_refiner_contract = self.chain_manager.web3.eth.contract(
                address=data_refiner_address,
                abi=json.load(f)
            )
        query_engine_contract_path = os.path.join(
            os.path.dirname(__file__),
            "contracts/QueryEngine.json"
        )
        with open(query_engine_contract_path) as f:
            query_engine_address = contracts[self.network]["QueryEngine"]
            if hasattr(self.config, 'client') and self.config.client is not None:
                query_engine_address = self.config.client.query_engine_contract_address or query_engine_address

            self.query_engine_contract = self.chain_manager.web3.eth.contract(
                address=query_engine_address,
                abi=json.load(f)
            )

        compute_engine_contract_path = os.path.join(
            os.path.dirname(__file__),
            "contracts/ComputeEngine.json"
        )
        with open(compute_engine_contract_path) as f:
            compute_engine_address = contracts[self.network]["ComputeEngine"]
            if hasattr(self.config, 'client') and self.config.client is not None:
                compute_engine_address = self.config.client.compute_engine_contract_address or compute_engine_address

            self.compute_engine_contract = self.chain_manager.web3.eth.contract(
                address=compute_engine_address,
                abi=json.load(f)
            )
        
        compute_instruction_registry_contract_path = os.path.join(
            os.path.dirname(__file__),
            "contracts/ComputeInstructionRegistry.json"
        )
        with open(compute_instruction_registry_contract_path) as f:
            compute_instruction_registry_address = contracts[self.network]["ComputeInstructionRegistry"]
            if hasattr(self.config, 'client') and self.config.client is not None:
                compute_instruction_registry_address = self.config.client.compute_instruction_registry_contract_address or compute_instruction_registry_address

            self.compute_instruction_registry_contract = self.chain_manager.web3.eth.contract(
                address=compute_instruction_registry_address,
                abi=json.load(f)
            )
        
        compute_engine_tee_pool_contract_path = os.path.join(
            os.path.dirname(__file__),
            "contracts/ComputeEngineTeePool.json"
        )
        with open(compute_engine_tee_pool_contract_path) as f:
            compute_engine_tee_pool_address = contracts[self.network]["ComputeEngineTeePool"]
            if hasattr(self.config, 'client') and self.config.client is not None:
                compute_engine_tee_pool_address = self.config.client.compute_engine_tee_pool_contract_address or compute_engine_tee_pool_address

            self.compute_engine_tee_pool_contract = self.chain_manager.web3.eth.contract(
                address=compute_engine_tee_pool_address,
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

    def add_refinement_with_permission(self, file_id: int, refiner_id: int, url: str, account: str, key: str):
        """
        Add a refinement to the Data Registry contract.
        :param file_id: File ID in the Data Registry contract to add a refinement to
        :param refiner_id: Refiner ID from the Data Refiner Registry, where refinement instructions are stored
        :param url: URL where encrypted refinement is uploaded
        :param account: Address of the account to grant permission to the refinement
        :param key: The encrypted encryption key that only the account can decrypt
        :return: Transaction hex, Transaction receipt
        """
        add_refinement_with_permission_fn = self.data_registry_contract.functions.addRefinementWithPermission(file_id, refiner_id, url, account, key)
        return self.chain_manager.send_transaction(add_refinement_with_permission_fn, self.wallet.hotkey)

    # Data Refiner Registry

    def get_refiner(self, refiner_id: int):
        """
        Get the refiner information for a given refiner ID
        :param refiner_id: Refiner ID from the Data Refiner Registry
        :return: Refiner information
        """
        get_refiner_fn = self.data_refiner_contract.functions.refiners(refiner_id)
        refiner = self.chain_manager.read_contract_fn(get_refiner_fn)
        keys = ["dlp_id", "owner", "name", "schema_definition_url", "refinement_instruction_url", "public_key"]
        return dict(zip(keys, refiner))

    # Query Engine

    def get_dlp_pub_key(self, dlp_id: int) -> Optional[str]:
        """
        Get the public key for a given DLP ID
        :param dlp_id: DLP ID from the Query Engine
        :return: Public key, or None if the DLP is not found
        """
        try:
            get_dlp_pub_key_fn = self.query_engine_contract.functions.dlpPubKeys(dlp_id)
            pub_key = self.chain_manager.read_contract_fn(get_dlp_pub_key_fn)
            return pub_key
        except Exception as e:
            vana.logging.error(f"Error getting DLP public key: {str(e)}")
            return None

    # Compute Engine

    def get_job(self, job_id: int):
        """
        Get the compute job information for a given job ID
        :param job_id: Compute job ID from the Compute Engine
        :return: Job information
        """
        get_job_fn = self.compute_engine_contract.functions.jobs(job_id)
        job = self.chain_manager.read_contract_fn(get_job_fn)
        keys = ["owner_address", "max_timeout", "gpu_required", "status", "tee_address", "compute_instruction_id", "added_timestamp", "status_message", "tee_pool_address"]
        return dict(zip(keys, job))
    
    def update_job_status(self, job_id: int, status: int, status_message: Optional[str] = ""):
        """
        Update the compute job status in the Compute Engine contract.
        :param job_id: Job ID for status update
        :param job_status: New job status
        :param status_message: Optional message for relevant status (ie. error details, ...)
        :return: Transaction hex, Transaction receipt
        """
        update_status_fn = self.compute_engine_contract.functions.updateJobStatus(job_id, status, status_message)
        return self.chain_manager.send_transaction(update_status_fn, self.wallet.hotkey)

    # Compute Instructions Registry

    def get_compute_instruction(self, instruction_id: int):
        """
        Get the compute instruction information for a given instruction ID
        :param instruction_id: Compute instruction ID from the Compute Instructions Registry contract
        :return: Compute instruction information
        """
        get_instruction_fn = self.compute_instruction_registry_contract.functions.instructions(instruction_id)
        instruction = self.chain_manager.read_contract_fn(get_instruction_fn)
        keys = ["hash", "owner", "url"]
        return dict(zip(keys, instruction))

    def is_instruction_approved(self, instruction_id: int, dlp_id: int):
        """
        Get the compute instruction approval information for a given dlp ID from the Compute Instructions Registry contract
        :param instruction_id: Compute instruction ID from the Compute Instructions Registry contract
        :param dlp_id: DLP ID that the instruction might be approved for
        :return: DLP approval (True / False)
        """
        get_approval_fn = self.compute_instruction_registry_contract.functions.isApproved(instruction_id, dlp_id)
        is_approved = self.chain_manager.read_contract_fn(get_approval_fn)
        if is_approved is None:
            return False
        return is_approved
    
    def add_compute_instruction(self, instruction_hash: bytes, url: str):
        """
        Writes a new compute instruction to the Compute Instructions Registry contract
        :param instruction_hash: The SHA256 checksum hash of the instruction image archive (as bytes)
        :param url: Publicly accessible download URL of the instruction image archive (.tar.gz)
        :return: Transaction hex, Transaction receipt
        """
        add_instruction_fn = self.compute_engine_contract.functions.addComputeInstruction(instruction_hash, url)
        return self.chain_manager.send_transaction(add_instruction_fn, self.wallet.hotkey)
    

    def update_compute_instruction(self, instruction_id: int, dlp_id: int, approved: bool):
        """
        Update DLP approval of a compute instruction in the Compute Instructions Registry contract
        :param instruction_id: The SHA256 checksum hash of the instruction image archive (as bytes)
        :param dlp_id: The DLP ID to update compute instruction execution approval for.
        :param approved: Approval (True / False) of whether the instruction is allowed to be executed on the provided DLP's data.
        :return: Transaction hex, Transaction receipt
        """
        update_instruction_fn = self.compute_engine_contract.functions.updateComputeInstruction(instruction_id, dlp_id, approved)
        return self.chain_manager.send_transaction(update_instruction_fn, self.wallet.hotkey)

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
    
    # Compute Engine TEE Pool

    def get_compute_engine_tee(self, address: str):
        """
        Get the TEE information for a registered compute engine TEE in the configured Compute Engine TEE Pool contract
        :param address: Address (hotkey) of TEE
        :return: Transaction hex, Transaction receipt
        """
        get_tee_fn = self.compute_engine_tee_pool_contract.functions.tees(address)
        tee = self.chain_manager.read_contract_fn(get_tee_fn)
        if tee is None:
            return None
        keys = ["tee_address", "url", "status", "jobs_count", "public_key"]
        return dict(zip(keys, tee))
