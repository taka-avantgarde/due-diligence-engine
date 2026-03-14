"""FastAPI SaaS application for Due Diligence Engine."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from src.analyze.engine import AnalysisEngine
from src.config import Config, get_config
from src.ingest.secure_loader import SecureLoader
from src.purge.secure_delete import SecurePurger
from src.report.generator import ReportGenerator
from src.report.slides import SlideGenerator
from src.saas.auth import APIKeyRecord, AuthManager
from src.saas.billing import BillingManager

app = FastAPI(
    title="Due Diligence Engine",
    description="AI startup technical due diligence as a service",
    version="0.1.0",
)

# Singletons (initialized on startup)
_config: Config | None = None
_auth: AuthManager | None = None
_billing: BillingManager | None = None


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
