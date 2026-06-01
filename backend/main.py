# Environment variables read by this service:
#   FRONTEND_ORIGINS — Comma-separated CORS allowed origins (default: http://localhost:3000)
#   XAI_API_KEY — Passed through to src/ui retrieval for Grok scoring (optional; also loaded by src on import)
#   TALENTLENS_GROK_MAX_WORKERS — Max parallel Grok calls in SearchEngine (optional; default 6 in src/ui/search.py)
#   TALENTLENS_DISABLE_RERANKER — If 1/true, skip cross-encoder load (saves ~500MB+ RAM on Railway 1GB)
#   TALENTLENS_RERANKER_ENABLED — Explicit 0/false to disable reranker (set automatically when DISABLE_RERANKER=1)
#   TALENTLENS_STRICT_STARTUP — If 1/true, fail boot when semantic/reranker missing (default off when DISABLE_RERANKER=1)
#
# Run from the project root so data/ artifacts resolve correctly, e.g.:
#   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UI_DIR = PROJECT_ROOT / "src" / "ui"
if str(UI_DIR) not in sys.path:
    sys.path.insert(0, str(UI_DIR))


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes")


def _configure_low_memory_profile() -> bool:
    """Apply env before SearchEngine import so config.py sees reranker flags."""
    if _env_flag("TALENTLENS_DISABLE_RERANKER"):
        os.environ["TALENTLENS_RERANKER_ENABLED"] = "0"
        return True
    return os.getenv("TALENTLENS_RERANKER_ENABLED", "1").strip().lower() in ("0", "false", "no")


def _strict_startup_enabled(reranker_disabled: bool) -> bool:
    raw = os.getenv("TALENTLENS_STRICT_STARTUP")
    if raw is None:
        return not reranker_disabled
    return raw.strip().lower() in ("1", "true", "yes")


_reranker_disabled = _configure_low_memory_profile()

from search import ResumeResult, SearchEngine  # noqa: E402

DEFAULT_FRONTEND_ORIGINS = "http://localhost:3000"


def _parse_frontend_origins() -> list[str]:
    raw = os.getenv("FRONTEND_ORIGINS", DEFAULT_FRONTEND_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="TalentLens API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = SearchEngine(strict_startup=_strict_startup_enabled(_reranker_disabled))


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=10, ge=1, le=100)
    filters: dict[str, Any] = Field(default_factory=dict)


def _resume_result_to_dict(result: ResumeResult) -> dict[str, Any]:
    return {
        "rank": result.rank,
        "resume_id": result.candidate_id or result.filename,
        "filename": result.filename,
        "candidate_id": result.candidate_id,
        "score": float(result.score),
        "semantic_score": float(result.semantic_score),
        "file_path": result.file_path,
        "local_resume_path": result.local_resume_path,
        "full_name": result.full_name,
        "major": result.major,
        "graduation_year": result.graduation_year,
        "resume_link": result.resume_link,
        "linkedin": result.linkedin,
        "github": result.github,
        "matched_skills": result.matched_skills,
        "text_preview": result.text_preview,
        "top_evidence_chunks": result.top_evidence_chunks,
        "hard_filter_status": result.hard_filter_status,
        "ranking_details": result.ranking_details,
        "page_count": result.page_count,
        "company_match_status": result.company_match_status,
        "grok_status": result.grok_status,
        "grok_fit_score": float(result.grok_fit_score),
        "grok_resume_quality_score": float(result.grok_resume_quality_score),
        "grok_summary": result.grok_summary,
        "grok_matched_requirements": result.grok_matched_requirements,
        "grok_missing_requirements": result.grok_missing_requirements,
        "grok_weakness_flags": result.grok_weakness_flags,
    }


def _coerce_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _search_kwargs_from_filters(filters: dict[str, Any]) -> dict[str, Any]:
    skill_filters = filters.get("skill_filters") or filters.get("skills")
    if skill_filters is not None and not isinstance(skill_filters, list):
        skill_filters = [str(skill_filters)]

    grad_year_min = _coerce_optional_int(filters.get("grad_year_min"))
    grad_year_max = _coerce_optional_int(filters.get("grad_year_max"))
    grad_year_range = filters.get("grad_year")
    if isinstance(grad_year_range, dict):
        grad_year_min = _coerce_optional_int(grad_year_range.get("min")) or grad_year_min
        grad_year_max = _coerce_optional_int(grad_year_range.get("max")) or grad_year_max

    grad_year_filter = filters.get("grad_year_filter")
    if grad_year_filter is None and grad_year_min is not None and grad_year_max is not None:
        if grad_year_min == grad_year_max:
            grad_year_filter = str(grad_year_min)

    role_type = filters.get("role_type") or filters.get("role_type_filter")
    if isinstance(role_type, str) and role_type.strip().lower() in {"", "all"}:
        role_type = None

    return {
        "grad_year_filter": grad_year_filter,
        "grad_year_min": grad_year_min,
        "grad_year_max": grad_year_max,
        "role_type_filter": role_type,
        "major_filter": filters.get("major_filter") or filters.get("major"),
        "skill_filters": skill_filters,
        "input_mode": filters.get("input_mode", "Job Description"),
        "min_score": float(filters.get("min_score", 0.0)),
        "recruiter_company": filters.get("recruiter_company"),
        "recruiter_job_title": filters.get("recruiter_job_title"),
    }


def _resume_exists(resume_id: str) -> bool:
    if resume_id in engine.resume_metadata_by_filename:
        return True
    if resume_id in engine.parsed_resume_map:
        return True
    if engine.demo_mode:
        return resume_id in engine.resume_metadata_by_filename
    return False


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/search")
async def search_resumes(body: SearchRequest) -> list[dict[str, Any]]:
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    search_kwargs = _search_kwargs_from_filters(body.filters)
    results = engine.search(
        query=body.query.strip(),
        top_k=body.top_k,
        api_key=os.getenv("XAI_API_KEY"),
        **search_kwargs,
    )
    return [_resume_result_to_dict(result) for result in results]


@app.get("/api/resume/{resume_id}")
async def get_resume(resume_id: str) -> dict[str, Any]:
    if not _resume_exists(resume_id):
        raise HTTPException(status_code=404, detail=f"Resume not found: {resume_id}")

    profile = engine._get_candidate_profile(resume_id)
    member_info = engine._lookup_member(resume_id, profile.get("combined_text", ""))
    local_resume_path = engine._resolve_resume_path(resume_id, profile.get("file_path", ""))

    return {
        "resume_id": resume_id,
        "candidate_id": resume_id,
        "filename": resume_id,
        "source": profile.get("source", ""),
        "file_path": profile.get("file_path", ""),
        "local_resume_path": local_resume_path,
        "full_name": member_info.get("full_name") or profile.get("full_name", resume_id),
        "major": member_info.get("major") or profile.get("major", ""),
        "graduation_year": str(
            member_info.get("graduation_year") or profile.get("graduation_year", "")
        ),
        "resume_link": member_info.get("resume_link") or profile.get("resume_link", ""),
        "linkedin": member_info.get("linkedin") or profile.get("linkedin", ""),
        "github": member_info.get("github") or profile.get("github", ""),
        "skills": profile.get("skills", []),
        "canonical_skills": profile.get("canonical_skills", []),
        "summary": profile.get("summary", ""),
        "education": profile.get("education", []),
        "experience": profile.get("experience_entries", []),
        "projects": profile.get("project_entries", []),
        "employer_names": profile.get("employer_names", []),
        "estimated_years_experience": profile.get("estimated_years_experience"),
        "combined_text": profile.get("combined_text", ""),
    }
