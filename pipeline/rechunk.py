import json
import uuid
import os
from pathlib import Path
from typing import Dict, List, Optional
from tqdm import tqdm

MIN_CHUNK_CHARS = 30

def make_chunk(candidate_id: str, source: str, section_type: str,
               text: str, extra_meta: Optional[Dict] = None) -> Dict:
    """Build a single chunk dict."""
    meta = {"candidate_id": candidate_id, "source": source}
    if extra_meta:
        meta.update(extra_meta)
    return {
        "chunk_id":     str(uuid.uuid4()),
        "candidate_id": candidate_id,
        "source":       source,
        "section_type": section_type,
        "text":         text.strip(),
        "metadata":     meta,
    }

def chunk_resume(parsed: Dict) -> List[Dict]:
    """Convert a parsed resume into a list of chunks."""
    cid    = parsed["candidate_id"]
    source = parsed["source"]
    chunks: List[Dict] = []

    # --- Contact ---
    contact = parsed.get("contact", {})
    contact_text = " | ".join(v for v in contact.values() if v)
    if len(contact_text) >= MIN_CHUNK_CHARS:
        chunks.append(make_chunk(cid, source, "contact", contact_text))

    # --- Summary ---
    summary = parsed.get("summary", "")
    if len(summary) >= MIN_CHUNK_CHARS:
        chunks.append(make_chunk(cid, source, "summary", summary))

    # --- Experience ---
    for entry in parsed.get("experience", []):
        parts = [entry.get("raw_header", "")]
        if entry.get("dates"):
            parts.append(" | ".join(entry["dates"]))
        parts.extend(entry.get("bullets", []))
        text = "\n".join(p for p in parts if p)
        if len(text) >= MIN_CHUNK_CHARS:
            chunks.append(make_chunk(cid, source, "experience", text, {
                "dates": entry.get("dates", []),
            }))

    # --- Education ---
    for entry in parsed.get("education", []):
        text = entry.get("raw_text", "")
        if len(text) >= MIN_CHUNK_CHARS:
            chunks.append(make_chunk(cid, source, "education", text, {
                "dates": entry.get("dates", []),
            }))

    # --- Skills ---
    skills = parsed.get("skills", [])
    if skills:
        skills_text = ", ".join(skills)
        if len(skills_text) >= MIN_CHUNK_CHARS:
            chunks.append(make_chunk(cid, source, "skills", skills_text, {
                "skills_list": skills,
            }))

    # --- Projects ---
    for entry in parsed.get("projects", []):
        parts = [entry.get("raw_header", "")]
        parts.extend(entry.get("bullets", []))
        text = "\n".join(p for p in parts if p)
        if len(text) >= MIN_CHUNK_CHARS:
            chunks.append(make_chunk(cid, source, "projects", text))

    # --- Certifications ---
    certs = parsed.get("certifications", [])
    if certs:
        cert_text = "\n".join(certs)
        if len(cert_text) >= MIN_CHUNK_CHARS:
            chunks.append(make_chunk(cid, source, "certifications", cert_text))

    # --- Raw sections ---
    handled = {"contact", "summary", "experience", "education", "skills", "projects", "certifications"}
    for section_type, section_text in parsed.get("sections_raw", {}).items():
        if section_type in handled:
            continue
        if len(section_text) >= MIN_CHUNK_CHARS:
            words = section_text.split()
            capped = " ".join(words[:512])
            chunks.append(make_chunk(cid, source, section_type, capped))

    return chunks

def run_chunking(parsed_path: Path, output_path: Path):
    with open(parsed_path, "r", encoding="utf-8") as f:
        records = json.load(f)
    print(f"Loaded {len(records)} resumes. Chunking...")
    all_chunks = []
    for r in tqdm(records):
        all_chunks.extend(chunk_resume(r))
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(all_chunks)} chunks to {output_path}")

if __name__ == "__main__":
    PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
    run_chunking(PROCESSED_DIR / "resumes_parsed.json", PROCESSED_DIR / "resume_chunks.json")
