import os
import json
import re
import requests
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

GROK_MODEL_CANDIDATES = [
    "grok-4",
    "grok-3-mini",
    "grok-2",
]

def _resolve_api_key(api_key: str | None = None) -> str | None:
    if api_key:
        return api_key
    return os.getenv("XAI_API_KEY") or st.session_state.get("XAI_API_KEY")

def _build_client(api_key: str | None = None):
    return _resolve_api_key(api_key)

def _create_chat_completion(client, messages: list[dict], temperature: float = 0):
    last_error = None
    for model_name in GROK_MODEL_CANDIDATES:
        try:
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {client}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "messages": messages,
                    "stream": False,
                    "temperature": temperature,
                },
                timeout=120,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            last_error = e
            continue
    raise last_error or Exception("All Grok models failed.")

def _extract_json_payload(raw_text: str) -> dict:
    """Extracts JSON from markdown code blocks or raw string."""
    try:
        # Strip markdown code blocks if present
        cleaned = re.sub(r'^```json\s*', '', raw_text, flags=re.MULTILINE)
        cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE)
        return json.loads(cleaned.strip())
    except Exception:
        # Fallback: find first { and last }
        try:
            start = raw_text.find('{')
            end = raw_text.rfind('}')
            if start != -1 and end != -1:
                return json.loads(raw_text[start:end+1])
        except Exception:
            pass
    return {}

def _coerce_score(val) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def _coerce_list(val) -> list[str]:
    if isinstance(val, list):
        return [str(i) for i in val]
    return []

def structure_jd_with_grok(job_description: str, api_key: str | None = None) -> list[dict]:
    """Analyze JD and extract key qualifications."""
    client = _build_client(api_key)
    if not client: return []
    
    prompt = (
        f"Analyze this job description and extract 5-8 concrete, actionable qualifications "
        f"to use as a scoring rubric. For each, provide a name and a one-sentence description "
        f"of what 'excellent' looks like.\n\nJD:\n{job_description[:2000]}\n\n"
        "Return ONLY a JSON list of objects with keys 'qualification' and 'description'."
    )
    
    try:
        response = _create_chat_completion(client, [{"role": "user", "content": prompt}])
        return _extract_json_payload(response["choices"][0]["message"]["content"])
    except:
        return []

def evaluate_candidate_with_rubric(
    candidate_text: str,
    candidate_name: str,
    job_description: str,
    api_key: str | None = None,
) -> dict:
    """
    Step 6/7: Evaluates a candidate against a job description using Grok.
    Returns the 10-field structured JSON requested by the user.
    """
    client = _build_client(api_key)
    if not client:
        return {}

    prompt = (
        f"You are a technical recruiting expert. Evaluate candidate '{candidate_name}' for this role.\n\n"
        f"JOB DESCRIPTION:\n{job_description[:2000]}\n\n"
        f"RESUME TEXT:\n{candidate_text[:6000]}\n\n"
        "Score the candidate (0-10) on match, company relevance, experience, bullets, projects, and resume quality. "
        "List matched requirements, missing ones, and flags. Provide a 2-sentence summary.\n"
        "Return strictly valid JSON with EXACTLY these keys:\n"
        "{\n"
        '  "qualification_match_score": number,\n'
        '  "company_relevance_score": number,\n'
        '  "experience_relevance_score": number,\n'
        '  "bullet_quality_score": number,\n'
        '  "project_strength_score": number,\n'
        '  "resume_quality_score": number,\n'
        '  "matched_requirements": [string],\n'
        '  "missing_requirements": [string],\n'
        '  "weakness_flags": [string],\n'
        '  "summary": string\n'
        "}"
    )

    try:
        response = _create_chat_completion(client, [
            {"role": "system", "content": "You are a precise technical recruiter providing structured JSON evaluations."},
            {"role": "user", "content": prompt}
        ])
        payload = _extract_json_payload(response["choices"][0]["message"]["content"])
        
        return {
            "qualification_match_score": _coerce_score(payload.get("qualification_match_score")),
            "company_relevance_score": _coerce_score(payload.get("company_relevance_score")),
            "experience_relevance_score": _coerce_score(payload.get("experience_relevance_score")),
            "bullet_quality_score": _coerce_score(payload.get("bullet_quality_score")),
            "project_strength_score": _coerce_score(payload.get("project_strength_score")),
            "resume_quality_score": _coerce_score(payload.get("resume_quality_score")),
            "matched_requirements": _coerce_list(payload.get("matched_requirements")),
            "missing_requirements": _coerce_list(payload.get("missing_requirements")),
            "weakness_flags": _coerce_list(payload.get("weakness_flags")),
            "summary": str(payload.get("summary", "")).strip()
        }
    except Exception as e:
        print(f"Grok evaluation error for {candidate_name}: {e}")
        return {}

