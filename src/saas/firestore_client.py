"""Firestoreクライアント — DDE専用（due-diligence-engineプロジェクト）。

ユーザー管理、チケット残高、購入履歴、レポート履歴を一元管理する。
Arcプロジェクトとは完全分離。
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import transaction as fs_transaction

from src.config import REPORT_TTL_DAYS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# シングルトン初期化
# ---------------------------------------------------------------------------

_app: firebase_admin.App | None = None
_db = None


def _ensure_initialized():
    """Firebase Admin SDKを初期化（1回のみ）。"""
    global _app, _db
    if _app is not None:
        return

    sa_path = os.environ.get("FIREBASE_SA_PATH", "")
    if sa_path and os.path.exists(sa_path):
        cred = credentials.Certificate(sa_path)
        _app = firebase_admin.initialize_app(cred)
    else:
        # Cloud Run上ではデフォルトクレデンシャルを使用
        _app = firebase_admin.initialize_app()

    _db = firestore.client()
    logger.info("Firebase Admin SDK initialized (project: due-diligence-engine)")


def get_db():
    """Firestoreクライアントを取得。"""
    _ensure_initialized()
    return _db


# ---------------------------------------------------------------------------
# ユーザー管理
# ---------------------------------------------------------------------------


def get_or_create_user(uid: str, email: str, display_name: str) -> dict[str, Any]:
    """ユーザーを取得、または新規作成。

    Args:
        uid: Firebase Auth UID
        email: メールアドレス
        display_name: 表示名

    Returns:
        ユーザードキュメントのdict
    """
    db = get_db()
    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()

    if user_doc.exists:
        # 最終ログイン更新
        user_ref.update({"updated_at": datetime.now(timezone.utc)})
        return user_doc.to_dict()

    # 新規作成
    user_data = {
        "email": email,
        "display_name": display_name,
        "ticket_balance": 0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    user_ref.set(user_data)
    logger.info(f"New user created: {uid} ({email})")
    return user_data


def get_user(uid: str) -> dict[str, Any] | None:
    """ユーザー情報を取得。"""
    db = get_db()
    doc = db.collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None


def get_ticket_balance(uid: str) -> int:
    """チケット残高を取得。"""
    user = get_user(uid)
    return user.get("ticket_balance", 0) if user else 0


# ---------------------------------------------------------------------------
# チケット管理（トランザクション使用）
# ---------------------------------------------------------------------------


def add_tickets(uid: str, count: int, purchase_id: str) -> int:
    """チケットをユーザーに付与（Firestoreトランザクション）。

    Args:
        uid: Firebase Auth UID
        count: 追加チケット数
        purchase_id: 購入ID

    Returns:
        新しいチケット残高
    """
    db = get_db()
    user_ref = db.collection("users").document(uid)

    @firestore.transactional
    def _add_in_transaction(txn, ref):
        doc = ref.get(transaction=txn)
        if not doc.exists:
            raise ValueError(f"User {uid} not found")
        current = doc.to_dict().get("ticket_balance", 0)
        new_balance = current + count
        txn.update(ref, {
            "ticket_balance": new_balance,
            "updated_at": datetime.now(timezone.utc),
        })
        return new_balance

    txn = db.transaction()
    new_balance = _add_in_transaction(txn, user_ref)
    logger.info(f"Tickets added: uid={uid}, +{count}, balance={new_balance}")
    return new_balance


def use_ticket(uid: str, report_id: str) -> bool:
    """チケットを1枚消費（Firestoreトランザクション）。

    Args:
        uid: Firebase Auth UID
        report_id: 紐づけるレポートID

    Returns:
        消費成功かどうか
    """
    db = get_db()
    user_ref = db.collection("users").document(uid)

    @firestore.transactional
    def _use_in_transaction(txn, ref):
        doc = ref.get(transaction=txn)
        if not doc.exists:
            return False
        current = doc.to_dict().get("ticket_balance", 0)
        if current <= 0:
            return False
        txn.update(ref, {
            "ticket_balance": current - 1,
            "updated_at": datetime.now(timezone.utc),
        })
        return True

    txn = db.transaction()
    success = _use_in_transaction(txn, user_ref)
    if success:
        logger.info(f"Ticket used: uid={uid}, report={report_id}")
    else:
        logger.warning(f"Ticket use failed (insufficient balance): uid={uid}")
    return success


# ---------------------------------------------------------------------------
# 購入管理
# ---------------------------------------------------------------------------


def create_purchase(
    uid: str | None,
    tier: str,
    amount_jpy: int,
    ticket_count: int,
    stripe_session_id: str,
) -> str:
    """購入レコードを作成。

    Args:
        uid: Firebase Auth UID（匿名購入の場合はNone）
        tier: "single", "pack_10", "pack_50", "pack_100"
        amount_jpy: 支払額（円）
        ticket_count: チケット枚数
        stripe_session_id: Stripe Session ID

    Returns:
        purchase_id
    """
    db = get_db()
    purchase_id = f"pur_{uuid.uuid4().hex[:12]}"
    purchase_data = {
        "uid": uid,
        "tier": tier,
        "amount_jpy": amount_jpy,
        "ticket_count": ticket_count,
        "stripe_session_id": stripe_session_id,
        "status": "completed",
        "created_at": datetime.now(timezone.utc),
    }
    db.collection("purchases").document(purchase_id).set(purchase_data)
    logger.info(f"Purchase created: {purchase_id}, tier={tier}, uid={uid}")
    return purchase_id


# ---------------------------------------------------------------------------
# レポート管理
# ---------------------------------------------------------------------------


def create_report(
    uid: str | None,
    analysis_id: str,
    project_name: str,
) -> str:
    """レポートレコードを作成（3ヶ月TTL付き）。

    Args:
        uid: Firebase Auth UID（匿名の場合はNone）
        analysis_id: 分析ID
        project_name: プロジェクト名

    Returns:
        report_id
    """
    db = get_db()
    report_id = f"rpt_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    report_data = {
        "uid": uid,
        "analysis_id": analysis_id,
        "project_name": project_name,
        "status": "active",
        "created_at": now,
        "expires_at": now + timedelta(days=REPORT_TTL_DAYS),
    }
    db.collection("reports").document(report_id).set(report_data)
    logger.info(f"Report created: {report_id}, analysis={analysis_id}")
    return report_id


def get_user_reports(uid: str, limit: int = 50) -> list[dict[str, Any]]:
    """ユーザーのレポート一覧を取得（有効期限内のみ）。

    Args:
        uid: Firebase Auth UID
        limit: 最大取得件数

    Returns:
        レポートのリスト
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    docs = (
        db.collection("reports")
        .where("uid", "==", uid)
        .where("expires_at", ">", now)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    reports = []
    for doc in docs:
        data = doc.to_dict()
        data["report_id"] = doc.id
        reports.append(data)
    return reports


def delete_expired_reports() -> int:
    """期限切れレポートを削除。

    Returns:
        削除件数
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    expired = (
        db.collection("reports")
        .where("expires_at", "<=", now)
        .limit(500)
        .stream()
    )
    count = 0
    for doc in expired:
        doc.reference.delete()
        count += 1
    if count > 0:
        logger.info(f"Deleted {count} expired reports")
    return count
