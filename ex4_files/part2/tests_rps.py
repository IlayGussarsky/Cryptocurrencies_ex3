import pytest
from hexbytes import HexBytes
from web3 import Web3
import solcx
from solcx import compile_files, install_solc
from web3.exceptions import ContractLogicError
import hashlib
from enum import Enum


# Define Move enum locally in your test file
class Move(Enum):
    NONE = 0
    ROCK = 1
    PAPER = 2
    SCISSORS = 3


SOLC_VERSION = 'v0.8.19'

# Ensure you have the appropriate Solidity compiler version installed
install_solc(SOLC_VERSION)
REVEAL_PHASE_LENGTH = 4


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
    tx_hash = contract.constructor(REVEAL_PHASE_LENGTH).transact({'from': accounts[0]})
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = tx_receipt.contractAddress
    return w3.eth.contract(address=contract_address, abi=abi)


@pytest.fixture
def player1(w3, accounts):
    w3.eth.send_transaction(
        {'to': accounts[1], 'from': w3.eth.accounts[0], 'value': w3.to_wei(5, 'ether')})
    balance = w3.eth.get_balance(accounts[1])
    print(balance)
    return accounts[1]


@pytest.fixture
def player2(w3, accounts):
    # Fund player1 and player2 accounts with enough balance
    w3.eth.send_transaction({'to': accounts[2], 'value': w3.to_wei(5, 'ether')})  # Fund player2's account
    return accounts[2]


def virualBalance(contract, player):
    return contract.functions.balanceOf(player).call()


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
    contract.receive().transact({'from': player1, 'value': w3.to_wei(1, 'ether')})
    contract.functions.makeMove(game_id, bet_amount, hidden_move).transact({'from': player1})
    # Call the getGameState function
    actual_state = contract.functions.getGameState(game_id).call()
    # Check if the actual state is MOVE1 (1)
    assert actual_state == 1


def test_after_player2_made_move(w3, contract, accounts, player1, player2):
    # Simulate player 1 making a move
    game_id = 0
    bet_amount = w3.to_wei(1, 'ether')
    contract.receive().transact({'from': player1, 'value': w3.to_wei(1, 'ether')})
    contract.receive().transact({'from': player2, 'value': w3.to_wei(1, 'ether')})

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
    contract.receive().transact({'from': player1, 'value': w3.to_wei(1, 'ether')})
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
    contract.receive().transact({'from': player1, 'value': w3.to_wei(2, 'ether')})
    contract.receive().transact({'from': player2, 'value': w3.to_wei(2, 'ether')})
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


def test_reveal_move_first_player(contract, accounts, w3, player1, player2):
    # Simulate player 1 making a move
    game_id = 0
    bet_amount = w3.to_wei(1, 'ether')
    str1 = (Web3.to_bytes(text="secret1")).zfill(32)
    contract.receive().transact({'from': player1, 'value': w3.to_wei(1, 'ether')})
    contract.receive().transact({'from': player2, 'value': w3.to_wei(1, 'ether')})
    # Simulate player 1 making a move
    hidden_move1 = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, str1]))
    contract.functions.makeMove(game_id, bet_amount, hidden_move1).transact({'from': player1})
    # Simulate player 2 making a move
    hidden_move2 = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, b"secret2"]))
    contract.functions.makeMove(game_id, bet_amount, hidden_move2).transact({'from': player2})
    contract.functions.revealMove(game_id, 1, str1).transact({'from': player1})

    # Check game state after first player revealed
    game_state = contract.functions.getGameState(game_id).call()
    assert game_state == 3  # GameState.REVEAL1
    # try reveal again
    try:
        contract.functions.revealMove(game_id, 1, str1).transact({'from': player1})
        # Check if the transaction failed (revert occurred)
    except ContractLogicError:
        return True  # Error occurred as expected
    return False  # No error occurred


