// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

/// Test double that mirrors the canonical registry's getSummary / getValidationStatus logic
/// (filters by validator list and tag, integer average, "unknown" revert). Not for deployment.
contract MockValidationRegistry {
    struct S { address validatorAddress; uint256 agentId; uint8 response; bytes32 responseHash; string tag; uint256 lastUpdate; bool hasResponse; }
    mapping(bytes32 => S) public statuses;
    mapping(uint256 => bytes32[]) internal byAgent;

    function request(address validatorAddress, uint256 agentId, bytes32 requestHash) external {
        require(statuses[requestHash].validatorAddress == address(0), "exists");
        statuses[requestHash] = S(validatorAddress, agentId, 0, bytes32(0), "", block.timestamp, false);
        byAgent[agentId].push(requestHash);
    }

    function respond(bytes32 requestHash, uint8 response, bytes32 responseHash, string calldata tag) external {
        S storage s = statuses[requestHash];
        require(s.validatorAddress != address(0), "unknown");
        require(msg.sender == s.validatorAddress, "not validator");
        require(response <= 100, "resp>100");
        s.response = response; s.responseHash = responseHash; s.tag = tag; s.hasResponse = true; s.lastUpdate = block.timestamp;
    }

    function getSummary(uint256 agentId, address[] calldata validatorAddresses, string calldata tag)
        external view returns (uint64 count, uint8 avgResponse)
    {
        uint256 total;
        bytes32[] storage hs = byAgent[agentId];
        for (uint256 i; i < hs.length; i++) {
            S storage s = statuses[hs[i]];
            bool vOk = validatorAddresses.length == 0;
            for (uint256 j; j < validatorAddresses.length && !vOk; j++) if (s.validatorAddress == validatorAddresses[j]) vOk = true;
            bool tOk = bytes(tag).length == 0 || keccak256(bytes(s.tag)) == keccak256(bytes(tag));
            if (vOk && tOk && s.hasResponse) { total += s.response; count++; }
        }
        avgResponse = count > 0 ? uint8(total / count) : 0;
    }

    function getValidationStatus(bytes32 requestHash) external view
        returns (address, uint256, uint8, bytes32, string memory, uint256)
    {
        S storage s = statuses[requestHash];
        require(s.validatorAddress != address(0), "unknown");
        return (s.validatorAddress, s.agentId, s.response, s.responseHash, s.tag, s.lastUpdate);
    }
}
