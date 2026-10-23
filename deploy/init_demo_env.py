"""Explicit, opt-in local DEMO configuration; never overwrites an existing file."""

import argparse
from pathlib import Path
import re
import secrets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", required=True, action="store_true")
    parser.add_argument("--project", default="printtrack-demo")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", args.project):
        parser.error("Invalid Compose project name")
    path = Path(__file__).resolve().parents[1] / ".env"
    if path.exists():
        print("Existing .env preserved.")
        return
    content = f"POSTGRES_PASSWORD={secrets.token_hex(24)}\nADMIN_USERNAME=admin\nADMIN_PASSWORD={secrets.token_hex(24)}\nDEMO_MODE=true\nCOMPOSE_PROJECT_NAME={args.project}\nHOST_BIND=127.0.0.1\nAPP_PORT=8080\nCOOKIE_SECURE=false\n"
    with path.open("x", encoding="utf-8") as file:
        file.write(content)
    path.chmod(0o600)
    print(
        "Local DEMO .env created. Credentials are in .env; do not commit or share them."
    )


if __name__ == "__main__":
    main()
