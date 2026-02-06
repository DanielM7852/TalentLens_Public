import hashlib
import os

def file_hash(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_user_resumes(user_dir):
    return [
        os.path.join(user_dir, f)
        for f in os.listdir(user_dir)
        if os.path.isfile(os.path.join(user_dir, f))
    ]

def is_exact_duplicate(new_resume_path, existing_resumes):
    new_hash = file_hash(new_resume_path)
    for resume in existing_resumes:
        if file_hash(resume) == new_hash:
            return True
    return False

def get_newest_resume(resumes):
    return max(resumes, key=os.path.getmtime)

def replace_old_resumes(new_resume_path, existing_resumes):
    for resume in existing_resumes:
        print("Removing old version:", resume)
        os.remove(resume) 

def handle_resume_upload(user_id, new_resume_path):
    base_dir = "resumes"
    user_dir = os.path.join(base_dir, f"user_{user_id}")

    os.makedirs(user_dir, exist_ok=True)

    existing_resumes = get_user_resumes(user_dir)

    if is_exact_duplicate(new_resume_path, existing_resumes):
        print("Exact duplicate detected. Upload rejected.")
        os.remove(new_resume_path)
        return

    if existing_resumes:
        newest_existing = get_newest_resume(existing_resumes)
        if os.path.getmtime(new_resume_path) > os.path.getmtime(newest_existing):
            replace_old_resumes(new_resume_path, existing_resumes)

    final_path = os.path.join(user_dir, os.path.basename(new_resume_path))
    os.rename(new_resume_path, final_path)

    print("Resume uploaded successfully:", final_path)