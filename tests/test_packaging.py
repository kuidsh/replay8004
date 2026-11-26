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
    for f in ("boundary-policy.json", "deployer-policy.json"):
        text = (ROOT / "infra" / "iam" / f).read_text(encoding="utf-8")
        doc = json.loads(text)
        assert doc["Version"] == "2012-10-17" and doc["Statement"]
        assert not re.search(r"\b\d{12}\b", text)            # ${AWS_ACCOUNT_ID} placeholder only
        assert len(json.dumps(doc, separators=(",", ":")).replace("${AWS_ACCOUNT_ID}", "0" * 12)) <= 6144
