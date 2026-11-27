// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

/// @notice The two read calls of the canonical ERC-8004 ValidationRegistry that a gate needs.
/// Signatures from erc-8004-contracts ValidationRegistryUpgradeable.sol (read 2026-11-22).
interface IValidationRegistry {
    function getSummary(uint256 agentId, address[] calldata validatorAddresses, string calldata tag)
        external view returns (uint64 count, uint8 avgResponse);

    function getValidationStatus(bytes32 requestHash)
        external view
        returns (address validatorAddress, uint256 agentId, uint8 response, bytes32 responseHash,
                 string memory tag, uint256 lastUpdate);
}

/// @title ReplayGate
/// @notice "Only accept agents that replay8004 has validated." Read-only: holds no funds, has no owner,
///         and its settings are fixed at deploy time. Inherit it, or call it from another contract.
/// @dev Two checks, because the registry offers two views:
///      - track record: getSummary over every answered request for (agentId, validator, tag).
///        The agent owner chooses which claims to submit, so a record shows "N claims checked, average S",
///        not "every claim this agent ever made". Use minCount to demand a real history.
///      - one specific claim: getValidationStatus(requestHash), e.g. "this exact payment was verified,
///        recently, with score >= S". This is the check to use before releasing an escrow.
contract ReplayGate {
    IValidationRegistry public immutable registry;
    address public immutable validator;

    error NotValidated(uint256 agentId, uint64 count, uint8 avg);
    error ClaimNotValidated(bytes32 requestHash, uint8 reason);

    // reasons for ClaimNotValidated
    uint8 internal constant WRONG_VALIDATOR = 1;
    uint8 internal constant WRONG_AGENT = 2;
    uint8 internal constant NO_RESPONSE = 3;
    uint8 internal constant LOW_SCORE = 4;
    uint8 internal constant STALE = 5;
    uint8 internal constant WRONG_TAG = 6;

    constructor(IValidationRegistry registry_, address validator_) {
        require(address(registry_) != address(0) && validator_ != address(0), "zero address");
        registry = registry_;
        validator = validator_;
    }

    /// @return count answered requests
    /// @return avg their average score (0 when count is 0)
    function record(uint256 agentId, string memory tag) public view returns (uint64 count, uint8 avg) {
        address[] memory vs = new address[](1);
        vs[0] = validator;
        return registry.getSummary(agentId, vs, tag);
    }

    /// @notice true if replay8004 answered at least minCount requests for this agent and tag,
    ///         with an average score of at least minAvg. tag "" means any replay8004 tag.
    function passes(uint256 agentId, string memory tag, uint64 minCount, uint8 minAvg) public view returns (bool) {
        (uint64 count, uint8 avg) = record(agentId, tag);
        return count >= minCount && count > 0 && avg >= minAvg;
    }

    /// @notice Checks one request. maxAge 0 means no freshness limit. tag "" accepts any tag.
    /// @return ok true when the claim passes
    /// @return reason 0 when ok, otherwise a reason code
    function claimStatus(bytes32 requestHash, uint256 agentId, string memory tag, uint8 minScore, uint256 maxAge)
        public view returns (bool ok, uint8 reason)
    {
        (address v, uint256 a, uint8 response, bytes32 responseHash, string memory t, uint256 lastUpdate) =
            registry.getValidationStatus(requestHash);
        if (v != validator) return (false, WRONG_VALIDATOR);
        if (a != agentId) return (false, WRONG_AGENT);
        // replay8004 always posts a non-zero responseHash (keccak of its evidence bundle), so a zero hash
        // means the request has not been answered yet.
        if (responseHash == bytes32(0)) return (false, NO_RESPONSE);
        if (bytes(tag).length != 0 && keccak256(bytes(t)) != keccak256(bytes(tag))) return (false, WRONG_TAG);
        if (response < minScore) return (false, LOW_SCORE);
        if (maxAge != 0 && block.timestamp > lastUpdate + maxAge) return (false, STALE);
        return (true, 0);
    }

    modifier onlyValidatedAgent(uint256 agentId, string memory tag, uint64 minCount, uint8 minAvg) {
        if (!passes(agentId, tag, minCount, minAvg)) {
            (uint64 c, uint8 avg) = record(agentId, tag);
            revert NotValidated(agentId, c, avg);
        }
        _;
    }

    modifier onlyValidatedClaim(bytes32 requestHash, uint256 agentId, string memory tag, uint8 minScore, uint256 maxAge) {
        (bool ok, uint8 reason) = claimStatus(requestHash, agentId, tag, minScore, maxAge);
        if (!ok) revert ClaimNotValidated(requestHash, reason);
        _;
    }
}
