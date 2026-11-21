"""AWS Lambda entry point: EventBridge runs it every minute (infra/template.yaml). Not deployed."""
from __future__ import annotations

import json
import os

from . import networks
from .evidence import S3Sink
from .registry import Sender
from .rpc import Rpc
from .store import DynamoStore
from .worker import Worker


def _secret(arn: str) -> str:  # pragma: no cover
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
               sink=S3Sink(os.environ["EVIDENCE_BUCKET"], os.environ["EVIDENCE_BASE_URL"]))
    out = w.poll_once()
    print(json.dumps({k: v for k, v in out.items() if k != "answered"} | {"answered": len(out["answered"])}))
    return out
