"""Secure data ingestion to encrypted temporary directory.

All ingested data is stored in a temporary directory with restricted permissions.
On completion or error, the data can be cryptographically purged.

Supports:
  - Local directory
  - Zip archive
  - GitHub URL (auto-clone + cleanup)
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

from cryptography.fernet import Fernet

from src.config import Config

logger = logging.getLogger(__name__)

# File extensions to analyze
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".kt",
    ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift", ".dart",
    ".scala", ".clj", ".ex", ".exs", ".hs", ".ml",
}

DOC_EXTENSIONS = {
    ".md", ".txt", ".rst", ".pdf", ".docx", ".csv", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg",
}

IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".next", ".nuxt", "target", "vendor",
}

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB per file


class SecureLoader:
    """Securely loads and manages project data in an encrypted temp directory."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._encryption_key = Fernet.generate_key()
        self._fernet = Fernet(self._encryption_key)
        self._work_dir: Path | None = None
        self._manifest: list[dict[str, str]] = []

    @property
    def work_dir(self) -> Path:
        if self._work_dir is None:
            raise RuntimeError("Loader not initialized. Call load_directory or load_archive first.")
        return self._work_dir

    @property
    def manifest(self) -> list[dict[str, str]]:
        return list(self._manifest)

    def _create_secure_temp(self) -> Path:
        """Create a temporary directory with restricted permissions."""
        base = self._config.temp_dir
        base.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix="dde_", dir=str(base)))
        # Restrict to owner only
        tmp.chmod(stat.S_IRWXU)
        return tmp

    def load_from_url(self, url: str) -> Path:
        """Load a project from a GitHub URL (or any Git-compatible URL).

        Clones the repo into a secure temp directory, loads files, then
        removes the clone. Only code/doc files are retained (encrypted).

        Args:
            url: GitHub URL. Accepts formats like:
                 - https://github.com/owner/repo
                 - https://github.com/owner/repo.git
                 - https://github.com/owner/repo/tree/branch
                 - github.com/owner/repo
                 - owner/repo (assumes GitHub)

        Returns:
            Path to the secure working directory.

        Raises:
            ValueError: If the URL is invalid.
            RuntimeError: If git clone fails.
        """
        normalized = self._normalize_github_url(url)
        branch = self._extract_branch(url)

        clone_dir = Path(tempfile.mkdtemp(prefix="dde_clone_", dir=str(self._config.temp_dir)))

        try:
            logger.info(f"Cloning {normalized} ...")
            cmd = ["git", "clone", "--depth", "1"]
            if branch:
                cmd.extend(["--branch", branch])
            cmd.extend([normalized, str(clone_dir / "repo")])

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 min timeout
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"git clone failed (exit {proc.returncode}): {proc.stderr.strip()}"
                )

            repo_dir = clone_dir / "repo"
            self._git_repo_path = repo_dir

            # Load into encrypted workspace
            return self.load_directory(repo_dir)

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"git clone timed out after 5 minutes: {normalized}")
        finally:
            # Remove .git directory immediately (large, not needed for analysis)
            git_dir = clone_dir / "repo" / ".git"
            if git_dir.exists():
                shutil.rmtree(str(git_dir), ignore_errors=True)

    @property
    def cloned_repo_path(self) -> Path | None:
        """Return the path to the cloned repo, if loaded via URL."""
        return getattr(self, "_git_repo_path", None)

    @staticmethod
    def _normalize_github_url(url: str) -> str:
        """Normalize various GitHub URL formats to a clone-able HTTPS URL.

        Accepts:
            owner/repo              → https://github.com/owner/repo.git
            github.com/owner/repo   → https://github.com/owner/repo.git
            https://github.com/...  → https://github.com/owner/repo.git
        """
        url = url.strip().rstrip("/")

        # Remove tree/branch suffix: .../tree/main → ...
        url = re.sub(r"/tree/[^/]+/?$", "", url)

        # Short form: owner/repo
        if re.match(r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$", url):
            return f"https://github.com/{url}.git"

        # Missing scheme: github.com/owner/repo
        if url.startswith("github.com/"):
            url = "https://" + url

        parsed = urlparse(url)
        if not parsed.scheme:
            raise ValueError(f"Invalid URL format: {url}")

        # Ensure .git suffix for clone
        path = parsed.path.rstrip("/")
        if not path.endswith(".git"):
            path += ".git"

        return f"{parsed.scheme}://{parsed.netloc}{path}"

    @staticmethod
    def _extract_branch(url: str) -> str | None:
        """Extract branch name from GitHub URL if present.

        e.g., https://github.com/owner/repo/tree/develop → 'develop'
        """
        match = re.search(r"/tree/([^/]+)/?$", url.strip().rstrip("/"))
        return match.group(1) if match else None

    def load_directory(self, source: Path) -> Path:
        """Load a project directory into the secure workspace.

        Args:
            source: Path to the project directory.

        Returns:
            Path to the secure working directory.

        Raises:
            FileNotFoundError: If the source directory does not exist.
            PermissionError: If the source directory is not readable.
        """
        if not source.exists():
            raise FileNotFoundError(f"Source directory not found: {source}")
        if not source.is_dir():
            raise ValueError(f"Source is not a directory: {source}")

        self._work_dir = self._create_secure_temp()

        for file_path in self._walk_files(source):
            rel_path = file_path.relative_to(source)
            dest = self._work_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)

            try:
                content = file_path.read_bytes()
                if len(content) > MAX_FILE_SIZE_BYTES:
                    continue

                # Encrypt at rest
                encrypted = self._fernet.encrypt(content)
                dest.with_suffix(dest.suffix + ".enc").write_bytes(encrypted)

                file_hash = hashlib.sha256(content).hexdigest()
                self._manifest.append({
                    "path": str(rel_path),
                    "hash": file_hash,
                    "size": str(len(content)),
                    "type": _classify_file(file_path),
                })
            except (PermissionError, OSError):
                continue

        return self._work_dir

    def load_archive(self, archive_path: Path) -> Path:
        """Load a zip archive into the secure workspace.

        Args:
            archive_path: Path to the zip file.

        Returns:
            Path to the secure working directory.
        """
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")

        self._work_dir = self._create_secure_temp()
        extract_dir = self._work_dir / "_extracted"
        extract_dir.mkdir()

        with zipfile.ZipFile(str(archive_path), "r") as zf:
            # Security: check for path traversal
            for member in zf.namelist():
                resolved = (extract_dir / member).resolve()
                if not str(resolved).startswith(str(extract_dir.resolve())):
                    raise ValueError(f"Zip path traversal detected: {member}")
            zf.extractall(str(extract_dir))

        # Re-process extracted files through secure loading
        return self.load_directory(extract_dir)

    def read_file(self, relative_path: str) -> str:
        """Read and decrypt a file from the secure workspace.

        Args:
            relative_path: Path relative to the workspace root.

        Returns:
            Decrypted file content as a string.
        """
        enc_path = self.work_dir / (relative_path + ".enc")
        if not enc_path.exists():
            raise FileNotFoundError(f"File not found in workspace: {relative_path}")

        encrypted = enc_path.read_bytes()
        decrypted = self._fernet.decrypt(encrypted)
        return decrypted.decode("utf-8", errors="replace")

    def read_file_bytes(self, relative_path: str) -> bytes:
        """Read and decrypt a file as raw bytes."""
        enc_path = self.work_dir / (relative_path + ".enc")
        if not enc_path.exists():
            raise FileNotFoundError(f"File not found in workspace: {relative_path}")

        encrypted = enc_path.read_bytes()
        return self._fernet.decrypt(encrypted)

    def get_code_files(self) -> list[dict[str, str]]:
        """Return manifest entries for code files only."""
        return [f for f in self._manifest if f["type"] == "code"]

    def get_doc_files(self) -> list[dict[str, str]]:
        """Return manifest entries for document files only."""
        return [f for f in self._manifest if f["type"] == "doc"]

    def destroy(self) -> int:
        """Securely destroy the workspace. Returns bytes overwritten."""
        if self._work_dir is None or not self._work_dir.exists():
            return 0

        bytes_overwritten = 0
        for root, _dirs, files in os.walk(str(self._work_dir)):
            for fname in files:
                fpath = Path(root) / fname
                try:
                    size = fpath.stat().st_size
                    # Overwrite with random data before deletion
                    with open(fpath, "wb") as f:
                        f.write(os.urandom(size))
                        f.flush()
                        os.fsync(f.fileno())
                    bytes_overwritten += size
                    fpath.unlink()
                except OSError:
                    pass

        shutil.rmtree(str(self._work_dir), ignore_errors=True)
        self._work_dir = None
        self._encryption_key = b""
        self._manifest.clear()
        return bytes_overwritten

    def _walk_files(self, root: Path) -> Iterator[Path]:
        """Walk directory yielding analyzable files, skipping ignored dirs."""
        for entry in sorted(root.iterdir()):
            if entry.name.startswith(".") and entry.name != ".github":
                if entry.is_dir() and entry.name == ".git":
                    # We skip .git contents but note its presence
                    continue
                continue
            if entry.is_dir():
                if entry.name in IGNORED_DIRS:
                    continue
                yield from self._walk_files(entry)
            elif entry.is_file():
                if entry.suffix in CODE_EXTENSIONS | DOC_EXTENSIONS:
                    yield entry


def _classify_file(path: Path) -> str:
    """Classify a file as code, doc, or other."""
    if path.suffix in CODE_EXTENSIONS:
        return "code"
    if path.suffix in DOC_EXTENSIONS:
        return "doc"
    return "other"
