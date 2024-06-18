// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface IRPS {
    // WARNING: Do not change this interface!!! these API functions are used to test your code.
    function getGameState(uint gameID) external view returns (RPS.GameState);

    function makeMove(uint gameID, uint betAmount, bytes32 hiddenMove) external;

    function cancelGame(uint gameID) external;

    function revealMove(uint gameID, RPS.Move move, bytes32 key) external;

    function revealPhaseEnded(uint gameID) external;

    function balanceOf(address player) external view returns (uint);

    function withdraw(uint amount) external;
}

contract RPS is IRPS {
    // This contract lets players play rock-paper-scissors.
    // its constructor receives a uint k which is the number of blocks mined before a reveal phase is over.

    // players can send the contract money to fund their bets, see their balance and withdraw it, as long as the amount is not in an active game.

    // the game mechanics: The players choose a gameID (some uint) that is not being currently used. They then each call make_move() making a bet and committing to a move.
    // in the next phase each of them reveals their committment, and once the second commit is done, the game is over. The winner gets the amount of money they agreed on.

    enum GameState {
        NO_GAME, // signifies that there is no game with this id (or there was and it is over)
        MOVE1, // signifies that a single move was entered
        MOVE2, // a second move was entered
        REVEAL1, // one of the moves was revealed, and the reveal phase just started
        LATE // one of the moves was revealed, and enough blocks have been mined since so that the other player is considered late.
    } // These correspond to values 0,1,2,3,4


    enum Move {
        NONE,
        ROCK,
        PAPER,
        SCISSORS
    } //These correspond to values 0,1,2,3

    struct Game {
        address player1;
        address player2;
        uint betAmount;
        Move move1;
        Move move2;
        bytes32 hiddenMove1;
        bytes32 hiddenMove2;
        uint revealBlock;
        GameState state;
    }

    mapping(uint => Game) public games;
    mapping(address => uint) public balances;
    uint public revealPeriodLength;

    constructor(uint _revealPeriodLength) {
        // Constructs a new contract that allows users to play multiple rock-paper-scissors games.
        // If one of the players does not reveal the move committed to, then the _revealPeriodLength
        // is the number of blocks that a player needs to wait from the moment of revealing her move until
        // she can calim that the other player loses (for not revealing).
        // The _revealPeriodLength must be at least 1 block.
        require(_revealPeriodLength >= 1, "Reveal period must be at least 1 block");
        revealPeriodLength = _revealPeriodLength;
    }

    function checkCommitment(
    // A utility function that can be used to check commitments. See also commit.py.
    // python code to generate the commitment is:
    //  commitment = HexBytes(Web3.solidityKeccak(['int256', 'bytes32'], [move, key]))
        bytes32 commitment,
        Move move,
        bytes32 key
    ) public pure returns (bool) {
        return keccak256(abi.encodePacked(uint(move), key)) == commitment;
    }

    function getGameState(uint gameID) external view override returns (GameState) {
        // Returns the state of the game at the current address as a GameState (see enum definition)
        return games[gameID].state;
    }

    function makeMove(
    // The first call to this function starts the game. The second call finishes the commit phase.
    // The amount is the amount of money (in wei) that a user is willing to bet.
    // The amount provided in the call by the second player is ignored, but the user must have an amount matching that of the game to bet.
    // amounts that are wagered are locked for the duration of the game.
    // A player should not be allowed to enter a commitment twice.
    // If two moves have already been entered, then this call reverts.
        uint gameID,
        uint betAmount,
        bytes32 hiddenMove
    ) external override {
        Game storage game = games[gameID];

        if (game.state == GameState.MOVE1) {
            require(msg.sender != game.player1, "Cannot play against yourself");
            require(balances[msg.sender] >= betAmount, "Not enough balance");
//            balances[msg.sender]-=betAmount;
            game.player2 = msg.sender;
            game.hiddenMove2 = hiddenMove;
            game.state = GameState.MOVE2;
            game.move2 = Move.NONE;
        } else if (game.state == GameState.NO_GAME) {
            require(balances[msg.sender] >= betAmount, "Not enough balance");
//            balances[msg.sender]-=betAmount;
            game.player1 = msg.sender;
            game.betAmount = betAmount;
            game.hiddenMove1 = hiddenMove;
            game.hiddenMove2 = 0;
            game.state = GameState.MOVE1;
            game.move1 = Move.NONE;
        } else {
            revert("Invalid game state");
        }
    }


    function cancelGame(uint gameID) external override {
        // This function allows a player to cancel the game, but only if the other player did not yet commit to his move.
        // a canceled game returns the funds to the player. Only the player that made the first move can call this function, and it will run only if
        // no other commitment for a move was entered.
        Game storage game = games[gameID];
        require(game.state == GameState.MOVE1, "player1 must commit");
        require(game.hiddenMove2 == 0, "other player did not yet commit");
        require(msg.sender == game.player1, "Only the first player can cancel");
        balances[game.player1] += game.betAmount;
        game.state = GameState.NO_GAME;
    }

    function revealMove(uint gameID, Move move, bytes32 key) external {
        // Reveals the move of a player (which is checked against his commitment using the key)
        // The first call to this function can be made only after two moves have been entered (otherwise the function reverts).
        // This call will begin the reveal period.
        // the second call (if called by the player that entered the second move) reveals her move, ends the game, and awards the money to the winner.
        // if a player has already revealed, and calls this function again, then this call reverts.
        // only players that have committed a move may reveal.
        // if the revealed move is bogus (not rock paper or scissors) the call should revert. This means that if both players entered bogus moves, the game cannot end and their money is stuck.
        Game storage game = games[gameID];
        require(
            game.state == GameState.MOVE2 || game.state == GameState.REVEAL1,
            "Cannot reveal"
        );
        require(
            msg.sender == game.player1 || msg.sender == game.player2,
            "Only players in this game can reveal"
        );
        require(
            move == Move.ROCK || move == Move.PAPER || move == Move.SCISSORS,
            "Invalid move"
        );

        if (msg.sender == game.player1) {
            require(game.move1 == Move.NONE, "Move1 already revealed");
            require(checkCommitment(game.hiddenMove1, Move(move), key), "Invalid commitment");
            game.move1 = move;
            if (game.state == GameState.REVEAL1) {
//                this.revealPhaseEnded(gameID);
                if (game.move2 != Move.NONE) {
                    endGame(gameID);
                }
            }
            else {
                game.revealBlock = block.number;
                game.state = GameState.REVEAL1;
            }
        } else if (msg.sender == game.player2) {
            require(game.move2 == Move.NONE, "Move2 already revealed");
            require(checkCommitment(game.hiddenMove2, move, key), "Invalid commitment");
            game.move2 = move;
            if (game.state == GameState.REVEAL1) {
//                this.revealPhaseEnded(gameID);
                if (game.move1 != Move.NONE) {
                    endGame(gameID);
                }
            } else {
                game.revealBlock = block.number;
                game.state = GameState.REVEAL1;
            }
        }
    }

    function endGame(uint gameID) internal {
        Game storage game = games[gameID];
        // tie
        if (game.move1 != game.move2) {
            //player1 wins
            if (
                (game.move1 == Move.ROCK && game.move2 == Move.SCISSORS) ||
                (game.move1 == Move.PAPER && game.move2 == Move.ROCK) ||
                (game.move1 == Move.SCISSORS && game.move2 == Move.PAPER)
            ) {
                balances[game.player1] += 1 * game.betAmount;
                balances[game.player2] -= 1 * game.betAmount;
            }
                // player2 wins
            else {
                balances[game.player1] -= 1 * game.betAmount;
                balances[game.player2] += 1 * game.betAmount;
            }
        }
        game.state = GameState.NO_GAME;
    }

    function revealPhaseEnded(uint gameID) external {
        // If no second reveal is made, and the reveal period ends, the player that did reveal can claim all funds wagered in this game.
        // The game then ends, and the game id is released (and can be reused in another game).
        // this function can only be called by the first revealer. If the reveal phase is not over, this function reverts.
        Game storage game = games[gameID];
        require(game.state == GameState.REVEAL1, "Reveal phase not started yet");
        require(
            block.number >= game.revealBlock + revealPeriodLength,
            "Reveal period is not over"
        );
        require(
            msg.sender == game.player1 || msg.sender == game.player2,
            "Only players in this game can claim"
        );
        if (game.move1 != Move.NONE && game.move2 == Move.NONE) {
            balances[game.player1] += 1 * game.betAmount;
            balances[game.player2] -= 1 * game.betAmount;
        } else if (game.move1 == Move.NONE && game.move2 != Move.NONE) {
            balances[game.player1] -= 1 * game.betAmount;
            balances[game.player2] += 1 * game.betAmount;
        }
        game.state = GameState.LATE;
    }

    function balanceOf(address player) external view returns (uint) {
        // returns the balance of the given player. Funds that are wagered in games that did not complete yet are not counted as part of the balance.
        // make sure the access level of this function is "view" as it does not change the state of the contract.
        return balances[player];
    }

    function withdraw(uint amount) external {
        // Withdraws amount from the account of the sender
        // (available funds are those that were deposited or won but not currently staked in a game).
        require(balances[msg.sender] >= amount, "Not enough balance");
        balances[msg.sender] -= amount;
        msg.sender.call{value: amount}("");
    }

    receive() external payable {
        // adds eth to the account of the message sender.
        balances[msg.sender] += msg.value;
    }

}
