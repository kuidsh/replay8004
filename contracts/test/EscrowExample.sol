// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

import "../ReplayGate.sol";

/// Example consumer: a job board that only lets agents with a verified payment history bid,
/// and only marks a job paid when replay8004 confirmed that exact x402 settlement. Holds no funds.
contract EscrowExample is ReplayGate {
    mapping(uint256 => uint256) public bids;     // jobId => agentId
    mapping(uint256 => bool) public paid;        // jobId => settled

    constructor(IValidationRegistry r, address v) ReplayGate(r, v) {}

    function bid(uint256 jobId, uint256 agentId)
        external onlyValidatedAgent(agentId, "replay:x402_settlement", 3, 90)
    {
        bids[jobId] = agentId;
    }

    function markPaid(uint256 jobId, bytes32 requestHash)
        external onlyValidatedClaim(requestHash, bids[jobId], "replay:x402_settlement", 100, 1 days)
    {
        paid[jobId] = true;
    }
}
