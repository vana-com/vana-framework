import json
import os

import requests

import vana
from vana.contracts import contracts


def fetch_and_save_contract_abi(network, contract_name, contract_hash):
    try:
        # Determine VanaScan API base URLs based on network
        if network == "vana":
            api_base_url = "https://vanascan.io/api/v2"
        else:
            api_base_url = f"https://api.{network}.vanascan.io/api/v2"

        # Fetch contract details to find implementation address if it's a proxy
        address_response = requests.get(f"{api_base_url}/addresses/{contract_hash}")
        address_response.raise_for_status()
        address_data = address_response.json()

        address_to_fetch_abi_from = contract_hash # Default to original hash
        implementations = address_data.get('implementations')
        if address_data.get('is_contract') and implementations and isinstance(implementations, list) and len(implementations) > 0:
            # It's a proxy, use the first implementation address
            implementation_address = implementations[0].get('address')
            if implementation_address:
                address_to_fetch_abi_from = implementation_address
                vana.logging.info(f"Proxy detected. Using implementation address: {implementation_address}")
            else:
                 vana.logging.warning(f"Proxy detected but no implementation address found in response for {contract_hash}. Using original address.")
        else:
             vana.logging.info(f"Contract {contract_hash} is not a proxy or implementation not found. Using original address.")

        # Fetch ABI from the implementation or original address
        abi_response = requests.get(f"{api_base_url}/smart-contracts/{address_to_fetch_abi_from}")
        abi_response.raise_for_status()

        # Extract the ABI from the response
        abi = abi_response.json().get('abi')
        if not abi:
            vana.logging.error(f"No ABI found for contract {contract_name} (hash: {contract_hash}, fetched from: {address_to_fetch_abi_from})")
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
        network = "vana"

    for contract_name, contract_hash in contracts[network].items():
        fetch_and_save_contract_abi(network, contract_name, contract_hash)


if __name__ == "__main__":
    # To update contract ABIs, run
    # poetry run python -m vana.contracts
    update_contract_abis()
