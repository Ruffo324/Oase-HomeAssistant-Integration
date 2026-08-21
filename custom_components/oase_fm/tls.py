"""Ephemeral EasyControl-compatible TLS server certificate."""

from __future__ import annotations

import datetime
from pathlib import Path
import ssl

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

_CERT_NAME = "oase-easycontrol-cert.pem"
_KEY_NAME = "oase-easycontrol-key.pem"
_COMMON_NAME = "com.oase.easycontrol"


def create_server_context(directory: Path) -> ssl.SSLContext:
    """Create or reuse the local self-signed TLS 1.2 identity EasyControl expects."""
    directory.mkdir(parents=True, exist_ok=True)
    cert_path = directory / _CERT_NAME
    key_path = directory / _KEY_NAME
    if not cert_path.exists() or not key_path.exists():
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, _COMMON_NAME)])
        now = datetime.datetime.now(datetime.UTC)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=3650))
            .sign(private_key, hashes.SHA256())
        )
        key_path.write_bytes(
            private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )
        cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        key_path.chmod(0o600)
        cert_path.chmod(0o600)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert_path, key_path)
    return context
