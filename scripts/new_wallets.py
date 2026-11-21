"""Create fresh TESTNET-ONLY wallets and show them on this terminal only.

Run it yourself in a terminal nobody else can see (not one an AI assistant reads):
    .venv\\Scripts\\python scripts\\new_wallets.py            # validator + test-agent-owner
    .venv/bin/python scripts/new_wallets.py name1 name2      # custom labels

Nothing is written to disk. Copy each key into your password manager, then clear the terminal.
Share only the addresses. Never fund these wallets with real money.
"""
import sys

from eth_account import Account


def main(names: list[str]) -> None:
    print("TESTNET ONLY. Store each key in your password manager; share only the addresses.\n")
    for name in names:
        acct = Account.create()
        print(f"{name}")
        print(f"  address  {acct.address}")
        print(f"  key      0x{acct.key.hex().removeprefix('0x')}\n")
    print("Done. Clear this terminal (cls / clear) and close it.")


if __name__ == "__main__":
    main(sys.argv[1:] or ["validator", "test-agent-owner"])
