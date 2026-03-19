"""Firebase Auth トークン検証ミドルウェア。

Google Sign-InのID tokenをサーバーサイドで検証する。
未ログインユーザーも許可するOptional依存として使用。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)


@dataclass
class FirebaseUser:
    """検証済みFirebaseユーザー情報。"""
    uid: str
    email: str
    display_name: str
    photo_url: str | None = None


async def verify_firebase_token(
    authorization: str | None = Header(None),
) -> FirebaseUser | None:
    """Bearer tokenからFirebase ID tokenを検証。

    未ログインの場合はNoneを返す（Optional依存）。
    バルク購入など認証必須のエンドポイントでは別途チェックする。

    Args:
        authorization: "Bearer <id_token>" 形式のAuthorizationヘッダー

    Returns:
        FirebaseUser または None（未ログイン）
    """
    if not authorization:
        return None

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    id_token = parts[1]
    try:
        from src.saas.firestore_client import _ensure_initialized
        _ensure_initialized()

        from firebase_admin import auth as firebase_auth
        decoded = firebase_auth.verify_id_token(id_token)

        return FirebaseUser(
            uid=decoded["uid"],
            email=decoded.get("email", ""),
            display_name=decoded.get("name", decoded.get("email", "")),
            photo_url=decoded.get("picture"),
        )
    except Exception as e:
        logger.warning(f"Firebase token verification failed: {e}")
        return None


async def require_firebase_auth(
    authorization: str | None = Header(None),
) -> FirebaseUser:
    """認証必須のエンドポイント用。未認証なら401を返す。"""
    user = await verify_firebase_token(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required. Please sign in with Google.")
    return user
