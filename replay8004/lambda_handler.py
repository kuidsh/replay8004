"""AWS Lambda entry points: the worker (EventBridge, every minute) and the x402 paywall (only with PaidMode=1)."""
from __future__ import annotations

import functools
import json
import os

from . import networks
from .evidence import S3Sink
from .registry import Sender, verify_deployment
from .rpc import Rpc
from .store import DynamoStore
from .worker import Worker


@functools.lru_cache(maxsize=1)
def _secret(arn: str) -> str:  # pragma: no cover
    """Read once per warm container: every read costs money (US$0.05 per 10k). After rotating the key,
    update the function configuration so new containers start."""
    import boto3
    return boto3.client("secretsmanager").get_secret_value(SecretId=arn)["SecretString"].strip()


def make_sender(rpc, chain_id: int, key: str, expected_address: str) -> Sender:
    """Refuse to run with a key that doesn't belong to VALIDATOR_ADDRESS: it would watch for requests addressed
    to some other validator and never answer. The error names addresses only, never the key."""
    sender = Sender(rpc, chain_id, key)
    if sender.address.lower() != expected_address.lower():
        raise RuntimeError(f"the key in Secrets Manager belongs to {sender.address}, "
                           f"but VALIDATOR_ADDRESS is {expected_address}")
    return sender


def handler(event, context):  # pragma: no cover - needs AWS
    net = networks.get(os.environ.get("NETWORK", "celo-sepolia"),
                       allow_mainnet=os.environ.get("REPLAY8004_ALLOW_MAINNET") == "1")
    rpc = Rpc(os.environ.get("RPC_URL", net.rpc))
    dry = os.environ.get("DRY_RUN", "1") == "1"
    verify_deployment(rpc, net)  # raises before any key is loaded if the registry isn't the expected one
    sender = None if dry else make_sender(rpc, net.chain_id, _secret(os.environ["VALIDATOR_KEY_SECRET_ARN"]),
                                          os.environ["VALIDATOR_ADDRESS"])
    validator = sender.address if sender else os.environ["VALIDATOR_ADDRESS"]
    w = Worker(network=net, rpc=rpc, validator=validator, sender=sender,
               store=DynamoStore(os.environ["STATE_TABLE"], start_block=int(os.environ.get("START_BLOCK", "0")) or net.validation_deploy_block),
               sink=S3Sink(os.environ["EVIDENCE_BUCKET"], os.environ["EVIDENCE_BASE_URL"],
                           retain_days=int(os.environ.get("EVIDENCE_RETENTION_DAYS", "365"))),
               max_answers_per_day=int(os.environ.get("MAX_ANSWERS_PER_DAY", "20")),
               max_answers_per_agent_per_day=int(os.environ.get("MAX_ANSWERS_PER_AGENT_PER_DAY", "5")),
               billing=_billing_from_env())
    out = w.poll_once()
    print(json.dumps({k: v for k, v in out.items() if k != "answered"} | {"answered": len(out["answered"])}))
    return out


def _billing_from_env():
    """None unless PAID_MODE=1 (the default template value is 0: every request within the daily cap is answered)."""
    if os.environ.get("PAID_MODE", "0") != "1":
        return None
    from . import billing
    allow = frozenset(a for a in os.environ.get("FREE_ACCOUNTS", "").split(",") if a)
    plan = billing.Plan(free_per_month=int(os.environ.get("FREE_PER_MONTH", "25")), allowlist=allow)
    return billing.Billing(plan, DynamoStore(os.environ["STATE_TABLE"], key="ledger", default=billing.empty_ledger))


def paywall_handler(event, context):  # pragma: no cover - needs AWS
    """Lambda Function URL (auth NONE: x402 is the auth). Holds no key that can move funds."""
    from . import billing
    from .paywall import HttpFacilitator, Paywall
    net = networks.get(os.environ.get("NETWORK", "celo-sepolia"),
                       allow_mainnet=os.environ.get("REPLAY8004_ALLOW_MAINNET") == "1")
    key_arn = os.environ.get("FACILITATOR_KEY_SECRET_ARN", "")
    fac = HttpFacilitator(os.environ.get("FACILITATOR_URL", billing.FACILITATOR[net.name]),
                          _secret(key_arn) if key_arn else None)
    b = _billing_from_env()
    pw = Paywall(network=net, rpc=Rpc(os.environ.get("RPC_URL", net.rpc)),
                 ledger_store=DynamoStore(os.environ["STATE_TABLE"], key="ledger", default=billing.empty_ledger),
                 usage_store=DynamoStore(os.environ["STATE_TABLE"], key="worker"),
                 facilitator=fac, pay_to=os.environ["PAY_TO"], plan=b.plan if b else billing.Plan(),
                 base_url=os.environ.get("PUBLIC_URL", "https://validator.example"))
    return pw.handle(event)
