"""AWS Lambda entry point: EventBridge runs it every minute (infra/template.yaml). Not deployed."""
from __future__ import annotations

import functools
import json
import os

from . import networks
from .evidence import S3Sink
from .registry import Sender
from .rpc import Rpc
from .store import DynamoStore
from .worker import Worker


@functools.lru_cache(maxsize=1)
def _secret(arn: str) -> str:  # pragma: no cover
    """Read once per warm container: every read costs money (US$0.05 per 10k). After rotating the key,
    update the function configuration so new containers start."""
    import boto3
    return boto3.client("secretsmanager").get_secret_value(SecretId=arn)["SecretString"].strip()


def handler(event, context):  # pragma: no cover - needs AWS
    net = networks.get(os.environ.get("NETWORK", "celo-sepolia"),
                       allow_mainnet=os.environ.get("REPLAY8004_ALLOW_MAINNET") == "1")
    rpc = Rpc(os.environ.get("RPC_URL", net.rpc))
    dry = os.environ.get("DRY_RUN", "1") == "1"
    sender = None if dry else Sender(rpc, net.chain_id, _secret(os.environ["VALIDATOR_KEY_SECRET_ARN"]))
    validator = sender.address if sender else os.environ["VALIDATOR_ADDRESS"]
    w = Worker(network=net, rpc=rpc, validator=validator, sender=sender,
               store=DynamoStore(os.environ["STATE_TABLE"], start_block=int(os.environ.get("START_BLOCK", "0")) or net.validation_deploy_block),
               sink=S3Sink(os.environ["EVIDENCE_BUCKET"], os.environ["EVIDENCE_BASE_URL"],
                           retain_days=int(os.environ.get("EVIDENCE_RETENTION_DAYS", "365"))))
    out = w.poll_once()
    print(json.dumps({k: v for k, v in out.items() if k != "answered"} | {"answered": len(out["answered"])}))
    return out
