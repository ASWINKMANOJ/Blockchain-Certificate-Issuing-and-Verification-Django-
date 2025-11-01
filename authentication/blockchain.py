import json
import os
from web3 import Web3
from django.conf import settings

# ---------------------------------------------------------
# ✅ Connect to Ganache
# ---------------------------------------------------------
GANACHE_RPC = "http://127.0.0.1:7545"
w3 = Web3(Web3.HTTPProvider(GANACHE_RPC))
print("✅ Connected to Ganache:", w3.is_connected())

if not w3.is_connected():
    raise Exception("❌ Ganache not connected. Start Ganache GUI.")


# ---------------------------------------------------------
# ✅ Load Truffle contract JSON
# ---------------------------------------------------------
CONTRACT_JSON_PATH = os.path.join(
    settings.BASE_DIR,
    "contract",
    "build",
    "contracts",
    "CertificateVerification.json"   # ✅ EXACT FILE NAME FROM TRUFFLE
)

with open(CONTRACT_JSON_PATH) as f:
    contract_json = json.load(f)

abi = contract_json["abi"]


# ---------------------------------------------------------
# ✅ Extract deployed contract address from networks
# ---------------------------------------------------------
def get_contract_address():
    networks = contract_json.get("networks", {})
    if len(networks) == 0:
        raise Exception("❌ No networks found in Truffle JSON. Did you deploy with Truffle?")

    first_network = list(networks.values())[0]
    return first_network["address"]


CONTRACT_ADDRESS = get_contract_address()


# ---------------------------------------------------------
# ✅ Contract Instance
# ---------------------------------------------------------
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)



# ---------------------------------------------------------
# ✅ Helper: Send Raw Transaction
# ---------------------------------------------------------
def send_tx(address, private_key, function_call):
    print("send_tx called!")
    nonce = w3.eth.get_transaction_count(address)

    tx = function_call.build_transaction({
        "from": address,
        "nonce": nonce,
        "gas": 3_000_000,
        "gasPrice": w3.eth.gas_price,
    })

    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    return receipt


# ---------------------------------------------------------
# ✅ OWNER — authorize issuer (organization)
# ---------------------------------------------------------
def authorize_issuer_onchain(owner_address, owner_private_key, org_address):
    print("authorize_issuer_onchain called!")
    try:
        receipt = send_tx(
            owner_address,
            owner_private_key,
            contract.functions.authorizeIssuer(org_address)
        )
        print("✅ Blockchain authorize_issuer TX receipt:", receipt)
        
        return receipt.transactionHash.hex()
    except Exception as e:
        print("❌ Blockchain authorize_issuer error:", e)
        return None


# ---------------------------------------------------------
# ✅ ORGANIZATION — issue certificate
# ---------------------------------------------------------
def issue_certificate_onchain(certificate_id, data_hash_bytes32, org_address, org_private_key):
    try:
        receipt = send_tx(
            org_address,
            org_private_key,
            contract.functions.issueCertificate(certificate_id, data_hash_bytes32)
        )

        return {
            "tx_hash": receipt.transactionHash.hex(),
            "block_number": receipt.blockNumber
        }

    except Exception as e:
        print("❌ Blockchain issue_certificate error:", e)
        return None


# ---------------------------------------------------------
# ✅ VERIFY CERTIFICATE ON BLOCKCHAIN
# ---------------------------------------------------------
def verify_certificate_onchain(cert_id, data_hash):
    print("verify_certificate_onchain called!")
    print("Contract Address:", contract.address)
    print("Input Hash:", data_hash)

    try:
        result = contract.functions.verifyCertificate(cert_id, data_hash).call()
        print("✅ Raw blockchain result:", result)

        # result MAY be 4-tuple or 2-tuple if call failed
        if len(result) == 4:
            return result  # (exists, isValid, issuedAt, issuer)

        # If only 2 values were returned, contract call failed internally
        if len(result) == 2:
            exists, is_valid = result
            return (exists, is_valid, 0, "0x0000000000000000000000000000000000000000")

        # Unexpected fallback
        return (False, False, 0, "0x0000000000000000000000000000000000000000")

    except Exception as e:
        print("❌ Blockchain verify_certificate error:", e)

        # return safe fallback
        return (False, False, 0, "0x0000000000000000000000000000000000000000")

