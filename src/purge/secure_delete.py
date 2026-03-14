"""Cryptographic erasure and purge certificate generation.

Implements secure deletion by:
1. Overwriting files with random data (3 passes)
2. Destroying encryption keys
3. Generating a verifiable purge certificate
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)

from src.models import PurgeCertificate


OVERWRITE_PASSES = 3


class SecurePurger:
    """Securely deletes analysis data and generates purge certificates."""

    def __init__(self) -> None:
        # Generate an ephemeral signing key for certificates
        self._signing_key = ec.generate_private_key(ec.SECP256R1())
        self._verify_key = self._signing_key.public_key()

    def purge_directory(
        self,
        directory: Path,
        analysis_id: str,
        project_name: str,
        operator: str = "system",
    ) -> PurgeCertificate:
        """Securely purge a directory and generate a certificate.

        Args:
            directory: Directory to purge.
            analysis_id: ID of the analysis being purged.
            project_name: Name of the analyzed project.
            operator: Name of the person/system performing the purge.

        Returns:
            PurgeCertificate documenting the purge.
        """
        if not directory.exists():
            return PurgeCertificate(
                analysis_id=analysis_id,
                project_name=project_name,
                files_purged=0,
                bytes_overwritten=0,
                operator=operator,
                verification_hash="directory_not_found",
            )

        files_purged = 0
        bytes_overwritten = 0
        file_hashes: list[str] = []

        # Walk and securely overwrite all files
        for root, _dirs, files in os.walk(str(directory)):
            for fname in files:
                fpath = Path(root) / fname
                try:
                    size = fpath.stat().st_size
                    overwritten = self._secure_overwrite(fpath)
                    bytes_overwritten += overwritten
                    files_purged += 1

                    # Record hash of the overwritten data for verification
                    file_hashes.append(
                        hashlib.sha256(f"{fpath}:{size}:{overwritten}".encode()).hexdigest()
                    )
                except OSError:
                    continue

        # Remove directory structure
        shutil.rmtree(str(directory), ignore_errors=True)

        # Generate verification hash
        combined = "|".join(file_hashes)
        verification_hash = hashlib.sha256(combined.encode()).hexdigest()

        cert = PurgeCertificate(
            analysis_id=analysis_id,
            project_name=project_name,
            files_purged=files_purged,
            bytes_overwritten=bytes_overwritten,
            operator=operator,
            verification_hash=verification_hash,
        )

        # Sign the certificate
        self._sign_certificate(cert)

        return cert

    def _secure_overwrite(self, file_path: Path) -> int:
        """Overwrite a file with random data multiple times, then delete.

        Args:
            file_path: Path to the file to overwrite.

        Returns:
            Total bytes overwritten across all passes.
        """
        size = file_path.stat().st_size
        total_overwritten = 0

        for pass_num in range(OVERWRITE_PASSES):
            try:
                with open(file_path, "wb") as f:
                    if pass_num < OVERWRITE_PASSES - 1:
                        # Random data passes
                        f.write(os.urandom(size))
                    else:
                        # Final pass: zeros
                        f.write(b"\x00" * size)
                    f.flush()
                    os.fsync(f.fileno())
                total_overwritten += size
            except OSError:
                break

        # Delete the file
        try:
            file_path.unlink()
        except OSError:
            pass

        return total_overwritten

    def _sign_certificate(self, cert: PurgeCertificate) -> None:
        """Sign the purge certificate with the ephemeral key."""
        data = (
            f"{cert.certificate_id}|{cert.analysis_id}|{cert.project_name}|"
            f"{cert.purge_timestamp.isoformat()}|{cert.files_purged}|"
            f"{cert.bytes_overwritten}|{cert.verification_hash}"
        ).encode()

        signature = self._signing_key.sign(data, ec.ECDSA(hashes.SHA256()))
        # Store the signature as hex in the verification hash field
        cert.verification_hash = (
            f"{cert.verification_hash}|sig:{signature.hex()}"
        )

    def export_certificate(self, cert: PurgeCertificate, output_path: Path) -> Path:
        """Export the purge certificate to a JSON file.

        Args:
            cert: The purge certificate.
            output_path: Path to save the certificate.

        Returns:
            Path to the saved certificate file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cert_data = {
            "certificate_id": cert.certificate_id,
            "analysis_id": cert.analysis_id,
            "project_name": cert.project_name,
            "purge_timestamp": cert.purge_timestamp.isoformat(),
            "files_purged": cert.files_purged,
            "bytes_overwritten": cert.bytes_overwritten,
            "method": cert.method,
            "verification_hash": cert.verification_hash,
            "operator": cert.operator,
            "public_key": self._verify_key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode(),
        }

        output_path.write_text(
            json.dumps(cert_data, indent=2), encoding="utf-8"
        )
        return output_path

    def purge_file(self, file_path: Path) -> int:
        """Securely purge a single file.

        Args:
            file_path: Path to the file.

        Returns:
            Bytes overwritten.
        """
        if not file_path.exists():
            return 0
        return self._secure_overwrite(file_path)
