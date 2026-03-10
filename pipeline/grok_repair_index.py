import json
import os
import sys
from pathlib import Path
from tqdm import tqdm
import concurrent.futures

# Add streamlit dir to path for grok_utils
sys.path.append(str(Path(__file__).parent.parent / "streamlit"))
try:
    from grok_utils import repair_resume_parse, enrich_whole_resume
    from rechunk import run_chunking
except ImportError:
    # Fallback if running from a different context
    sys.path.append(os.getcwd())
    from streamlit.grok_utils import repair_resume_parse, enrich_whole_resume
    from pipeline.rechunk import run_chunking

PROJECT_ROOT = Path(__file__).parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXTRACTED_PATH = PROCESSED_DIR / "resumes_extracted.json"
PARSED_PATH = PROCESSED_DIR / "resumes_parsed.json"
REPAIRED_PATH = PROCESSED_DIR / "resumes_parsed.json" # We'll overwrite or save to a new one then swap

def is_low_quality(candidate: dict) -> bool:
    """Heuristic to detect messy parses."""
    exp = candidate.get("experience", [])
    proj = candidate.get("projects", [])
    
    # 1. Experience is a single giant block with no company detected
    if len(exp) == 1:
        raw_text = exp[0].get("raw_text", "")
        # If it's more than 8 lines and no separate company found
        if len(raw_text.splitlines()) > 8 and not exp[0].get("company"):
            return True
            
    # 2. Key sections are missing but text is substantial
    word_count = candidate.get("word_count", 0)
    if word_count > 250 and not exp and not proj:
        return True
        
    # 3. Skills list looks like a single concatenated string
    skills = candidate.get("skills", [])
    if len(skills) == 1 and "," in skills[0]:
        return True
    
    # 4. Completely empty or extremely sparse
    if not exp and not proj and word_count <= 250:
        return True
        
    return False

def main():
    if not os.environ.get("XAI_API_KEY"):
        print("XAI_API_KEY environment variable not set. Exiting.")
        return

    print(f"Loading data from {PARSED_PATH}...")
    with open(PARSED_PATH, "r") as f:
        parsed_data = json.load(f)
        
    print(f"Loading raw text from {EXTRACTED_PATH}...")
    with open(EXTRACTED_PATH, "r") as f:
        extracted_data = json.load(f)
    
    # Map extracted text for easy lookup
    raw_text_map = {item["filename"]: item["text"] for item in extracted_data}

    to_repair = [c for c in parsed_data if is_low_quality(c)]
    print(f"Detected {len(to_repair)} potential low-quality parses out of {len(parsed_data)}.")
    repaired_count = 0
    
    def _process_candidate(raw: str, cand: dict):
        rep = repair_resume_parse(raw, cand)
        exp_count = len(rep.get("experience_entries", []))
        proj_count = len(rep.get("project_entries", []))
        
        # If still critically sparse, try whole-resume enrichment
        if exp_count == 0 and proj_count == 0:
            return enrich_whole_resume(raw, cand), True
        return rep, False

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_candidate = {
            executor.submit(_process_candidate, raw_text_map.get(c["candidate_id"], ""), c): c 
            for c in to_repair if raw_text_map.get(c["candidate_id"])
        }
        
        for future in tqdm(concurrent.futures.as_completed(future_to_candidate), total=len(future_to_candidate), desc="Repairing with Grok"):
            original = future_to_candidate[future]
            try:
                repaired_fields, is_enriched = future.result()
                
                # If enriched, the payload contains full schema, so we update the original object
                if is_enriched:
                    if "full_name" in repaired_fields:
                        original["full_name"] = repaired_fields["full_name"]
                    if "contact" in repaired_fields:
                        original["contact"] = repaired_fields["contact"]
                    if "summary" in repaired_fields:
                        original["summary"] = repaired_fields["summary"]
                    if "education" in repaired_fields:
                        original["education"] = repaired_fields["education"]
                
                if repaired_fields and (repaired_fields.get("experience_entries") or repaired_fields.get("project_entries")):
                    # Update experience
                    if "experience_entries" in repaired_fields and len(repaired_fields["experience_entries"]) > 0:
                        original["experience"] = [
                            {
                                "raw_header": f"{e.get('title', 'Position')} at {e.get('company', 'Unknown')}",
                                "company": e.get("company", ""),
                                "company_normalized": e.get("company_normalized", ""),
                                "title": e.get("title", ""),
                                "dates": [e.get("dates", "")] if e.get("dates") else [],
                                "location": e.get("location", ""),
                                "bullets": e.get("bullets", []),
                                "technologies": e.get("technologies", []),
                                "raw_text": "\n".join(e.get("bullets", []))
                            }
                            for e in repaired_fields["experience_entries"]
                        ]
                    # Update projects
                    if "project_entries" in repaired_fields and len(repaired_fields["project_entries"]) > 0:
                        original["projects"] = [
                            {
                                "raw_header": p.get("name", "Project"),
                                "name": p.get("name", ""),
                                "dates": p.get("dates", ""),
                                "location": p.get("location", ""),
                                "bullets": p.get("bullets", []),
                                "technologies": p.get("technologies", []),
                                "raw_text": "\n".join(p.get("bullets", []))
                            }
                            for p in repaired_fields["project_entries"]
                        ]
                    # Update skills
                    if "canonical_skills" in repaired_fields:
                        original["skills"] = repaired_fields["canonical_skills"]
                    elif "skills" in repaired_fields:
                        original["skills"] = repaired_fields["skills"]
                    
                    # Metadata
                    original["parse_warnings"] = repaired_fields.get("parse_warnings", [])
                    original["summary_flags"] = repaired_fields.get("summary_flags", ["Grok Whole-Resume Enrich"] if is_enriched else [])
                    original["is_grok_repaired"] = True
                    repaired_count += 1
            except Exception as e:
                print(f"Failed to repair {original['candidate_id']}: {e}")

    # Save a backup first
    backup_path = PARSED_PATH.with_suffix(".json.bak")
    os.rename(PARSED_PATH, backup_path)
    
    with open(PARSED_PATH, "w") as f:
        json.dump(parsed_data, f, indent=2)
        
    print(f"Done. Overwrote {PARSED_PATH} with repaired data. {repaired_count} candidates improved.")
    print(f"Backup saved to {backup_path}")

    # Re-run chunking
    print("Triggering re-chunking of repaired data...")
    CHUNKS_PATH = PROCESSED_DIR / "resume_chunks.json"
    run_chunking(PARSED_PATH, CHUNKS_PATH)
    print("Re-chunking complete. You should now re-run 03_embeddings and 04_2_faiss_indexing to fully refresh the index.")

if __name__ == "__main__":
    main()
