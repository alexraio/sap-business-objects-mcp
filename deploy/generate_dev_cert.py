"""
Generates a self-signed TLS certificate + private key for DEVELOPMENT / TEST use of the
remote bo-mcp server over HTTPS. Works on Linux, macOS and Windows (no openssl binary needed).

Usage:
    uv run python deploy/generate_dev_cert.py --host bo-prod.example.com --host 10.0.0.12
    # -> certs/dev-cert.pem and certs/dev-key.pem

Server:
    uv run python server.py --transport streamable-http --host 0.0.0.0 --port 8443 \
        --ssl-certfile certs/dev-cert.pem --ssl-keyfile certs/dev-key.pem

Client (copy ONLY dev-cert.pem to the workstation, never the key):
    ... deploy/client_bridge.py --remote-url https://bo-prod.example.com:8443 --ca-file dev-cert.pem

For production use a certificate issued by your corporate CA instead.
"""

from __future__ import annotations

import argparse
import datetime
import ipaddress
import os
import sys
from pathlib import Path
from typing import List, Optional

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
except ImportError:  # pragma: no cover
    print("ERROR: the 'cryptography' package is required (run: uv add cryptography).", file=sys.stderr)
    raise SystemExit(1)


def _subject_alt_names(hosts: List[str]) -> List[x509.GeneralName]:
    names: List[x509.GeneralName] = []
    for host in hosts:
        try:
            names.append(x509.IPAddress(ipaddress.ip_address(host)))
        except ValueError:
            names.append(x509.DNSName(host))
    return names


def generate_self_signed_cert(
    hosts: List[str],
    cert_path: Path,
    key_path: Path,
    days: int = 365,
) -> None:
    """Writes a PEM certificate and unencrypted PEM private key (key file is chmod 600 on POSIX)."""
    all_hosts = list(dict.fromkeys(["localhost", "127.0.0.1", *hosts]))
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hosts[0] if hosts else "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=days))
        .add_extension(x509.SubjectAlternativeName(_subject_alt_names(all_hosts)), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    if os.name == "posix":
        os.chmod(key_path, 0o600)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a self-signed dev TLS certificate for bo-mcp")
    parser.add_argument(
        "--host",
        action="append",
        default=[],
        help="Hostname or IP the clients will use (repeatable). localhost/127.0.0.1 are always included.",
    )
    parser.add_argument("--days", type=int, default=365, help="Validity in days (default: 365)")
    parser.add_argument("--out-dir", default="certs", help="Output directory (default: ./certs)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    cert_path, key_path = out_dir / "dev-cert.pem", out_dir / "dev-key.pem"
    if not args.force and (cert_path.exists() or key_path.exists()):
        print(f"ERROR: {cert_path} or {key_path} already exists (use --force to overwrite).", file=sys.stderr)
        return 1

    generate_self_signed_cert(args.host, cert_path, key_path, args.days)
    print(f"Certificate: {cert_path}\nPrivate key: {key_path}  (keep secret, never commit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