def test_reveal_move_both_players(contract, accounts, w3, player1, player2):
    # TO DO - check why not pass? probably problem with balance in endGame

    # Simulate player 1 making a move
    game_id = 0
    bet_amount = w3.to_wei(5, 'ether')
    contract.receive().transact({'from': player1, 'value': w3.to_wei(5, 'ether')})
    contract.receive().transact({'from': player2, 'value': w3.to_wei(5, 'ether')})
    before = virualBalance(contract, player1)
    # Check balances before endGame
    print("before made move1")
    print(before)
    # Player 1's move
    str1 = (Web3.to_bytes(text="secret1")).zfill(32)
    hidden_move1 = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, str1]))
    tx1 = contract.functions.makeMove(game_id, bet_amount, hidden_move1).transact({'from': player1})
    after = virualBalance(contract, player1)
    print("after made move1")
    print(after)
    print("tx1", w3.eth.get_transaction_receipt(tx1).gasUsed)
    # assert after == (before -bet_amount)
    print("before made move2")
    print(w3.to_wei(virualBalance(contract, player2), 'ether'))
    # Simulate player 2 making a move
    str2 = (Web3.to_bytes(text="secret2")).zfill(32)
    hidden_move2 = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [2, str2]))
    tx2 = contract.functions.makeMove(game_id, bet_amount, hidden_move2).transact({'from': player2})
    print("after made move2")
    print(w3.from_wei(virualBalance(contract, player2), "ether"))
    # Player 1 reveals move
    tx3 = contract.functions.revealMove(game_id, 1, str1).transact({'from': player1})

    # Check game state after first player revealed
    game_state = contract.functions.getGameState(game_id).call()
    assert game_state == 3  # GameState.REVEAL1

    # Player 2 reveals move
    tx4 = contract.functions.revealMove(game_id, 2, str2).transact({'from': player2})

    # Check game state after both players revealed
    game_state = contract.functions.getGameState(game_id).call()
    assert game_state == 0  # GameState.NoGame

    # Calculate gas used
    gas_used = sum(w3.eth.get_transaction_receipt(tx).gasUsed for tx in [tx1, tx2, tx3, tx4])
    gas_price = w3.eth.gas_price

    # Calculate expected balances
    winner_balance_after = virualBalance(contract, player2)
    loser_balance_after = virualBalance(contract, player1)

    # Check if the winner balance increased by the correct amount (bet)
    # assert winner_balance_after == winner_balance_before + bet_amount - gas_used * gas_price

    # Check if the loser balance decreased by the bet amount
    assert before - loser_balance_after == w3.to_wei(5, 'ether')


def test_revealPhaseEnded(contract, accounts, w3, player1, player2):
    assert virualBalance(contract, player1) == 0
    assert virualBalance(contract, player2) == 0
    game_id = 0

    def tryToEnterRevealTestEnded(player=player1):
        try:
            contract.functions.revealPhaseEnded(game_id).transact({'from': player})
            return False
        except ContractLogicError:
            pass



    bet_amount = w3.to_wei(5, 'ether')
    contract.receive().transact({'from': player1, 'value': bet_amount})
    contract.receive().transact({'from': player2, 'value': bet_amount})

    # See that you can't enter revealPhaseEnded
    tryToEnterRevealTestEnded()
    tryToEnterRevealTestEnded(player=player2)

    # Player 1 makes a move
    str1 = (Web3.to_bytes(text="secret1")).zfill(32)
    hidden_move1 = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, str1]))
    tx1 = contract.functions.makeMove(game_id, bet_amount, hidden_move1).transact({'from': player1})

    # See that you can't enter revealPhaseEnded
    tryToEnterRevealTestEnded()

    # Mine some unimportant blocks.
    for i in range(REVEAL_PHASE_LENGTH + 1):
        w3.provider.make_request('evm_mine', [])
    assert contract.functions.getGameState(game_id).call() == 1

    # See that you can't enter revealPhaseEnded
    tryToEnterRevealTestEnded()

    # Player 2 makes a move
    str2 = (Web3.to_bytes(text="secret2")).zfill(32)
    hidden_move2 = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [2, str2]))
    tx2 = contract.functions.makeMove(game_id, bet_amount, hidden_move2).transact({'from': player2})

    # See that you can't enter revealPhaseEnded
    tryToEnterRevealTestEnded()

    # Mine some unimportant blocks.
    for i in range(REVEAL_PHASE_LENGTH + 1):
        w3.provider.make_request('evm_mine', [])
    assert contract.functions.getGameState(game_id).call() == 2

    # See that you can't enter revealPhaseEnded
    tryToEnterRevealTestEnded()

    tx3 = contract.functions.revealMove(game_id, 1, str1).transact({'from': player1})

    # Mine some IMPORTANT blocks.
    for i in range(REVEAL_PHASE_LENGTH-1):
        w3.provider.make_request('evm_mine', [])

    # See that you can't enter revealPhaseEnded
    tryToEnterRevealTestEnded()

    # Mine one last block:
    w3.provider.make_request('evm_mine', [])

    # See that you can enter revealPhaseEnded
    contract.functions.revealPhaseEnded(game_id).transact({'from': player1})
    tryToEnterRevealTestEnded(player=player2)



def test_balanceOf(contract, accounts, w3):
    # TO DO
    return 1


