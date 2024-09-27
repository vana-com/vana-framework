import json
import os

import requests

import vana
from vana.contracts import contracts


def fetch_and_save_contract_abi(network, contract_name, contract_hash):
    try:
        BASE_URL = f"https://api.{network}.vanascan.io/api/v2/smart-contracts"

        # Get details about the proxy contract
        proxy_response = requests.get(f"{BASE_URL}/{contract_hash}")
        proxy_response.raise_for_status()
        implementation_address = proxy_response.json()["decoded_constructor_args"][0][0]

        # Fetch ABI from the implementation
        implementation_response = requests.get(f"{BASE_URL}/{implementation_address}")
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
    network = os.environ.get("CHAIN_NETWORK", "satori")
    if network not in contracts:
        network = "satori"

    for contract_name, contract_hash in contracts[network].items():
        fetch_and_save_contract_abi(network, contract_name, contract_hash)


if __name__ == "__main__":
    # To update contract ABIs, run
    # poetry run python -m vana.contracts
    update_contract_abis()
