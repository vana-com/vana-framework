import json
import os

import requests
from web3 import Web3

import vana
from vana.contracts import contracts


def fetch_and_save_contract_abi(network, contract_name, contract_hash):
    try:
        base_url = f"https://api.{network}.vanascan.io/api/v2/smart-contracts"
        rpc_url = f"https://rpc.{network}.vana.org"

        # Connect to the network
        w3 = Web3(Web3.HTTPProvider(rpc_url))

        # ERC1967 implementation slot
        implementation_slot = '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'

        # Get the implementation address
        implementation_address = w3.eth.get_storage_at(contract_hash, implementation_slot)
        # If address is 0x0000...0000, it means the contract is not a proxy, use its address as implementation address
        implementation_address = '0x' + implementation_address.hex()[-40:] if implementation_address != b'\x00' * 32 else contract_hash

        # Fetch ABI from the implementation
        implementation_response = requests.get(f"{base_url}/{implementation_address}")
        implementation_response.raise_for_status()

        # Extract the ABI from the response
        abi = implementation_response.json().get('abi')
        if not abi:
            vana.logging.error(f"No ABI found for contract {contract_name} with hash {contract_hash}")
            return

        output_file = os.path.join(os.path.dirname(__file__), f"{contract_name}.json")
        with open(output_file, 'w') as f:
            json.dump(abi, f, indent=2)

        vana.logging.info(f"Successfully saved ABI for contract {contract_name} to {output_file}")

    except requests.RequestException as e:
        vana.logging.error(f"Error fetching ABI for contract {contract_name} with hash {contract_hash}: {e}")
    except Exception as e:
        vana.logging.error(f"Unexpected error: {e}")


def update_contract_abis():
    network = os.environ.get("CHAIN_NETWORK", "moksha")
    if network not in contracts:
        network = "satori"

    for contract_name, contract_hash in contracts[network].items():
        fetch_and_save_contract_abi(network, contract_name, contract_hash)


if __name__ == "__main__":
    # To update contract ABIs, run
    # poetry run python -m vana.contracts
    update_contract_abis()
