from solcx import compile_files, install_solc
from web3 import Web3
import solcx

SOLC_VERSION = 'v0.8.19'

# Ensure you have the appropriate Solidity compiler version installed
install_solc(SOLC_VERSION)


# Compile Solidity source code
def compile(file_name: str):
    solcx.set_solc_version(SOLC_VERSION)
    compiled_sol = compile_files([file_name], output_values=['abi', 'bin'])
    contract_id, contract_interface = compiled_sol.popitem()
    return contract_interface['bin'], contract_interface['abi']


# Compile the contracts
wallet_bytecode, wallet_abi = compile(r'part1/VulnerableWallet.sol')
attack_bytecode, attack_abi = compile(r'part1/WalletAttack.sol')

# Web3 connection
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))


def test_wallet_attack():
    # Deploy VulnerableWallet contract
    vulnerable_wallet_interface = w3.eth.contract(abi=wallet_abi, bytecode=wallet_bytecode)
    vulnerable_tx_hash = vulnerable_wallet_interface.constructor().transact()
    vulnerable_tx_receipt = w3.eth.wait_for_transaction_receipt(vulnerable_tx_hash)
    vulnerable_wallet_address = vulnerable_tx_receipt.contractAddress

    # Deploy WalletAttack contract
    wallet_attack_interface = w3.eth.contract(abi=attack_abi, bytecode=attack_bytecode)
    wallet_attack_tx_hash = wallet_attack_interface.constructor().transact()
    wallet_attack_tx_receipt = w3.eth.wait_for_transaction_receipt(wallet_attack_tx_hash)
    wallet_attack_address = wallet_attack_tx_receipt.contractAddress

    # Call exploit function in WalletAttack contract
    wallet_attack_instance = w3.eth.contract(address=wallet_attack_address, abi=attack_abi)

    # Deposit 3 Ether to VulnerableWallet
    w3.eth.send_transaction(
        {'to': vulnerable_wallet_address, 'from': w3.eth.accounts[0], 'value': w3.to_wei(3, 'ether')})

    # Call exploit function in WalletAttack contract
    wallet_attack_instance.functions.exploit(vulnerable_wallet_address).transact({'from': w3.eth.accounts[0], 'value': w3.to_wei(1, 'ether')})

    # Check the balance of VulnerableWallet after the attack
    balance_after_attack = vulnerable_wallet_interface.functions.getBalance().call()
    assert balance_after_attack == 2 * 10 ** 18  # Assuming 1 Ether is 10**18 Wei



# Run the test
test_wallet_attack()