def test_withdraw(contract, accounts, w3, player1, player2):
    def checkBaseBalance():
        assert virualBalance(contract, player1) == w3.to_wei(5, 'ether')
        assert virualBalance(contract, player2) == w3.to_wei(5, 'ether')

    assert virualBalance(contract, player1) == 0
    assert virualBalance(contract, player2) == 0

    game_id = 0
    bet_amount = w3.to_wei(5, 'ether')
    contract.receive().transact({'from': player1, 'value': bet_amount})
    contract.receive().transact({'from': player2, 'value': bet_amount})

    checkBaseBalance()

    str1 = (Web3.to_bytes(text="secret1")).zfill(32)
    hidden_move1 = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, str1]))
    tx1 = contract.functions.makeMove(game_id, bet_amount, hidden_move1).transact({'from': player1})

    checkBaseBalance()

    str2 = (Web3.to_bytes(text="secret2")).zfill(32)
    hidden_move2 = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [2, str2]))
    tx2 = contract.functions.makeMove(game_id, bet_amount, hidden_move2).transact({'from': player2})

    checkBaseBalance()

    tx3 = contract.functions.revealMove(game_id, 1, str1).transact({'from': player1})

    checkBaseBalance()

    tx4 = contract.functions.revealMove(game_id, 2, str2).transact({'from': player2})

    # Game ended, now try to withdraw
    assert virualBalance(contract, player1) == w3.to_wei(0, 'ether')
    assert virualBalance(contract, player2) == w3.to_wei(10, 'ether')

    try:
        contract.functions.withdraw(w3.to_wei(15, 'ether')).transact({'from': player2})
        return False
    except ContractLogicError:
        pass

    contract.functions.withdraw(w3.to_wei(7, 'ether')).transact({'from': player2})
    assert virualBalance(contract, player1) == w3.to_wei(0, 'ether')
    assert virualBalance(contract, player2) == w3.to_wei(3, 'ether')

    try:
        contract.functions.withdraw(w3.to_wei(1, 'ether')).transact({'from': player1})
        return False
    except ContractLogicError:
        pass

    contract.receive().transact({'from': player2, 'value': bet_amount})
    assert virualBalance(contract, player1) == w3.to_wei(0, 'ether')
    assert virualBalance(contract, player2) == w3.to_wei(8, 'ether')


def test_withdraw_draw(contract, accounts, w3, player1, player2):
    def checkBaseBalance():
        assert virualBalance(contract, player1) == w3.to_wei(5, 'ether')
        assert virualBalance(contract, player2) == w3.to_wei(5, 'ether')

    assert virualBalance(contract, player1) == 0
    assert virualBalance(contract, player2) == 0

    game_id = 0
    bet_amount = w3.to_wei(5, 'ether')
    contract.receive().transact({'from': player1, 'value': bet_amount})
    contract.receive().transact({'from': player2, 'value': bet_amount})

    checkBaseBalance()

    str1 = (Web3.to_bytes(text="secret1")).zfill(32)
    hidden_move1 = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, str1]))
    tx1 = contract.functions.makeMove(game_id, bet_amount, hidden_move1).transact({'from': player1})

    checkBaseBalance()

    str2 = (Web3.to_bytes(text="secret2")).zfill(32)
    hidden_move2 = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, str2]))
    tx2 = contract.functions.makeMove(game_id, bet_amount, hidden_move2).transact({'from': player2})

    checkBaseBalance()

    tx3 = contract.functions.revealMove(game_id, 1, str1).transact({'from': player1})

    checkBaseBalance()

    tx4 = contract.functions.revealMove(game_id, 1, str2).transact({'from': player2})

    # Game ended, now try to withdraw
    checkBaseBalance()


def test_playerSendsTwoMoves(contract, accounts, w3, player1, player2):
    assert virualBalance(contract, player1) == 0
    assert virualBalance(contract, player2) == 0

    game_id = 0
    bet_amount = w3.to_wei(5, 'ether')
    contract.receive().transact({'from': player1, 'value': bet_amount})
    contract.receive().transact({'from': player2, 'value': bet_amount})

    str1 = (Web3.to_bytes(text="secret1")).zfill(32)
    hidden_move1 = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, str1]))
    tx1 = contract.functions.makeMove(game_id, bet_amount, hidden_move1).transact({'from': player1})

    try:
        str1 = (Web3.to_bytes(text="secret1")).zfill(32)
        hidden_move1 = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, str1]))
        tx1 = contract.functions.makeMove(game_id, bet_amount, hidden_move1).transact({'from': player1})
        return False
    except ContractLogicError:
        pass


def test_wrongCommitment(contract, accounts, w3, player1, player2):
    game_id = 0
    bet_amount = w3.to_wei(5, 'ether')
    contract.receive().transact({'from': player1, 'value': bet_amount})
    contract.receive().transact({'from': player2, 'value': bet_amount})

    str1 = (Web3.to_bytes(text="secret1")).zfill(32)
    hidden_move1 = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [1, str1]))
    tx1 = contract.functions.makeMove(game_id, bet_amount, hidden_move1).transact({'from': player1})

    str2 = (Web3.to_bytes(text="secret2")).zfill(32)
    hidden_move2 = HexBytes(Web3.solidity_keccak(['int256', 'bytes32'], [2, str2]))
    tx2 = contract.functions.makeMove(game_id, bet_amount, hidden_move2).transact({'from': player2})

    try:
        tx3 = contract.functions.revealMove(game_id, 2, str1).transact({'from': player1})
    except ContractLogicError:
        return True
    return False
