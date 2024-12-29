import json
import os
import time
from asyncio import timeout
from typing import List

from eth_account.signers.local import LocalAccount
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from web3.datastructures import AttributeDict
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers import HTTPProvider

RPC_1_URL: str = os.environ["RPC_1_URL"]
RPC_2_URL: str = os.environ["RPC_2_URL"]

BRIDGE_1_ADDRESS: str = os.environ["BRIDGE_1_ADDRESS"]
BRIDGE_2_ADDRESS: str = os.environ["BRIDGE_2_ADDRESS"]

PRIVATE_KEY: str = os.environ["PRIVATE_KEY"]


def read_abi(filename: str):
    with open(f"abi/{filename}", "r") as file:
        return json.load(file)


def handle_bridging(web3_initializer: Web3, contract_initializer: Contract, web3_finalizer: Web3,
                    contract_finalizer: Contract):
    contract_filter = contract_initializer.events["BridgingInitialized"].create_filter(
        from_block="latest")  # latest actually
    bridge_initializer_account = web3_finalizer.eth.account.from_key(PRIVATE_KEY)
    bridge_finalizer_account = web3_finalizer.eth.account.from_key(PRIVATE_KEY)
    while True:
        events: List[AttributeDict] = contract_filter.get_all_entries()
        print(f"Processing {len(events)} events")
        for event in events:
            arguments = event["args"]
            bridging_id: bytes = arguments["bridgingId"]
            amount = arguments["amount"]
            user = web3_initializer.to_checksum_address(arguments["user"])
            print(f"Processing bridge with id 0x{bridging_id.hex()}: user {user} transfers {amount}")
            can_finalize: bool = contract_finalizer.functions["canFinalizeBridge"](amount).call()
            if can_finalize:
                bridge_finalize_data = contract_finalizer.encode_abi("finalizeBridge", args=[bridging_id, user, amount])
                finalization_tx_hash = send_tx(bridge_finalizer_account, contract_finalizer, bridge_finalize_data,
                                               web3_finalizer)
                print(f"Sent to finalizer-chain tx {prettify_tx_hash(finalization_tx_hash)}")
                receipt = web3_finalizer.eth.wait_for_transaction_receipt(finalization_tx_hash, timeout=600)
                if receipt["status"] == 1:
                    print(f"Bridging finalized successfully")
                    bridge_complete_data = contract_initializer.encode_abi("bridgeCompleted", args=[bridging_id])
                    complete_tx_hash = send_tx(bridge_initializer_account, contract_initializer, bridge_complete_data,
                                               web3_initializer)
                    print(f"Bridging was completed with tx hash {prettify_tx_hash(complete_tx_hash)}")
            else:
                data = contract_initializer.encode_abi("bridgeFailed", args=[bridging_id])
                tx_hash = send_tx(bridge_initializer_account, contract_initializer, data, web3_initializer)
                print(f"Failure: not enough money; send to initializer-chain tx {prettify_tx_hash(tx_hash)}")
        print("End of cycle; sleep for 5 seconds")
        time.sleep(5)


def prettify_tx_hash(tx_hash: HexBytes):
    return f"0x{tx_hash.hex()}"


def send_tx(account: LocalAccount, contract: Contract, data, web3: Web3) -> HexBytes:
    unsigned_tx = {
        'chainId': web3.eth.chain_id,
        'from': account.address,
        'to': contract.address,
        'value': 0,
        'nonce': web3.eth.get_transaction_count(account.address),
        'gas': 200000,
        'gasPrice': web3.eth.gas_price,
        'data': data
    }
    signed_tx = web3.eth.account.sign_transaction(unsigned_tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return tx_hash


def main():
    web1 = Web3(HTTPProvider(RPC_1_URL))
    web1.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    web2 = Web3(HTTPProvider(RPC_2_URL))
    web2.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    bridge1 = web1.eth.contract(address=web1.to_checksum_address(BRIDGE_1_ADDRESS), abi=read_abi("MyBridge.json"))
    bridge2 = web2.eth.contract(address=web2.to_checksum_address(BRIDGE_2_ADDRESS), abi=read_abi("MyBridge.json"))
    handle_bridging(web1, bridge1, web2, bridge2)


if __name__ == "__main__":
    main()
