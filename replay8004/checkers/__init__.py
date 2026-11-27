"""Checkers re-execute a claim against Celo state and return a Verdict.

A checker is pure apart from the RPC object it is given, so it can be tested with a fake chain.
Return None to mean "not decidable yet" (e.g. too few confirmations): the worker retries later
instead of posting a premature answer.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .erc20 import check_erc20_balance, check_erc20_transfer
from .read import check_contract_read
from .x402 import check_x402_settlement


@dataclass
class Verdict:
    score: int                      # 0..100, posted on-chain as `response`
    findings: list = field(default_factory=list)
    observed: dict = field(default_factory=dict)

    def __post_init__(self):
        if not 0 <= self.score <= 100:
            raise ValueError("score must be 0..100")


CHECKERS = {
    "erc20_transfer": check_erc20_transfer,
    "erc20_balance": check_erc20_balance,
    "contract_read": check_contract_read,
    "x402_settlement": check_x402_settlement,
}

TAGS = {k: f"replay:{k}" for k in CHECKERS}
