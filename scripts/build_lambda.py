"""Stage the Lambda source in build/lambda: only the replay8004 package and its requirements.txt.

infra/template.yaml points CodeUri here, so `sam build` installs the dependencies and never packages local
files such as .env, .replay8004/ or the documents in the repo root. Run it before every `sam build`.
"""
import shutil
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def stage(out: Path = ROOT / "build" / "lambda") -> Path:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "replay8004", out / "replay8004", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
    (out / "requirements.txt").write_text("\n".join(deps) + "\n", encoding="utf-8", newline="\n")
    return out


if __name__ == "__main__":
    print(stage())
