import hashlib
import os
from datetime import datetime
from pathlib import Path
import json


print("hello")
def file_hash(path): 
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def pdf_content_hash(path):
    try:
        import PyPDF2
        hasher = hashlib.sha256()
        
        with open(path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                hasher.update(text.encode('utf-8'))
        return hasher.hexdigest()
    except ImportError:
        print("Warning: PyPDF2 not installed. Using file hash instead.")
        return file_hash(path)
    except Exception as e:
        print(f"Error extracting PDF content: {e}. Using file hash instead.")
        return file_hash(path)
    
def get_user_resumes(user_dir):
    if not os.path.exists(user_dir):
        return []
    
    return [
        os.path.join(user_dir, f)
        for f in os.listdir(user_dir)
        if os.path.isfile(os.path.join(user_dir, f)) and f.lower().endswith('.pdf')
    ]

def is_exact_duplicate(new_resume_path, existing_resumes, use_content_hash=True):
    if use_content_hash and new_resume_path.lower().endswith('.pdf'):
        new_hash = pdf_content_hash(new_resume_path)
    else:
        new_hash = file_hash(new_resume_path)
    
    for resume in existing_resumes:
        if use_content_hash and resume.lower().endswith('.pdf'):
            existing_hash = pdf_content_hash(resume)
        else:
            existing_hash = file_hash(resume)
        
        if existing_hash == new_hash:
            return True, resume
    return False, None

def get_newest_resume(resumes):
    if not resumes:
        return None
    return max(resumes, key=os.path.getmtime)\
    
def get_file_metadata(file_path):
    stat = os.stat(file_path)
    return {
        'path': file_path,
        'filename': os.path.basename(file_path),
        'size': stat.st_size,
        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'modified_timestamp': stat.st_mtime,
        'hash': pdf_content_hash(file_path) if file_path.lower().endswith('.pdf') else file_hash(file_path)
    }

def replace_old_resumes(new_resume_path, existing_resumes, keep_newest=True):
    resumes_to_remove = []

    if keep_newest:
        new_mtime = os.path.getmtime(new_resume_path)
        for resume in existing_resumes:
            if os.path.getmtime(resume) < new_mtime:
                resumes_to_remove.append(resume)
            else:
                print(f"Keeping existing resume (newer): {resume}")
    else:
        resumes_to_remove = existing_resumes
    
    for resume in resumes_to_remove:
        print(f"Removing old version: {resume}")
        os.remove(resume)
    
    return len(resumes_to_remove)

def handle_resume_upload(user_id, new_resume_path, base_dir="resumes", use_content_hash=True):
    user_dir = os.path.join(base_dir, f"user_{user_id}")
    os.makedirs(user_dir, exist_ok=True)
    
    if not os.path.exists(new_resume_path):
        return {
            'success': False,
            'message': 'File not found',
            'action': 'rejected'
        }
    
    existing_resumes = get_user_resumes(user_dir)
    is_dup, duplicate_path = is_exact_duplicate(new_resume_path, existing_resumes, use_content_hash)
    
    if is_dup:
        print("Exact duplicate detected. Upload rejected.")
        print(f"Duplicate of: {duplicate_path}")
        os.remove(new_resume_path)
        return {
            'success': False,
            'message': 'Exact duplicate detected',
            'action': 'rejected',
            'duplicate_of': duplicate_path
        }
    
    removed_count = 0
    if existing_resumes:
        newest_existing = get_newest_resume(existing_resumes)
        new_mtime = os.path.getmtime(new_resume_path)
        newest_existing_mtime = os.path.getmtime(newest_existing)
        
        if new_mtime > newest_existing_mtime:
            removed_count = replace_old_resumes(new_resume_path, existing_resumes)
            action = 'replaced'
        else:
            print("New resume is older than existing resume. Keeping both.")
            action = 'added'
    else:
        action = 'uploaded'
    
    final_filename = f"resume_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    final_path = os.path.join(user_dir, final_filename)
    
    if os.path.exists(final_path):
        base, ext = os.path.splitext(final_filename)
        counter = 1
        while os.path.exists(final_path):
            final_filename = f"{base}_{counter}{ext}"
            final_path = os.path.join(user_dir, final_filename)
            counter += 1
    
    os.rename(new_resume_path, final_path)
    print(f"Resume uploaded successfully: {final_path}")
    
    return {
        'success': True,
        'message': 'Resume uploaded successfully',
        'action': action,
        'final_path': final_path,
        'removed_count': removed_count
    }

def find_all_duplicates(base_dir="resumes", use_content_hash=True):
    hash_map = {}
    
    if not os.path.exists(base_dir):
        return hash_map
    
    for user_folder in os.listdir(base_dir):
        user_dir = os.path.join(base_dir, user_folder)
        if os.path.isdir(user_dir):
            resumes = get_user_resumes(user_dir)
            
            for resume in resumes:
                if use_content_hash and resume.lower().endswith('.pdf'):
                    file_hash_value = pdf_content_hash(resume)
                else:
                    file_hash_value = file_hash(resume)
                
                if file_hash_value not in hash_map:
                    hash_map[file_hash_value] = []
                hash_map[file_hash_value].append(resume)

    duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}
    
    return duplicates

def generate_duplicate_report(base_dir="resumes", use_content_hash=True):
    duplicates = find_all_duplicates(base_dir, use_content_hash)
    
    if not duplicates:
        print("No duplicates found!")
        return
    
    print(f"\n{'='*80}")
    print(f"DUPLICATE RESUME REPORT")
    print(f"{'='*80}\n")
    
    for i, (hash_value, files) in enumerate(duplicates.items(), 1):
        print(f"Duplicate Set #{i}")
        print(f"Hash: {hash_value}")
        print(f"Number of copies: {len(files)}")
        print(f"Files:")
        
        for file_path in sorted(files):
            metadata = get_file_metadata(file_path)
            print(f"  - {file_path}")
            print(f"    Modified: {metadata['modified']}")
            print(f"    Size: {metadata['size']} bytes")
        print()