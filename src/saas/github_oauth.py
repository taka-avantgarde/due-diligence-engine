"""GitHub OAuth integration for private repository access.

Implements the full OAuth App flow:
1. Redirect user to GitHub authorization URL
2. Handle callback with authorization code
3. Exchange code for access token
4. List and clone private repositories
5. Revoke access and disconnect

All tokens are encrypted at rest using Fernet and stored in-memory only
(never persisted to disk) for NDA compliance.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import httpx
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# GitHub OAuth endpoints
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE = "https://api.github.com"

# Required scopes for private repo access
DEFAULT_SCOPES = "repo read:user"


@dataclass
class GitHubConnection:
    """Represents an authenticated GitHub connection.

    Fields:
        connection_id: Unique identifier for this connection.
        user_id: Internal user identifier.
        github_username: The GitHub username of the connected account.
        repo_full_name: Full name of the selected repository (owner/repo), if any.
        encrypted_token: Fernet-encrypted access token (never stored in plaintext).
        connected_at: Timestamp when the connection was established.
        expires_at: Token expiration timestamp, if applicable.
    """

    connection_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    user_id: str = ""
    github_username: str = ""
    repo_full_name: str = ""
    encrypted_token: bytes = b""
    connected_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None


class GitHubOAuthManager:
    """Manages GitHub OAuth flows and token lifecycle.

    All tokens are encrypted using Fernet and stored only in-memory.
    No token data is ever written to disk.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        """Initialize the OAuth manager.

        Args:
            client_id: GitHub OAuth App client ID.
            client_secret: GitHub OAuth App client secret.
            redirect_uri: OAuth callback URL (e.g., http://localhost:8000/api/github/callback).
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

        # Fernet encryption for tokens at rest (in-memory only)
        self._encryption_key = Fernet.generate_key()
        self._fernet = Fernet(self._encryption_key)

        # In-memory storage: connection_id -> GitHubConnection
        self._connections: dict[str, GitHubConnection] = {}

        # CSRF state tokens: state -> user_id
        self._pending_states: dict[str, str] = {}

    def get_authorization_url(self, user_id: str) -> tuple[str, str]:
        """Generate the GitHub OAuth authorization URL.

        Args:
            user_id: Internal user identifier to associate with this flow.

        Returns:
            Tuple of (authorization_url, state_token).
        """
        state = secrets.token_urlsafe(32)
        self._pending_states[state] = user_id

        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "scope": DEFAULT_SCOPES,
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{GITHUB_AUTHORIZE_URL}?{query}"

        return url, state

    async def handle_callback(
        self, code: str, state: str
    ) -> GitHubConnection:
        """Handle the OAuth callback and exchange code for token.

        Args:
            code: Authorization code from GitHub.
            state: CSRF state token for verification.

        Returns:
            GitHubConnection with encrypted access token.

        Raises:
            ValueError: If state is invalid or token exchange fails.
        """
        user_id = self._pending_states.pop(state, None)
        if user_id is None:
            raise ValueError("Invalid or expired OAuth state token")

        # Exchange authorization code for access token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "redirect_uri": self._redirect_uri,
                    "state": state,
                },
                headers={"Accept": "application/json"},
            )

        if response.status_code != 200:
            raise ValueError(f"GitHub token exchange failed: HTTP {response.status_code}")

        token_data = response.json()
        if "error" in token_data:
            raise ValueError(
                f"GitHub OAuth error: {token_data.get('error_description', token_data['error'])}"
            )

        access_token = token_data["access_token"]

        # Fetch user profile
        github_username = await self._get_github_username(access_token)

        # Encrypt token before storing
        encrypted_token = self._fernet.encrypt(access_token.encode("utf-8"))

        # Compute expiration if provided
        expires_at = None
        if "expires_in" in token_data:
            expires_at = datetime.utcnow() + timedelta(seconds=int(token_data["expires_in"]))

        connection = GitHubConnection(
            user_id=user_id,
            github_username=github_username,
            encrypted_token=encrypted_token,
            expires_at=expires_at,
        )

        self._connections[connection.connection_id] = connection
        logger.info(f"GitHub connection established for user {user_id} ({github_username})")

        return connection

    async def list_repos(self, connection_id: str) -> list[dict[str, Any]]:
        """List repositories accessible to the connected GitHub account.

        Includes both public and private repos the user granted access to.

        Args:
            connection_id: ID of the GitHub connection.

        Returns:
            List of repository metadata dicts with keys:
            full_name, private, description, language, stargazers_count,
            updated_at, default_branch.

        Raises:
            ValueError: If connection_id is invalid.
        """
        token = self._decrypt_token(connection_id)

        repos: list[dict[str, Any]] = []
        page = 1
        per_page = 100

        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    f"{GITHUB_API_BASE}/user/repos",
                    params={
                        "visibility": "all",
                        "sort": "updated",
                        "per_page": per_page,
                        "page": page,
                    },
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )

                if response.status_code != 200:
                    logger.error(f"GitHub API error listing repos: {response.status_code}")
                    break

                page_repos = response.json()
                if not page_repos:
                    break

                for repo in page_repos:
                    repos.append({
                        "full_name": repo["full_name"],
                        "private": repo["private"],
                        "description": repo.get("description", ""),
                        "language": repo.get("language", ""),
                        "stargazers_count": repo.get("stargazers_count", 0),
                        "updated_at": repo.get("updated_at", ""),
                        "default_branch": repo.get("default_branch", "main"),
                    })

                page += 1
                if len(page_repos) < per_page:
                    break

        return repos

    def get_clone_url(self, connection_id: str, repo_full_name: str) -> str:
        """Generate an authenticated clone URL for a private repository.

        Args:
            connection_id: ID of the GitHub connection.
            repo_full_name: Full repository name (owner/repo).

        Returns:
            HTTPS clone URL with embedded access token.
        """
        token = self._decrypt_token(connection_id)
        return f"https://x-access-token:{token}@github.com/{repo_full_name}.git"

    def set_repo(self, connection_id: str, repo_full_name: str) -> None:
        """Associate a specific repository with a connection.

        Args:
            connection_id: ID of the GitHub connection.
            repo_full_name: Full repository name (owner/repo).

        Raises:
            ValueError: If connection_id is invalid.
        """
        conn = self._connections.get(connection_id)
        if conn is None:
            raise ValueError(f"Unknown connection: {connection_id}")
        conn.repo_full_name = repo_full_name

    async def revoke_access(self, connection_id: str) -> bool:
        """Revoke the GitHub OAuth token and remove the connection.

        Calls the GitHub API to revoke the token, then removes all
        in-memory data associated with this connection.

        Args:
            connection_id: ID of the GitHub connection to revoke.

        Returns:
            True if revocation succeeded, False otherwise.
        """
        conn = self._connections.get(connection_id)
        if conn is None:
            logger.warning(f"Attempted to revoke unknown connection: {connection_id}")
            return False

        token = self._decrypt_token(connection_id)

        # Revoke the token via GitHub API
        revoked = False
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{GITHUB_API_BASE}/applications/{self._client_id}/token",
                    auth=(self._client_id, self._client_secret),
                    json={"access_token": token},
                    headers={"Accept": "application/vnd.github+json"},
                )
                revoked = response.status_code in (204, 200)
                if not revoked:
                    logger.warning(
                        f"GitHub token revocation returned HTTP {response.status_code}"
                    )
        except httpx.HTTPError as e:
            logger.error(f"Failed to revoke GitHub token: {e}")

        # Always remove from in-memory storage regardless of API result
        self._connections.pop(connection_id, None)
        logger.info(f"GitHub connection {connection_id} removed (API revoked: {revoked})")

        return revoked

    def get_connection(self, connection_id: str) -> GitHubConnection | None:
        """Retrieve a connection by ID.

        Args:
            connection_id: ID of the GitHub connection.

        Returns:
            The GitHubConnection if found, None otherwise.
        """
        return self._connections.get(connection_id)

    def get_user_connections(self, user_id: str) -> list[GitHubConnection]:
        """List all connections for a given user.

        Args:
            user_id: Internal user identifier.

        Returns:
            List of GitHubConnection objects.
        """
        return [c for c in self._connections.values() if c.user_id == user_id]

    def _decrypt_token(self, connection_id: str) -> str:
        """Decrypt the access token for a connection.

        Args:
            connection_id: ID of the GitHub connection.

        Returns:
            Decrypted access token string.

        Raises:
            ValueError: If connection_id is invalid or token is corrupted.
        """
        conn = self._connections.get(connection_id)
        if conn is None:
            raise ValueError(f"Unknown connection: {connection_id}")

        try:
            return self._fernet.decrypt(conn.encrypted_token).decode("utf-8")
        except Exception as e:
            raise ValueError(f"Failed to decrypt token for connection {connection_id}: {e}")

    async def _get_github_username(self, access_token: str) -> str:
        """Fetch the authenticated user's GitHub username.

        Args:
            access_token: GitHub OAuth access token.

        Returns:
            GitHub username string.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )

        if response.status_code != 200:
            logger.warning(f"Failed to fetch GitHub user profile: HTTP {response.status_code}")
            return "unknown"

        return response.json().get("login", "unknown")
