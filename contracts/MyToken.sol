// SPDX-License-Identifier: UNLICENSED

pragma solidity ^0.8;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MyToken is ERC20 {

    constructor() ERC20("MyToken", "MOCK") {

    }

    function faucet() public {
        _mint(msg.sender, 1 ether);
    }
}
