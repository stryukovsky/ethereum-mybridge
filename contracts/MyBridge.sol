// SPDX-License-Identifier: MIT

pragma solidity ^0.8;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract MyBridge {

    IERC20 bridgedAsset;
    address offChainOperator;

    event BridgingInitialized(bytes32 indexed bridgingId, address indexed user, uint256 indexed amount);

    mapping (bytes32 => address) initializedBridgingUser;
    mapping (bytes32 => uint256) initializedBridgingAmount;

    mapping (bytes32 => bool) finalizedBridging;



    function createBridgingId() public view returns(bytes32) {
        return keccak256(abi.encodePacked(msg.sender, block.number,  block.timestamp));
    }

    constructor(IERC20 _bridgedAsset, address _offChainOperator) {
        bridgedAsset = _bridgedAsset;
        offChainOperator = _offChainOperator;
    }

    function initializeBridge(uint256 amount) public {
        bytes32 bridgingId = createBridgingId();
        require(initializedBridgingUser[bridgingId] == address(0), "ALREADY_INITIALIZED");
        require(initializedBridgingAmount[bridgingId] == 0, "ALREADY_INITIALIZED");
        bridgedAsset.transferFrom(msg.sender, address(this), amount);
        initializedBridgingUser[bridgingId] = msg.sender;
        initializedBridgingAmount[bridgingId] = amount;
        emit BridgingInitialized(bridgingId, msg.sender, amount);
    }

    function finalizeBridge(bytes32 bridgingId, address user, uint256 amount) public {
        require(msg.sender == offChainOperator, "NOT_AUTHORIZED");
        require(!finalizedBridging[bridgingId], "ALREADY_FINALIZED");
        finalizedBridging[bridgingId] = true;
        bridgedAsset.transfer(user, amount);
    }

    function canFinalizeBridge(uint256 amount) public view returns(bool) {
        return bridgedAsset.balanceOf(address(this)) >= amount;
    }

    function bridgeFailed(bytes32 bridgingId) public {
        require(msg.sender == offChainOperator, "NOT_AUTHORIZED");
        require(initializedBridgingUser[bridgingId] != address(0), "NOT_INITIALIZED");
        require(initializedBridgingAmount[bridgingId] != 0, "NOT_INITIALIZED");
        bridgedAsset.transfer(initializedBridgingUser[bridgingId], initializedBridgingAmount[bridgingId]);
        initializedBridgingUser[bridgingId] = address(0);
        initializedBridgingAmount[bridgingId] = 0;
    }

    function bridgeCompleted(bytes32 bridgingId) public {
        require(msg.sender == offChainOperator, "NOT_AUTHORIZED");
        require(initializedBridgingUser[bridgingId] != address(0), "NOT_INITIALIZED");
        require(initializedBridgingAmount[bridgingId] != 0, "NOT_INITIALIZED");
        // TODO: AMM stuff
        initializedBridgingUser[bridgingId] = address(0);
        initializedBridgingAmount[bridgingId] = 0;
    }
}