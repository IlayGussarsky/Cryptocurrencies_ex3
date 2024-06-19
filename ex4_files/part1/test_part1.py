from solcx import compile_files, install_solc
from web3 import Web3
import solcx

SOLC_VERSION = '0.8.19'

# Ensure you have the appropriate Solidity compiler version installed
install_solc(SOLC_VERSION)

# Helper function to get balance in ether
def get_balance(address):
    return w3.from_wei(w3.eth.get_balance(address), 'ether')

# Compile Solidity source code
def compile(file_name: str):
    solcx.set_solc_version(SOLC_VERSION)
    compiled_sol = compile_files([file_name], output_values=['abi', 'bin'])
    contract_id, contract_interface = compiled_sol.popitem()
    if compiled_sol:
        contract_id, contract_interface = compiled_sol.popitem()
    return contract_interface['bin'], contract_interface['abi']

# Compile the contracts
wallet_bytecode, wallet_abi = compile(r'..\VulnerableWallet.sol')
attack_bytecode, attack_abi = compile(r'..\WalletAttack.sol')

# Web3 connection
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
accounts = w3.eth.accounts
def test_wallet_attack():
    # Deploy VulnerableWallet contract
    vulnerable_wallet_interface = w3.eth.contract(abi=wallet_abi, bytecode=wallet_bytecode)
    vulnerable_tx_hash = vulnerable_wallet_interface.constructor().transact({'from': w3.eth.accounts[0]})
    vulnerable_tx_receipt = w3.eth.wait_for_transaction_receipt(vulnerable_tx_hash)
    vulnerable_wallet_address = vulnerable_tx_receipt.contractAddress
    vul_wallet_instance = w3.eth.contract(address=vulnerable_wallet_address, abi=wallet_abi)

    # Deploy WalletAttack contract
    wallet_attack_interface = w3.eth.contract(abi=attack_abi, bytecode=attack_bytecode)
    wallet_attack_tx_hash = wallet_attack_interface.constructor().transact({'from': w3.eth.accounts[0]})
    wallet_attack_tx_receipt = w3.eth.wait_for_transaction_receipt(wallet_attack_tx_hash)
    wallet_attack_address = wallet_attack_tx_receipt.contractAddress

    # Call exploit function in WalletAttack contract
    wallet_attack_instance = w3.eth.contract(address=wallet_attack_address, abi=attack_abi)

    # Deposit 3 Ether to VulnerableWallet
    tx_hash = vul_wallet_instance.functions.deposit().transact(
        {'from': w3.eth.accounts[0], 'value': w3.to_wei(3, 'ether')})
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    assert (get_balance(vulnerable_wallet_address) == 3)
    balance_0 = get_balance(vulnerable_wallet_address)

    # Call exploit function in WalletAttack contract
    wallet_attack_instance.functions.exploit(vulnerable_wallet_address).transact(
        {'from': w3.eth.accounts[1], 'value': w3.to_wei(1, 'ether')})

    # Check the balance of VulnerableWallet after the attack
    balance_after_attack = get_balance(vulnerable_wallet_address)
    assert balance_after_attack == balance_0 - 3
    print(get_balance(w3.eth.accounts[0]))
    print(get_balance(w3.eth.accounts[1]))

def test_wallet_attack_adi():
    # Deploy VulnerableWallet contract
    vulnerable_wallet_interface = w3.eth.contract(abi=wallet_abi, bytecode=wallet_bytecode)
    vulnerable_tx_hash = vulnerable_wallet_interface.constructor().transact({'from': accounts[1]})
    vulnerable_tx_receipt = w3.eth.wait_for_transaction_receipt(vulnerable_tx_hash)
    vulnerable_wallet_address = vulnerable_tx_receipt.contractAddress
    vul_wallet_instance = w3.eth.contract(address=vulnerable_wallet_address, abi=wallet_abi)

    # Deploy WalletAttack contract
    wallet_attack_interface = w3.eth.contract(abi=attack_abi, bytecode=attack_bytecode)
    wallet_attack_tx_hash = wallet_attack_interface.constructor().transact({'from': accounts[2]})
    wallet_attack_tx_receipt = w3.eth.wait_for_transaction_receipt(wallet_attack_tx_hash)
    wallet_attack_address = wallet_attack_tx_receipt.contractAddress
    wallet_attack_instance = w3.eth.contract(address=wallet_attack_address, abi=attack_abi)

    # Initial balances
    print(f"Initial attacker balance: {get_balance(wallet_attack_address)} ETH")
    print(f"Initial vulnerable wallet balance: {get_balance(vulnerable_wallet_address)} ETH")

    # Deposit 3 Ether to VulnerableWallet
    tx_hash = vul_wallet_instance.functions.deposit().transact({'from': accounts[0], 'value': w3.to_wei(3, 'ether')})
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Balance of vulnerable wallet after deposit: {get_balance(vulnerable_wallet_address)} ETH")
    assert get_balance(vulnerable_wallet_address) == 3

    # Call exploit function in WalletAttack contract
    wallet_attack_instance.functions.exploit(vulnerable_wallet_address).transact({'from': accounts[2], 'value': w3.to_wei(1, 'ether')})
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print("Attack executed successfully")
    # Check the balance of VulnerableWallet after the attack
    balance_after_attack = get_balance(vulnerable_wallet_address)
    print(f"Balance of vulnerable wallet after attack: {balance_after_attack} ETH")
    assert balance_after_attack == 0

    # Check the balance of attacker after the attack
    attacker_balance_after_attack = get_balance(wallet_attack_address)
    print(f"Balance of attacker wallet after attack: {attacker_balance_after_attack} ETH")
    assert attacker_balance_after_attack == 3

    # Check the balance of accounts[2] after the attack
    account1_balance_after_attack = get_balance(accounts[2])
    print(f"Balance of account[2]/attacker after attack: {account1_balance_after_attack} ETH")


