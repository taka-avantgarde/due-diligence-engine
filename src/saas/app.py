"""FastAPI SaaS application for Due Diligence Engine."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request as FastAPIRequest, UploadFile
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel

import stripe

from src.analyze.engine import AnalysisEngine
from src.config import Config, get_config, TICKET_TIERS, REPORT_TTL_DAYS
from src.saas.firebase_auth import verify_firebase_token, require_firebase_auth, FirebaseUser
from src.saas import firestore_client
from src.ingest.secure_loader import SecureLoader
from src.purge.secure_delete import SecurePurger
from src.report.generator import ReportGenerator
from src.report.pdf_generator import PDFReportGenerator
from src.report.slides import SlideGenerator
from src.saas.auth import APIKeyRecord, AuthManager
from src.saas.billing import BillingManager
from src.saas.dashboard import router as dashboard_router, store_analysis, get_analysis
from src.saas.github_oauth import GitHubOAuthManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stripe 設定
# ---------------------------------------------------------------------------
_STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
_STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
_STRIPE_PRO_PRICE_CENTS = 2000  # $20/回（単位: セント）— レガシー用

# 決済済みセッションのキャッシュ（本番ではRedis等に置き換え推奨）
_paid_sessions: dict[str, bool] = {}

app = FastAPI(
    title="Due Diligence Engine",
    description="AI startup technical due diligence as a service",
    version="0.1.0",
)

# Include dashboard router
app.include_router(dashboard_router)

# Singletons (initialized on startup)
_config: Config | None = None
_auth: AuthManager | None = None
_billing: BillingManager | None = None
_github_oauth: GitHubOAuthManager | None = None


def get_app_config() -> Config:
    global _config
    if _config is None:
        _config = get_config()
        _config.ensure_dirs()
    return _config


def get_auth_manager() -> AuthManager:
    global _auth
    if _auth is None:
        _auth = AuthManager()
    return _auth


def get_billing_manager() -> BillingManager:
    global _billing
    if _billing is None:
        _billing = BillingManager(get_app_config())
    return _billing


def get_github_oauth() -> GitHubOAuthManager:
    """Get or create the GitHub OAuth manager singleton.

    Reads credentials from environment variables:
    - GITHUB_CLIENT_ID
    - GITHUB_CLIENT_SECRET
    - GITHUB_REDIRECT_URI (defaults to http://localhost:8000/api/github/callback)
    """
    global _github_oauth
    if _github_oauth is None:
        client_id = os.environ.get("GITHUB_CLIENT_ID", "")
        client_secret = os.environ.get("GITHUB_CLIENT_SECRET", "")
        redirect_uri = os.environ.get(
            "GITHUB_REDIRECT_URI",
            "http://localhost:8000/api/github/callback",
        )

        if not client_id or not client_secret:
            raise HTTPException(
                status_code=503,
                detail="GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.",
            )

        _github_oauth = GitHubOAuthManager(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
    return _github_oauth


async def verify_api_key(
    x_api_key: Annotated[str, Header()],
    auth: AuthManager = Depends(get_auth_manager),
) -> APIKeyRecord:
    """Dependency that validates the API key from the request header."""
    record = auth.validate_key(x_api_key)
    if record is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")
    return record


# --- Request/Response Models ---


class AnalyzeRequest(BaseModel):
    project_name: str
    skip_git: bool = False


class AnalyzeResponse(BaseModel):
    analysis_id: str
    project_name: str
    overall_score: float
    grade: str
    recommendation: str
    red_flag_count: int
    critical_flag_count: int
    total_cost_usd: float
    charge_usd: float
    report_url: str | None = None


class EstimateRequest(BaseModel):
    file_count: int
    total_lines: int


class EstimateResponse(BaseModel):
    estimated_api_cost_usd: float
    estimated_charge_usd: float
    tier: str
    multiplier: float


class KeyCreateRequest(BaseModel):
    user_id: str
    tier: str = "starter"


class KeyCreateResponse(BaseModel):
    api_key: str
    key_id: str
    tier: str
    message: str = "Save this API key securely. It will not be shown again."


class HealthResponse(BaseModel):
    status: str
    version: str


# --- Stripe Checkout エンドポイント ---


class StripeCheckoutRequest(BaseModel):
    """チケット購入用 Stripe Checkout Session 作成リクエスト。

    tier: "single" | "pack_10" | "pack_50" | "pack_100"
    firebase_id_token: バルク購入時に必須（認証済みユーザーにチケットを紐付ける）
    lang: リダイレクト先の言語
    """
    tier: str = "single"
    firebase_id_token: str | None = None
    lang: str = "en"


@app.post("/api/v1/stripe/checkout")
async def create_stripe_checkout(request: StripeCheckoutRequest) -> dict:
    """チケット購入の Stripe Checkout Session を作成（JPY）。

    - single: 認証不要（匿名購入OK）
    - pack_10 / pack_50 / pack_100: Firebase認証必須
    """
    if not _STRIPE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured.",
        )

    # --- ティア検証 ---
    tier_info = TICKET_TIERS.get(request.tier)
    if tier_info is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier: {request.tier}. Valid: {list(TICKET_TIERS.keys())}",
        )

    # --- バルク購入時はFirebase認証を要求 ---
    uid = "anonymous"
    if tier_info.get("account_required"):
        if not request.firebase_id_token:
            raise HTTPException(
                status_code=401,
                detail="Bulk ticket purchase requires authentication. Provide firebase_id_token.",
            )
        try:
            from src.saas.firestore_client import _ensure_initialized
            _ensure_initialized()
            from firebase_admin import auth as fb_auth
            decoded = fb_auth.verify_id_token(request.firebase_id_token)
            uid = decoded["uid"]
        except Exception as e:
            logger.warning(f"Firebase token verification failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid firebase_id_token.")

    stripe.api_key = _STRIPE_API_KEY

    try:
        base_url = os.environ.get("BASE_URL", "https://dde-api-vdunszkasq-an.a.run.app")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "jpy",
                    "product_data": {
                        "name": f"DDE Ticket — {tier_info['name']}",
                        "description": f"{tier_info['tickets']} report ticket(s)",
                    },
                    "unit_amount": tier_info["price_jpy"],
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=(
                f"{base_url}/dashboard/stripe/success"
                f"?session_id={{CHECKOUT_SESSION_ID}}&lang={request.lang}"
            ),
            cancel_url=f"{base_url}/dashboard/?stripe=cancelled&lang={request.lang}",
            metadata={
                "tier": request.tier,
                "uid": uid,
                "ticket_count": str(tier_info["tickets"]),
                "service": "dde_ticket",
            },
        )

        return {"checkout_url": session.url, "session_id": session.id}

    except stripe.error.StripeError as e:
        logger.error(f"Stripe checkout creation failed: {e}")
        raise HTTPException(status_code=502, detail=f"Stripe error: {str(e)}")


@app.post("/api/v1/stripe/webhook")
async def stripe_webhook(
    request: FastAPIRequest,
    stripe_signature: str | None = Header(None),
) -> dict:
    """Stripe Webhook — 決済完了を検知しチケットを付与。

    Stripe Webhook Signing で署名検証を行い、
    checkout.session.completed イベントを処理する。
    """
    # raw bodyを取得（署名検証に必要）
    payload = await request.body()

    if not _STRIPE_API_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    stripe.api_key = _STRIPE_API_KEY

    # --- 署名検証 ---
    if _STRIPE_WEBHOOK_SECRET and stripe_signature:
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, _STRIPE_WEBHOOK_SECRET,
            )
        except stripe.error.SignatureVerificationError:
            logger.warning("Stripe webhook signature verification failed")
            raise HTTPException(status_code=400, detail="Invalid signature")
        except Exception as e:
            logger.error(f"Stripe webhook error: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # Webhook Secret未設定の場合はペイロードをそのままパース（開発用）
        import json
        try:
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
        except Exception:
            logger.warning("Stripe webhook: failed to parse payload")
            return {"status": "ignored"}

    # --- checkout.session.completed イベントの処理 ---
    if event.type == "checkout.session.completed":
        session = event.data.object
        metadata = session.get("metadata", {})
        tier = metadata.get("tier", "single")
        uid = metadata.get("uid", "anonymous")
        ticket_count = int(metadata.get("ticket_count", "1"))

        logger.info(
            f"Stripe checkout completed: tier={tier}, uid={uid}, tickets={ticket_count}"
        )

        # チケット付与（認証済みユーザーの場合）
        if uid != "anonymous":
            try:
                firestore_client.get_or_create_user(
                    uid=uid,
                    email=session.get("customer_details", {}).get("email", ""),
                    display_name=session.get("customer_details", {}).get("name", ""),
                )
                firestore_client.add_tickets(
                    uid=uid,
                    count=ticket_count,
                    purchase_id=session.get("id", ""),
                )
            except Exception as e:
                logger.error(f"Failed to add tickets for uid={uid}: {e}")

        # 購入レコード作成
        try:
            tier_info = TICKET_TIERS.get(tier, {})
            firestore_client.create_purchase(
                uid=uid if uid != "anonymous" else None,
                tier=tier,
                amount_jpy=tier_info.get("price_jpy", 0),
                ticket_count=ticket_count,
                stripe_session_id=session.get("id", ""),
            )
        except Exception as e:
            logger.error(f"Failed to create purchase record: {e}")

        # レガシー互換: 決済済みセッションキャッシュ
        _paid_sessions[session.get("id", "")] = True

    return {"status": "ok", "type": event.type}


@app.get("/dashboard/stripe/success")
async def stripe_success_page(
    session_id: str = Query(..., description="Stripe Checkout Session ID"),
    lang: str = Query(default="en"),
) -> HTMLResponse:
    """Stripe決済成功後のリダイレクトページ。

    session_idを検証し、Pro分析の実行権限を付与する。
    """
    from fastapi.responses import HTMLResponse

    if not _STRIPE_API_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    stripe.api_key = _STRIPE_API_KEY

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError:
        raise HTTPException(status_code=400, detail="Invalid session")

    if session.payment_status != "paid":
        raise HTTPException(status_code=402, detail="Payment not completed")

    # 決済済みとしてキャッシュ
    _paid_sessions[session_id] = True
    repo_url = session.metadata.get("repo_url", "")

    is_ja = lang == "ja"

    return HTMLResponse(
        '<!DOCTYPE html><html lang="' + lang + '">'
        '<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>' + ("決済完了 — DDE Pro分析" if is_ja else "Payment Complete — DDE Pro Analysis") + '</title>'
        '<script src="https://cdn.tailwindcss.com"></script></head>'
        '<body class="bg-slate-950 text-white min-h-screen flex items-center justify-center">'
        '<div class="text-center max-w-lg p-8">'
        '<div class="text-5xl mb-4">✅</div>'
        '<h1 class="text-2xl font-bold mb-2">'
        + ("決済が完了しました" if is_ja else "Payment Successful") +
        '</h1>'
        '<p class="text-slate-400 mb-6">'
        + ("Claude + Gemini によるPro分析を開始します。" if is_ja else "Starting Pro Analysis with Claude + Gemini.") +
        '</p>'
        '<p class="text-xs text-slate-500 mb-8">Session: ' + session_id[:16] + '...</p>'
        '<a href="/dashboard/?pro_session=' + session_id + '&lang=' + lang + '" '
        'class="inline-block bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 px-8 rounded-xl transition">'
        + ("ダッシュボードに戻ってPro分析を実行" if is_ja else "Return to Dashboard & Run Pro Analysis") +
        '</a>'
        '</div></body></html>'
    )


def _verify_stripe_payment(session_id: str) -> bool:
    """Stripe決済セッションの有効性を検証。

    キャッシュにあればTrue、なければStripe APIで確認。
    """
    if not session_id:
        return False

    # キャッシュチェック
    if _paid_sessions.get(session_id):
        return True

    # Stripe APIで確認
    if not _STRIPE_API_KEY:
        return False

    stripe.api_key = _STRIPE_API_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid" and session.metadata.get("service") == "dde_pro_analysis":
            _paid_sessions[session_id] = True
            return True
    except stripe.error.StripeError:
        pass

    return False


# ---------------------------------------------------------------------------
# チケット制 API エンドポイント
# ---------------------------------------------------------------------------


@app.get("/api/v1/account")
async def get_account(
    user: FirebaseUser = Depends(require_firebase_auth),
) -> dict:
    """認証ユーザーのアカウント情報を返す。

    - ユーザー基本情報
    - チケット残高
    """
    user_data = firestore_client.get_or_create_user(
        uid=user.uid,
        email=user.email,
        display_name=user.display_name,
    )
    return {
        "uid": user.uid,
        "email": user.email,
        "display_name": user.display_name,
        "photo_url": user.photo_url,
        "ticket_balance": user_data.get("ticket_balance", 0),
        "created_at": str(user_data.get("created_at", "")),
    }


@app.get("/api/v1/reports")
async def get_reports(
    user: FirebaseUser = Depends(require_firebase_auth),
) -> dict:
    """認証ユーザーのレポート一覧を返す（有効期限内のもののみ）。"""
    reports = firestore_client.get_user_reports(uid=user.uid)
    return {
        "uid": user.uid,
        "reports": reports,
        "count": len(reports),
    }


class TicketUseRequest(BaseModel):
    """チケット消費リクエスト。

    repo_url: 分析対象のGitHubリポジトリURL
    """
    repo_url: str


@app.post("/api/v1/tickets/use")
async def use_ticket_and_analyze(
    request: TicketUseRequest,
    user: FirebaseUser = Depends(require_firebase_auth),
    config: Config = Depends(get_app_config),
) -> dict:
    """チケットを1枚消費してレポートを生成する。

    トランザクションでチケット残高を減算し、分析を実行する。
    残高不足の場合は 402 を返す。
    """
    import re
    import uuid

    repo_url = request.repo_url.strip()

    # --- リポジトリURLパース ---
    match = re.match(
        r"(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/\s#?.]+)",
        repo_url,
    )
    if match:
        owner_repo = f"{match.group(1)}/{match.group(2).rstrip('.git')}"
    elif re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", repo_url):
        owner_repo = repo_url
    else:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")

    analysis_id = uuid.uuid4().hex[:16]
    report_id = f"rpt_{uuid.uuid4().hex[:12]}"

    # --- チケット消費（トランザクション） ---
    success = firestore_client.use_ticket(uid=user.uid, report_id=report_id)
    if not success:
        raise HTTPException(
            status_code=402,
            detail="Insufficient ticket balance. Please purchase tickets first.",
        )

    # --- 分析実行 ---
    clone_url = f"https://github.com/{owner_repo}.git"
    loader = SecureLoader(config)

    try:
        store_analysis(analysis_id, {
            "status": "running",
            "connection_id": "",
            "result": None,
            "purge_cert": None,
        })

        loader.load_from_url(clone_url)

        # サーバー側AIキーで分析
        pro_keys = config.get_ai_api_keys()
        pro_keys = {k: v for k, v in pro_keys.items() if k in ("claude", "gemini")}

        engine = AnalysisEngine(config, loader, api_keys=pro_keys if pro_keys else None)
        repo_path = loader.cloned_repo_path
        result = engine.run(project_name=owner_repo, repo_path=repo_path)
        result.analysis_id = analysis_id

        # レポート生成・保存
        report_gen = ReportGenerator()
        report_gen.save_report(result, config.output_dir)

        store_analysis(analysis_id, {
            "status": "completed",
            "connection_id": "",
            "result": result,
            "purge_cert": None,
        })

        # Firestoreにレポートレコード作成
        firestore_client.create_report(
            uid=user.uid,
            analysis_id=analysis_id,
            project_name=owner_repo,
        )

        return {
            "analysis_id": analysis_id,
            "report_id": report_id,
            "status": "completed",
            "ticket_balance": firestore_client.get_ticket_balance(user.uid),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ticket analysis failed for {owner_repo}: {e}")
        store_analysis(analysis_id, {
            "status": "error",
            "connection_id": "",
            "result": None,
            "purge_cert": None,
            "error": str(e),
        })
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        loader.destroy()


@app.get("/api/v1/pricing/tickets")
async def get_ticket_pricing() -> dict:
    """チケット料金体系を返す（公開エンドポイント）。"""
    return {
        "currency": "JPY",
        "tiers": {
            key: {
                "name": tier["name"],
                "name_ja": tier["name_ja"],
                "price_jpy": tier["price_jpy"],
                "tickets": tier["tickets"],
                "unit_price": tier["unit_price"],
                "account_required": tier["account_required"],
            }
            for key, tier in TICKET_TIERS.items()
        },
        "report_ttl_days": REPORT_TTL_DAYS,
    }


# --- Endpoints ---


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", version="0.1.0")


@app.post("/api/v1/keys", response_model=KeyCreateResponse)
async def create_api_key(
    request: KeyCreateRequest,
    auth: AuthManager = Depends(get_auth_manager),
) -> KeyCreateResponse:
    """Create a new API key. In production, this would require admin auth."""
    raw_key, record = auth.create_api_key(
        user_id=request.user_id,
        tier=request.tier,
    )
    return KeyCreateResponse(
        api_key=raw_key,
        key_id=record.key_id,
        tier=record.tier,
    )


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_upload(
    project_name: str,
    file: UploadFile = File(...),
    skip_git: bool = False,
    key_record: APIKeyRecord = Depends(verify_api_key),
    config: Config = Depends(get_app_config),
    billing: BillingManager = Depends(get_billing_manager),
) -> AnalyzeResponse:
    """Upload a zip file and run due diligence analysis.

    Requires API key in the X-API-Key header.
    """
    # Validate file
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are accepted")

    # Save uploaded file to temp location
    tmp_dir = Path(tempfile.mkdtemp(prefix="dde_upload_"))
    try:
        zip_path = tmp_dir / file.filename
        with open(zip_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Run analysis
        loader = SecureLoader(config)
        loader.load_archive(zip_path)

        engine = AnalysisEngine(config, loader)
        result = engine.run(
            project_name=project_name,
            skip_git=skip_git,
        )

        # Compute charge
        charge = billing.compute_charge(
            result.model_usage, tier=key_record.tier
        )

        # Generate report
        report_gen = ReportGenerator()
        saved = report_gen.save_report(result, config.output_dir)

        # Cleanup
        loader.destroy()

        score = result.score
        return AnalyzeResponse(
            analysis_id=result.analysis_id,
            project_name=result.project_name,
            overall_score=score.overall_score if score else 0,
            grade=score.grade if score else "N/A",
            recommendation=score.recommendation if score else "",
            red_flag_count=len(score.red_flags) if score else 0,
            critical_flag_count=(
                sum(1 for f in score.red_flags if f.is_deal_breaker) if score else 0
            ),
            total_cost_usd=result.total_cost_usd,
            charge_usd=charge["total_charge_usd"],
            report_url=str(saved[0]) if saved else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        shutil.rmtree(str(tmp_dir), ignore_errors=True)


@app.post("/api/v1/estimate", response_model=EstimateResponse)
async def estimate_cost(
    request: EstimateRequest,
    key_record: APIKeyRecord = Depends(verify_api_key),
    billing: BillingManager = Depends(get_billing_manager),
) -> EstimateResponse:
    """Estimate the cost of an analysis before running it."""
    estimate = billing.estimate_analysis_cost(
        file_count=request.file_count,
        total_lines=request.total_lines,
        tier=key_record.tier,
    )
    return EstimateResponse(**estimate)


@app.post("/api/v1/purge/{analysis_id}")
async def purge_analysis(
    analysis_id: str,
    key_record: APIKeyRecord = Depends(verify_api_key),
    config: Config = Depends(get_app_config),
) -> dict:
    """Securely purge all data from a completed analysis."""
    purger = SecurePurger()

    # Look for analysis data in the temp directory
    analysis_dir = config.temp_dir / analysis_id
    if not analysis_dir.exists():
        raise HTTPException(status_code=404, detail="Analysis data not found")

    cert = purger.purge_directory(
        directory=analysis_dir,
        analysis_id=analysis_id,
        project_name="unknown",
        operator=key_record.user_id,
    )

    cert_path = config.output_dir / f"purge_cert_{analysis_id}.json"
    purger.export_certificate(cert, cert_path)

    return {
        "status": "purged",
        "certificate_id": cert.certificate_id,
        "files_purged": cert.files_purged,
        "bytes_overwritten": cert.bytes_overwritten,
        "certificate_path": str(cert_path),
    }


@app.get("/api/v1/pricing")
async def get_pricing() -> dict:
    """Get current pricing tiers and their features."""
    from src.config import PRICING_TIERS

    return {
        tier_key: {
            "name": tier.name,
            "cost_multiplier": tier.cost_multiplier,
            "max_repos_per_month": tier.max_repos_per_month,
            "max_file_size_mb": tier.max_file_size_mb,
            "features": tier.features,
        }
        for tier_key, tier in PRICING_TIERS.items()
    }


# ---------------------------------------------------------------------------
# GitHub OAuth Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/github/connect")
@app.get("/api/github/connect")
async def github_connect(
    user_id: str = Query(default="demo_user", description="User ID to associate with the connection"),
) -> RedirectResponse:
    """Initiate the GitHub OAuth flow.

    Redirects the user to GitHub's authorization page.
    """
    oauth = get_github_oauth()
    auth_url, state = oauth.get_authorization_url(user_id=user_id)
    return RedirectResponse(url=auth_url, status_code=302)


@app.get("/api/github/callback")
async def github_callback(
    code: str = Query(..., description="Authorization code from GitHub"),
    state: str = Query(..., description="CSRF state token"),
) -> RedirectResponse:
    """Handle the GitHub OAuth callback.

    Exchanges the authorization code for an access token and
    redirects to the repository selection page.
    """
    oauth = get_github_oauth()

    try:
        connection = await oauth.handle_callback(code=code, state=state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Redirect to repository selection page
    return RedirectResponse(
        url=f"/dashboard/repos?connection_id={connection.connection_id}",
        status_code=302,
    )


@app.get("/api/github/repos/{connection_id}")
async def github_list_repos(connection_id: str) -> list[dict[str, Any]]:
    """List repositories accessible to the connected GitHub account.

    Returns both public and private repos the user granted access to.
    """
    oauth = get_github_oauth()

    conn = oauth.get_connection(connection_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="GitHub connection not found")

    try:
        repos = await oauth.list_repos(connection_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return repos


@app.post("/api/github/disconnect/{connection_id}")
async def github_disconnect(
    connection_id: str,
    analysis_id: str = Query(default="", description="Associated analysis ID for purging"),
    config: Config = Depends(get_app_config),
) -> RedirectResponse:
    """Disconnect GitHub and purge all associated data.

    This endpoint:
    1. Revokes the GitHub OAuth token (if connection exists)
    2. Purges all cloned source code data
    3. Generates a purge certificate
    4. Redirects to the purge confirmation page
    """
    project_name = "unknown"
    user_id = "system"

    # Step 1: Revoke GitHub token (only if connection_id is valid and OAuth is configured)
    if connection_id and connection_id != "none":
        try:
            oauth = get_github_oauth()
            conn = oauth.get_connection(connection_id)
            if conn:
                project_name = conn.repo_full_name or "unknown"
                user_id = conn.user_id or "system"
                await oauth.revoke_access(connection_id)
        except HTTPException:
            # OAuth not configured or connection not found — continue with purge
            pass

    # Step 2: Purge cloned data and generate certificate
    purge_cert = None
    if analysis_id:
        # Get project name from analysis store if not from connection
        data = get_analysis(analysis_id)
        if data is not None and project_name == "unknown":
            result = data.get("result")
            if result is not None:
                project_name = result.project_name

        purger = SecurePurger()

        # Purge the analysis temp directory if it exists
        analysis_dir = config.temp_dir / analysis_id
        if analysis_dir.exists():
            purge_cert = purger.purge_directory(
                directory=analysis_dir,
                analysis_id=analysis_id,
                project_name=project_name,
                operator=user_id,
            )

            # Export certificate
            cert_path = config.output_dir / f"purge_cert_{analysis_id}.json"
            purger.export_certificate(purge_cert, cert_path)
        else:
            # Create a certificate even if no directory exists (data was in-memory)
            from src.models import PurgeCertificate

            purge_cert = PurgeCertificate(
                analysis_id=analysis_id,
                project_name=project_name,
                files_purged=0,
                bytes_overwritten=0,
                method="in_memory_erasure",
                operator=user_id,
                verification_hash="in_memory_data_cleared",
            )

        # Update analysis store
        if data is not None:
            data["status"] = "purged"
            data["purge_cert"] = purge_cert
            store_analysis(analysis_id, data)

        return RedirectResponse(
            url=f"/dashboard/purge-complete/{analysis_id}",
            status_code=302,
        )

    # No analysis_id: just redirect back to home
    return RedirectResponse(url="/dashboard/", status_code=302)


@app.post("/api/purge/{analysis_id}")
async def purge_analysis_data(
    analysis_id: str,
    config: Config = Depends(get_app_config),
) -> RedirectResponse:
    """Purge analysis data without GitHub disconnection.

    Used for URL-based analyses that don't have a GitHub OAuth connection.
    """
    data = get_analysis(analysis_id)
    project_name = "unknown"
    if data is not None:
        result = data.get("result")
        if result is not None:
            project_name = result.project_name

    purger = SecurePurger()

    # Purge the analysis temp directory if it exists
    analysis_dir = config.temp_dir / analysis_id
    if analysis_dir.exists():
        purge_cert = purger.purge_directory(
            directory=analysis_dir,
            analysis_id=analysis_id,
            project_name=project_name,
            operator="system",
        )
        cert_path = config.output_dir / f"purge_cert_{analysis_id}.json"
        purger.export_certificate(purge_cert, cert_path)
    else:
        from src.models import PurgeCertificate

        purge_cert = PurgeCertificate(
            analysis_id=analysis_id,
            project_name=project_name,
            files_purged=0,
            bytes_overwritten=0,
            method="in_memory_erasure",
            operator="system",
            verification_hash="in_memory_data_cleared",
        )

    # Update analysis store
    if data is not None:
        data["status"] = "purged"
        data["purge_cert"] = purge_cert
        store_analysis(analysis_id, data)

    return RedirectResponse(
        url=f"/dashboard/purge-complete/{analysis_id}",
        status_code=302,
    )


@app.post("/api/analyze/github/{connection_id}/{repo:path}")
async def analyze_github_repo(
    connection_id: str,
    repo: str,
    config: Config = Depends(get_app_config),
) -> RedirectResponse:
    """Analyze a GitHub repository connected via OAuth.

    Clones the repository using the OAuth token, runs analysis,
    and redirects to the results page.
    """
    oauth = get_github_oauth()

    conn = oauth.get_connection(connection_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="GitHub connection not found")

    # Associate repo with the connection
    oauth.set_repo(connection_id, repo)

    # Get authenticated clone URL
    clone_url = oauth.get_clone_url(connection_id, repo)

    # Use SecureLoader to clone and analyze
    loader = SecureLoader(config)

    try:
        # Store as "running" in the analysis store
        import uuid

        analysis_id = uuid.uuid4().hex[:16]
        store_analysis(analysis_id, {
            "status": "running",
            "connection_id": connection_id,
            "result": None,
            "purge_cert": None,
        })

        # Clone the repo using authenticated URL
        loader.load_from_url(clone_url)

        # Run analysis
        engine = AnalysisEngine(config, loader)
        repo_path = loader.cloned_repo_path
        result = engine.run(
            project_name=repo,
            repo_path=repo_path,
        )

        # Force the analysis_id to match
        result.analysis_id = analysis_id

        # Generate reports
        report_gen = ReportGenerator()
        report_gen.save_report(result, config.output_dir)

        # Store completed result
        store_analysis(analysis_id, {
            "status": "completed",
            "connection_id": connection_id,
            "result": result,
            "purge_cert": None,
        })

        # Cleanup cloned data (but keep encrypted workspace for potential purge)
        # The loader workspace will be purged on disconnect

        return RedirectResponse(
            url=f"/dashboard/analysis/{analysis_id}",
            status_code=302,
        )

    except Exception as e:
        logger.error(f"GitHub analysis failed for {repo}: {e}")
        loader.destroy()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


class AnalyzeUrlRequest(BaseModel):
    repo_url: str
    pat_token: str | None = None
    api_keys: dict[str, str] | None = None  # {"claude": "sk-...", "gemini": "...", "chatgpt": "sk-..."}
    pro_analysis: bool = False  # True: 有料プラン（サーバー側Claude+Geminiで分析）
    stripe_session_id: str | None = None  # Stripe Checkout Session ID（Pro分析時に必須）


def _validate_pat(token: str) -> None:
    """Validate GitHub PAT format. Raises HTTPException on invalid."""
    import re as _re

    if not _re.match(r"^(github_pat_[A-Za-z0-9_]{22,}|ghp_[A-Za-z0-9]{36,})$", token):
        raise HTTPException(
            status_code=400,
            detail="Invalid PAT format. Must start with 'github_pat_' or 'ghp_'.",
        )


def _sanitize_token(message: str, token: str) -> str:
    """Strip PAT from error messages before logging."""
    return message.replace(token, "[REDACTED]")


def _validate_api_keys(keys: dict[str, str] | None) -> dict[str, str] | None:
    """BYOKのAPIキーをバリデーション・サニタイズ。

    許可されたプロバイダー名のみ受け付け、空文字列のキーは除外。
    """
    if not keys:
        return None

    allowed_providers = {"claude", "gemini", "chatgpt"}
    validated: dict[str, str] = {}

    for provider, key in keys.items():
        provider = provider.strip().lower()
        key = key.strip()
        if provider not in allowed_providers:
            continue
        if not key:
            continue
        validated[provider] = key

    return validated if validated else None


@app.post("/api/v1/analyze/url")
async def analyze_url(
    request: AnalyzeUrlRequest,
    config: Config = Depends(get_app_config),
) -> dict:
    """Analyze a GitHub repository by URL.

    For public repos, just paste the URL.
    For private repos, include a Fine-grained PAT with Contents: Read-only.
    """
    import re
    import uuid

    repo_url = request.repo_url.strip()

    # Parse owner/repo from URL or direct format
    match = re.match(
        r"(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/\s#?.]+)",
        repo_url,
    )
    if match:
        owner_repo = f"{match.group(1)}/{match.group(2).rstrip('.git')}"
    elif re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", repo_url):
        owner_repo = repo_url
    else:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")

    # Validate and build clone URL
    pat = request.pat_token.strip() if request.pat_token else None
    if pat:
        _validate_pat(pat)
        clone_url = f"https://x-access-token:{pat}@github.com/{owner_repo}.git"
        logger.info(f"Analyzing private repo with PAT: {owner_repo}")
    else:
        clone_url = f"https://github.com/{owner_repo}.git"
        logger.info(f"Analyzing public repo: {owner_repo}")

    analysis_id = uuid.uuid4().hex[:16]

    # Store as running
    store_analysis(analysis_id, {
        "status": "running",
        "connection_id": "",
        "result": None,
        "purge_cert": None,
    })

    # Clone and analyze
    loader = SecureLoader(config)
    try:
        loader.load_from_url(clone_url)

        # APIキーの決定: Pro分析 > BYOK > 環境変数
        if request.pro_analysis:
            # 有料プラン: Stripe決済を検証後、サーバー側のClaude + Geminiキーを使用
            if not request.stripe_session_id:
                raise HTTPException(
                    status_code=402,
                    detail="Pro Analysis requires Stripe payment. Please complete checkout first.",
                )
            if not _verify_stripe_payment(request.stripe_session_id):
                raise HTTPException(
                    status_code=402,
                    detail="Payment not verified. Please complete Stripe checkout.",
                )
            logger.info(f"Pro Analysis: Stripe payment verified (session: {request.stripe_session_id[:16]}...)")
            pro_keys = config.get_ai_api_keys()
            # Pro分析はClaude + Geminiの2社に限定
            pro_keys = {k: v for k, v in pro_keys.items() if k in ("claude", "gemini")}
            if not pro_keys:
                raise HTTPException(
                    status_code=503,
                    detail="Pro Analysis is not available. Server AI keys are not configured.",
                )
            byok_keys = pro_keys
            logger.info(f"Pro Analysis mode: using server-side keys ({list(pro_keys.keys())})")
        else:
            byok_keys = _validate_api_keys(request.api_keys) if request.api_keys else None

        engine = AnalysisEngine(config, loader, api_keys=byok_keys)
        repo_path = loader.cloned_repo_path
        result = engine.run(
            project_name=owner_repo,
            repo_path=repo_path,
        )
        result.analysis_id = analysis_id

        # Generate reports
        report_gen = ReportGenerator()
        report_gen.save_report(result, config.output_dir)

        # Store completed
        store_analysis(analysis_id, {
            "status": "completed",
            "connection_id": "",
            "result": result,
            "purge_cert": None,
        })

        return {"analysis_id": analysis_id, "status": "completed"}

    except Exception as e:
        error_msg = str(e)
        if pat:
            error_msg = _sanitize_token(error_msg, pat)
        logger.error(f"URL analysis failed for {owner_repo}: {error_msg}")

        # Still run local-only analysis if clone fails
        store_analysis(analysis_id, {
            "status": "error",
            "connection_id": "",
            "result": None,
            "purge_cert": None,
            "error": error_msg,
        })
        raise HTTPException(status_code=500, detail=f"Analysis failed: {error_msg}")
    finally:
        loader.destroy()


@app.get("/api/report/{analysis_id}/pdf")
async def download_pdf_report(
    analysis_id: str,
    lang: str = Query(default="en", description="Language: en or ja"),
) -> Response:
    """Generate and download a PDF report for a completed analysis.

    The PDF contains scores, findings, and recommendations.
    Source code is NEVER included in the PDF output.
    """
    if lang not in ("en", "ja"):
        lang = "en"

    data = get_analysis(analysis_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    result = data.get("result")
    if result is None:
        raise HTTPException(status_code=404, detail="No analysis result available")

    purge_cert = data.get("purge_cert")

    pdf_gen = PDFReportGenerator()
    pdf_bytes = pdf_gen.generate(result, purge_cert=purge_cert, lang=lang)

    filename = f"dde_report_{result.project_name}_{analysis_id}.pdf"
    # Sanitize filename
    filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
