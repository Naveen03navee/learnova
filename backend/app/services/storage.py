import re
from typing import Optional
from supabase import Client
from app.core.config import settings

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and ensure safe storage paths.
    Only allows alphanumeric, dot, dash, and underscore.
    """
    if not filename:
        return "unnamed_file"
    
    # Remove any directory traversal attempts
    filename = filename.replace("..", "").replace("/", "").replace("\\", "")
    
    # Replace anything that isn't alphanumeric, dot, dash, or underscore with underscore
    filename = re.sub(r'[^a-zA-Z0-9.\-_]', '_', filename)
    
    return filename

def generate_storage_path(exam_id: str, subject_id: str, folder_id: Optional[str], resource_id: str, filename: str) -> str:
    """
    Generates a predictable storage path for a resource.
    """
    sanitized = sanitize_filename(filename)
    
    if folder_id:
        return f"exam/{exam_id}/subject/{subject_id}/folder/{folder_id}/{resource_id}_{sanitized}"
    else:
        return f"exam/{exam_id}/subject/{subject_id}/root/{resource_id}_{sanitized}"

def upload_file_to_storage(supabase: Client, path: str, file_bytes: bytes, content_type: str) -> None:
    """
    Uploads a file to Supabase Storage.
    Raises Exception if upload fails.
    """
    bucket = settings.SUPABASE_STORAGE_BUCKET
    try:
        # Check if bucket exists? The user prompt said:
        # "If the bucket does not exist, provide the required Supabase setup/migration instructions."
        # We assume it exists for the API call, and if it fails, it will throw an exception.
        res = supabase.storage.from_(bucket).upload(
            file=file_bytes,
            path=path,
            file_options={"content-type": content_type}
        )
    except Exception as e:
        raise RuntimeError(f"Failed to upload file to storage: {str(e)}")

def delete_file_from_storage(supabase: Client, path: str) -> None:
    """
    Deletes a file from Supabase Storage.
    """
    bucket = settings.SUPABASE_STORAGE_BUCKET
    try:
        supabase.storage.from_(bucket).remove([path])
    except Exception as e:
        raise RuntimeError(f"Failed to delete file from storage: {str(e)}")

def download_file_from_storage(supabase: Client, path: str) -> bytes:
    """
    Downloads a file's bytes from Supabase Storage.
    """
    bucket = settings.SUPABASE_STORAGE_BUCKET
    try:
        res = supabase.storage.from_(bucket).download(path)
        return res
    except Exception as e:
        raise RuntimeError(f"Failed to download file from storage: {str(e)}")

def generate_signed_url(supabase: Client, path: str, expires_in_seconds: int = 3600) -> str:
    """
    Generates a temporary signed download URL for a file in Supabase Storage.
    """
    bucket = settings.SUPABASE_STORAGE_BUCKET
    try:
        res = supabase.storage.from_(bucket).create_signed_url(path, expires_in_seconds)
        if hasattr(res, 'signed_url'):
            return res.signed_url
        if isinstance(res, dict) and 'signedURL' in res:
            return res['signedURL']
        return str(res) # fallback depending on supabase-py version
    except Exception as e:
        raise RuntimeError(f"Failed to generate signed URL: {str(e)}")