def get_explanation_with_grok(job_description: str, candidate_text: str, candidate_name: str, api_key: str | None = None) -> str:
    """Concise 2-sentence match summary for the top 3."""
    client = _build_client(api_key)
    if not client: return "API key missing."
    
    prompt = (
        f"Explain specifically why {candidate_name}'s projects and past experience make them a top match for this role in 2 concise sentences. "
        f"Do not give generic answers; highlight specific skills, project outcomes, or past roles from their resume that align with the JD.\n\n"
        f"JD:\n{job_description[:1000]}\n\n"
        f"Resume Snippet:\n{candidate_text[:3000]}"
    )
    
    try:
        response = _create_chat_completion(client, [
            {"role": "system", "content": "You are a helpful recruiter writing concise summaries."},
            {"role": "user", "content": prompt}
        ], temperature=0.3)
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Error: {e}"

def _coerce_str(val) -> str:
    return str(val).strip() if val is not None else ""

def repair_resume_parse(raw_text: str, current_parsed: dict, api_key: str | None = None) -> dict:
    """
    Offline repair layer: Grok fixes messy parses by splitting entries and recovering metadata.
    Follows the specific schema requested by the USER.
    """
    client = _build_client(api_key)
    if not client: return current_parsed
    
    prompt = (
        "You are an expert resume parser. I have a messy parse of a resume. "
        "Directly use the raw text to recover a perfect structured parse.\n\n"
        "GOALS:\n"
        "1. Split collapsed experience into separate roles.\n"
        "2. Split collapsed projects into separate project entries.\n"
        "3. Recover missing company names.\n"
        "4. Extract technologies from experience and project bullets.\n"
        "5. Normalize messy skill tokens into canonical skills.\n\n"
        f"RAW TEXT:\n{raw_text[:8000]}\n\n"
        f"CURRENT MESSY PARSE (for reference):\n{json.dumps(current_parsed)[:2000]}\n\n"
        "Return ONLY valid JSON with EXACTLY this schema:\n"
        "{\n"
        '  "canonical_skills": [string],\n'
        '  "experience_entries": [\n'
        '    {\n'
        '      "title": string, "company": string, "company_normalized": string, \n'
        '      "dates": string, "location": string, "bullets": [string], "technologies": [string]\n'
        '    }\n'
        '  ],\n'
        '  "project_entries": [\n'
        '    {\n'
        '      "name": string, "dates": string, "location": string, \n'
        '      "bullets": [string], "technologies": [string]\n'
        '    }\n'
        '  ],\n'
        '  "parse_warnings": [string],\n'
        '  "summary_flags": [string]\n'
        "}"
    )
    
    try:
        response = _create_chat_completion(client, [
            {"role": "system", "content": "You are an elite data cleaning agent returning strict JSON following a specific schema."},
            {"role": "user", "content": prompt}
        ])
        raw_content = response["choices"][0]["message"]["content"]
        payload = _extract_json_payload(raw_content)
        return payload if payload else current_parsed
    except Exception:
        return current_parsed

def enrich_whole_resume(raw_text: str, current_parsed: dict, api_key: str | None = None) -> dict:
    """
    Optional Offline fallback: If a resume parse is critically sparse, 
    use Grok to extract ALL fundamental fields directly from the raw text.
    """
    client = _build_client(api_key)
    if not client: return current_parsed
    
    prompt = (
        "You are an expert resume parser. This resume was poorly parsed and is missing critical structured data. "
        "Read the raw text and extract an entirely new, fully structured profile.\n\n"
        f"RAW TEXT:\n{raw_text[:8000]}\n\n"
        "Return ONLY valid JSON with EXACTLY this schema. Pay special attention to structuring experience and projects as arrays of objects.\n"
        "{\n"
        '  "full_name": string,\n'
        '  "contact": string,\n'
        '  "summary": string,\n'
        '  "skills": [string],\n'
        '  "education": string,\n'
        '  "experience_entries": [\n'
        '    {"title": string, "company": string, "dates": string, "location": string, "bullets": [string], "technologies": [string]}\n'
        '  ],\n'
        '  "project_entries": [\n'
        '    {"name": string, "dates": string, "bullets": [string], "technologies": [string]}\n'
        '  ]\n'
        "}"
    )
    
    try:
        response = _create_chat_completion(client, [
            {"role": "system", "content": "You are a precise data extraction specialist returning strict JSON."},
            {"role": "user", "content": prompt}
        ])
        raw_content = response["choices"][0]["message"]["content"]
        payload = _extract_json_payload(raw_content)
        return payload if payload else current_parsed
    except Exception:
        return current_parsed
