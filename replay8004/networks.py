"""Celo networks and the ERC-8004 registry addresses (erc-8004-contracts scripts/addresses.ts, read 2026-11-20)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Network:
    name: str
    chain_id: int
    rpc: str
    identity: str
    reputation: str
    validation: str
    explorer: str
    mainnet: bool


CELO_SEPOLIA = Network(
    "celo-sepolia", 11142220, "https://forno.celo-sepolia.celo-testnet.org",
    identity="0x8004A818BFB912233c491871b3d84c89A494BD9e",
    reputation="0x8004B663056A597Dffe9eCcC1965A193B7388713",
    validation="0x8004Cb1BF31DAf7788923b405b754f57acEB4272",
    explorer="https://celo-sepolia.blockscout.com", mainnet=False)

CELO_MAINNET = Network(
    "celo-mainnet", 42220, "https://forno.celo.org",
    identity="0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
    reputation="0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
    validation="0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58",
    explorer="https://celoscan.io", mainnet=True)

NETWORKS = {n.name: n for n in (CELO_SEPOLIA, CELO_MAINNET)}


def get(name: str, allow_mainnet: bool = False) -> Network:
    net = NETWORKS[name]
    if net.mainnet and not allow_mainnet:
        raise RuntimeError("mainnet is off by default. The operator enables it with "
                           "REPLAY8004_ALLOW_MAINNET=1 after reviewing the code and funding the validator key.")
    return net
