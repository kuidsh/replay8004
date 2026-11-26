import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_lambda_package_holds_only_code_and_requirements(tmp_path):
    spec = importlib.util.spec_from_file_location("build_lambda", ROOT / "scripts" / "build_lambda.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = mod.stage(tmp_path / "lambda")
    assert sorted(p.name for p in out.iterdir()) == ["replay8004", "requirements.txt"]
    assert {p.suffix for p in out.rglob("*") if p.is_file()} == {".py", ".txt"}
    assert (out / "replay8004" / "lambda_handler.py").exists()
    reqs = (out / "requirements.txt").read_text()
    assert "eth-abi" in reqs and "eth-account" in reqs and "eth-hash" in reqs


def test_template_uses_the_staged_folder():
    assert "CodeUri: ../build/lambda\n" in (ROOT / "infra" / "template.yaml").read_text(encoding="utf-8")


def test_every_role_the_stack_creates_can_take_the_boundary():
    t = (ROOT / "infra" / "template.yaml").read_text(encoding="utf-8")
    assert t.count("PermissionsBoundary: !If [HasBoundary, !Ref PermissionsBoundaryArn, !Ref AWS::NoValue]") == 2
    assert 'FunctionName: !Sub "${AWS::StackName}-worker"' in t   # names match the replay8004-* IAM scopes
    assert 'Name: !Sub "${AWS::StackName}-every-minute"' in t
    assert t.index("  WorkerLogs:") < t.index("  WorkerFunction:")   # log group exists before the first run


def test_iam_policies_are_valid_and_carry_no_account_id():
    import json
    import re
    for f in ("boundary-policy.json", "deployer-policy.json", "deployer-extra-policy.json"):
        text = (ROOT / "infra" / "iam" / f).read_text(encoding="utf-8")
        doc = json.loads(text)
        assert doc["Version"] == "2012-10-17" and doc["Statement"]
        assert not re.search(r"\b\d{12}\b", text)            # ${AWS_ACCOUNT_ID} placeholder only
        assert len(json.dumps(doc, separators=(",", ":")).replace("${AWS_ACCOUNT_ID}", "0" * 12)) <= 6144


def _template():
    from cfnlint.decode import decode
    tpl, errs = decode(str(ROOT / "infra" / "template.yaml"))
    assert not errs
    return tpl


def test_every_taggable_resource_is_tagged_and_named_in_outputs():
    res = _template()["Resources"]
    for name in ("EvidenceBucket", "StateTable", "WorkerLogs"):
        tags = {t["Key"]: t["Value"] for t in res[name]["Properties"]["Tags"]}
        assert tags["Project"] == "replay8004" and "Stack" in tags, name
    assert res["WorkerFunction"]["Properties"]["Tags"]["Project"] == "replay8004"
    outs = _template()["Outputs"]
    for k in ("EvidenceBucketName", "StateTableName", "WorkerFunctionName", "WorkerLogGroupName", "ScheduleName",
              "WorkerRoleName", "SchedulerRoleName"):
        assert k in outs, k


def test_locked_evidence_bucket_does_not_block_stack_deletion():
    b = _template()["Resources"]["EvidenceBucket"]
    assert b["DeletionPolicy"] == "Retain" and b["UpdateReplacePolicy"] == "Retain"


def test_retention_parameter_reaches_the_lambda():
    t = _template()
    env = t["Resources"]["WorkerFunction"]["Properties"]["Environment"]["Variables"]
    assert env["EVIDENCE_RETENTION_DAYS"] == {"Ref": "EvidenceRetentionDays"}
    assert t["Parameters"]["EvidenceRetentionDays"]["MinValue"] == 1
    src = (ROOT / "replay8004" / "lambda_handler.py").read_text(encoding="utf-8")
    assert 'retain_days=int(os.environ.get("EVIDENCE_RETENTION_DAYS", "365"))' in src
    assert "@functools.lru_cache(maxsize=1)\ndef _secret(" in src


def test_no_reserved_concurrency():
    # new accounts have a concurrency quota of 10 and AWS keeps 10 unreserved, so any reservation fails to deploy
    # (CREATE_FAILED on 2026-11-27). Exactly-once comes from the conditional state write + on-chain check instead.
    assert "ReservedConcurrentExecutions" not in _template()["Resources"]["WorkerFunction"]["Properties"]


def test_schedule_does_not_retry_failed_runs():
    ev = _template()["Resources"]["WorkerFunction"]["Properties"]["Events"]["EveryMinute"]["Properties"]
    assert ev["RetryPolicy"] == {"MaximumRetryAttempts": 0}
