"""FastAPI SaaS application for Due Diligence Engine."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel

from src.analyze.engine import AnalysisEngine
from src.config import Config, get_config
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


@app.post("/api/v1/analyze/url")
async def analyze_url(
    request: AnalyzeUrlRequest,
    config: Config = Depends(get_app_config),
) -> dict:
    """Analyze a public GitHub repository by URL.

    Just paste a GitHub URL — no API key required for public repos.
    This is the endpoint the web search bar uses.
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
        clone_url = f"https://github.com/{owner_repo}.git"
        loader.load_from_url(clone_url)

        engine = AnalysisEngine(config, loader)
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
        logger.error(f"URL analysis failed for {owner_repo}: {e}")

        # Still run local-only analysis if clone fails
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
