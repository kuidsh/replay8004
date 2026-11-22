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
