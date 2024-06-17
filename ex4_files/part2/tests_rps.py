import pytest
from hexbytes import HexBytes
from web3 import Web3
import solcx
from solcx import compile_files, install_solc
from web3.exceptions import ContractLogicError
import hashlib

SOLC_VERSION = 'v0.8.19'

# Ensure you have the appropriate Solidity compiler version installed
install_solc(SOLC_VERSION)


# Compile Solidity source code
def compile(file_name: str):
    solcx.set_solc_version(SOLC_VERSION)
    compiled_sol = compile_files([file_name], output_values=['abi', 'bin'])
    contract_id, contract_interface = compiled_sol.popitem()
    return contract_interface['bin'], contract_interface['abi']


@pytest.fixture
def w3():
    # Initialize Web3 instance
    w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
    assert w3.is_connected(), "Web3 is not connected"
    return w3


@pytest.fixture
def accounts(w3):
    # Get the list of accounts
    return w3.eth.accounts


@pytest.fixture
def contract(w3, accounts):
    # Compile the contract
    bytecode, abi = compile("RPS.sol")

    # Deploy the contract
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = contract.constructor(4).transact({'from': accounts[0]})
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = tx_receipt.contractAddress
    return w3.eth.contract(address=contract_address, abi=abi)


@pytest.fixture
def player1(w3, accounts):
    w3.eth.send_transaction(
        {'to': accounts[1], 'from': w3.eth.accounts[0], 'value': w3.to_wei(10, 'ether')})
    balance = w3.eth.get_balance(accounts[1])
    return accounts[1]


@pytest.fixture
def player2(w3, accounts):
    # Fund player1 and player2 accounts with enough balance
    w3.eth.send_transaction({'to': accounts[2], 'value': w3.to_wei(10, 'ether')})  # Fund player2's account
    return accounts[2]


def test_constructor(contract):
    # Check initial reveal period length according to the revealPeriodLength in contract constructor
    reveal_period_length = contract.functions.revealPeriodLength().call()
    assert reveal_period_length == 4


def test_wrong_constructor(w3, accounts):
    # Check initial reveal period length is 0 in constructor
    bytecode, abi = compile("RPS.sol")
    # Deploy the contract with reveal period length 0
    try:
        w3.eth.contract(abi=abi, bytecode=bytecode).constructor(0).transact({'from': accounts[0]})
    # Check if the transaction failed (revert occurred)
    except ContractLogicError:
        return True  # Error occurred as expected
    return False  # No error occurred


def test_initial_get_game_state(contract):
    # check game start with NO_GAME state
    assert contract.functions.getGameState(0).call() == 0


def test_after_player1_made_move(w3, contract, accounts, player1):
    # Simulate player 1 making a move
    game_id = 0
    bet_amount = w3.to_wei(1, 'ether')
    hidden_move = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, b"secret"]))
    contract.functions.makeMove(game_id, bet_amount, hidden_move).transact({'from': player1})
    # Call the getGameState function
    actual_state = contract.functions.getGameState(game_id).call()
    # Check if the actual state is MOVE1 (1)
    assert actual_state == 1


def test_after_player2_made_move(w3, contract, accounts, player1, player2):
    # Simulate player 1 making a move
    game_id = 0
    bet_amount = w3.to_wei(1, 'ether')
    # Simulate player 1 making a move
    hidden_move = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, b"secret1"]))
    contract.functions.makeMove(game_id, bet_amount, hidden_move).transact({'from': player1})
    # Simulate player 2 making a move
    hidden_move = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, b"secret2"]))
    contract.functions.makeMove(game_id, bet_amount, hidden_move).transact({'from': player2})
    # Call the getGameState function
    actual_state = contract.functions.getGameState(game_id).call()
    # Check if the actual state is MOVE2 (2)
    assert actual_state == 2


def test_cancel_game(contract, accounts, w3, player1):
    # Simulate player 1 making a move
    game_id = 0
    bet_amount = w3.to_wei(1, 'ether')
    hidden_move = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, b"secret"]))
    contract.functions.makeMove(game_id, bet_amount, hidden_move).transact({'from': player1})

    # Cancel game
    contract.functions.cancelGame(game_id).transact({'from': player1})

    # Check game state
    game_state = contract.functions.getGameState(game_id).call()
    assert game_state == 0  # NO_GAME


def test_player2_cant_cancel_game(contract, accounts, w3, player1, player2):
    # Simulate player 1 making a move
    game_id = 0
    bet_amount = w3.to_wei(1, 'ether')
    # Simulate player 1 making a move
    hidden_move = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, b"secret1"]))
    contract.functions.makeMove(game_id, bet_amount, hidden_move).transact({'from': player1})
    # Simulate player 2 making a move
    hidden_move = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, b"secret2"]))
    contract.functions.makeMove(game_id, bet_amount, hidden_move).transact({'from': player2})
    try:
        contract.functions.cancelGame(game_id).transact({'from': player2})
    # Check if the transaction failed (revert occurred)
    except ContractLogicError:
        return True  # Error occurred as expected
    return False  # No error occurred


def test_reveal_move(contract, accounts, web3):
    return 1



def test_withdraw(contract, accounts, web3):
    return 1

