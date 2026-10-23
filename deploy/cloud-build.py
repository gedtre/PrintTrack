"""Optional Codex-only build adapter for a DNS-restricted proxy environment.

Normal local deployment uses `docker compose up --build -d` without this helper.
Existing proxy bindings are passed through Docker's standard proxy build args.
An existing trusted CA is mounted as a BuildKit secret; TLS remains verified.
"""

import argparse
import os
from pathlib import Path
import re
import socket
import subprocess
import tempfile
from urllib.parse import urlparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", args.project):
        parser.error("Invalid Compose project name")
    root = Path(__file__).resolve().parents[1]
    docker_env = {**os.environ}
    docker_env.setdefault(
        "DOCKER_CONFIG", str(Path(tempfile.gettempdir()) / "printtrack-docker")
    )
    cert = os.environ.get("SSL_CERT_FILE") or os.environ.get("NODE_EXTRA_CA_CERTS")
    if not cert or not Path(cert).is_file():
        parser.error(
            "An existing trusted CA file is required in SSL_CERT_FILE or NODE_EXTRA_CA_CERTS"
        )
    proxy = urlparse(
        os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    )
    if not proxy.hostname:
        parser.error("An existing HTTPS proxy binding is required")
    # Resolve only the proxy host through the environment's existing DNS route.
    proxy_ip = socket.gethostbyname(proxy.hostname)
    base = [
        "docker",
        "build",
        "--add-host",
        f"{proxy.hostname}:{proxy_ip}",
        "--secret",
        f"id=cloud_ca,src={cert}",
        "--build-arg",
        "HTTP_PROXY",
        "--build-arg",
        "HTTPS_PROXY",
        "--build-arg",
        "http_proxy",
        "--build-arg",
        "https_proxy",
    ]
    with tempfile.TemporaryDirectory(prefix="printtrack-build-") as directory:
        for service, context in [("backend", root / "backend"), ("frontend", root)]:
            source = (context / "Dockerfile").read_text()
            if service == "backend":
                source = source.replace(
                    "RUN pip install",
                    "RUN --mount=type=secret,id=cloud_ca PIP_CERT=/run/secrets/cloud_ca pip install",
                )
            else:
                source = source.replace(
                    "RUN npm ci",
                    "RUN --mount=type=secret,id=cloud_ca NODE_EXTRA_CA_CERTS=/run/secrets/cloud_ca npm ci",
                )
            dockerfile = Path(directory) / f"{service}.Dockerfile"
            dockerfile.write_text(source)
            subprocess.run(
                base
                + [
                    "-f",
                    str(dockerfile),
                    "-t",
                    f"{args.project}-{service}",
                    str(context),
                ],
                check=True,
                env=docker_env,
            )


if __name__ == "__main__":
    main()
