"""API key authentication for SaaS users."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class APIKeyRecord(BaseModel):
    """A stored API key record."""

    key_id: str
    key_hash: str
    user_id: str
    tier: str = "starter"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: datetime | None = None
    is_active: bool = True
    rate_limit_rpm: int = 60
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthManager:
    """Manages API key authentication for the SaaS platform.

    In production, this would be backed by a database. For now, it uses
    an in-memory store suitable for development and testing.
    """

    def __init__(self) -> None:
        self._keys: dict[str, APIKeyRecord] = {}

    def create_api_key(
        self,
        user_id: str,
        tier: str = "starter",
        rate_limit_rpm: int = 60,
    ) -> tuple[str, APIKeyRecord]:
        """Generate a new API key for a user.

        Args:
            user_id: The user's unique identifier.
            tier: Pricing tier (starter, professional, enterprise).
            rate_limit_rpm: Requests per minute limit.

        Returns:
            Tuple of (raw_api_key, record). The raw key is shown only once.
        """
        raw_key = f"dde_{secrets.token_urlsafe(32)}"
        key_id = f"key_{secrets.token_hex(8)}"
        key_hash = self._hash_key(raw_key)

        record = APIKeyRecord(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            tier=tier,
            rate_limit_rpm=rate_limit_rpm,
        )
        self._keys[key_id] = record

        return raw_key, record

    def validate_key(self, raw_key: str) -> APIKeyRecord | None:
        """Validate an API key and return its record if valid.

        Args:
            raw_key: The raw API key from the request header.

        Returns:
            The key record if valid, None otherwise.
        """
        if not raw_key.startswith("dde_"):
            return None

        target_hash = self._hash_key(raw_key)

        for record in self._keys.values():
            if hmac.compare_digest(record.key_hash, target_hash):
                if not record.is_active:
                    return None
                record.last_used = datetime.utcnow()
                return record

        return None

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key.

        Args:
            key_id: The key ID to revoke.

        Returns:
            True if the key was found and revoked, False otherwise.
        """
        record = self._keys.get(key_id)
        if record is None:
            return False
        record.is_active = False
        return True

    def get_user_keys(self, user_id: str) -> list[APIKeyRecord]:
        """Get all API keys for a user.

        Args:
            user_id: The user's unique identifier.

        Returns:
            List of API key records (without raw keys).
        """
        return [r for r in self._keys.values() if r.user_id == user_id]

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        """Hash an API key using SHA-256."""
        return hashlib.sha256(raw_key.encode()).hexdigest()
