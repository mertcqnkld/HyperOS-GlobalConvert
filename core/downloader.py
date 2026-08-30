import os
import re
import urllib.parse
from typing import Callable, Optional
import requests

def extract_filename_from_url(url: str, response: Optional[requests.Response] = None) -> str:
    """Extract a reasonable APK filename from HTTP headers or URL."""
    if response and "content-disposition" in response.headers:
        cd = response.headers["content-disposition"]
        fname_match = re.findall(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\n]+)["\']?', cd, re.IGNORECASE)
        if fname_match:
            candidate = os.path.basename(urllib.parse.unquote(fname_match[0]))
            if candidate.lower().endswith(".apk"):
                return candidate
            return f"{candidate}.apk"

    parsed = urllib.parse.urlparse(url)
    path_name = os.path.basename(parsed.path)
    if path_name:
        clean_name = urllib.parse.unquote(path_name)
        if clean_name.lower().endswith(".apk"):
            return clean_name
        return f"{clean_name}.apk"

    return "target_app.apk"

def is_valid_zip_or_apk(file_path: str) -> bool:
    """Check if the downloaded file has a valid ZIP/APK magic header."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) < 22:
        return False
    with open(file_path, "rb") as f:
        magic = f.read(4)
        return magic.startswith(b"PK\x03\x04") or magic.startswith(b"PK\x05\x06") or magic.startswith(b"PK\x07\x08")

def download_apk(
    url_or_path: str,
    target_dir: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    timeout: int = 60
) -> str:
    """
    Downloads an APK from a URL or copies from a local path into target_dir.
    Returns the absolute path to the local APK.
    """
    os.makedirs(target_dir, exist_ok=True)

    # If it's already a local file path
    if os.path.exists(url_or_path) and os.path.isfile(url_or_path):
        filename = os.path.basename(url_or_path)
        dest_path = os.path.join(target_dir, filename)
        if os.path.abspath(url_or_path) != os.path.abspath(dest_path):
            import shutil
            shutil.copy2(url_or_path, dest_path)
        if not is_valid_zip_or_apk(dest_path):
            raise ValueError(f"Local file '{url_or_path}' is not a valid APK/ZIP archive.")
        if progress_callback:
            progress_callback(100, 100, f"Local APK loaded: {filename}")
        return dest_path

    # Clean URL
    url = url_or_path.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError(f"Invalid APK URL or file path: '{url_or_path}'. Must start with http:// or https://")

    # Handle Google Drive share links
    if "drive.google.com" in url:
        file_id_match = re.search(r"/d/([a-zA-Z0-9_-]+)", url) or re.search(r"id=([a-zA-Z0-9_-]+)", url)
        if file_id_match:
            file_id = file_id_match.group(1)
            url = f"https://drive.google.com/uc?export=download&id={file_id}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*"
    }

    if progress_callback:
        progress_callback(0, 0, f"Connecting to {url}...")

    session = requests.Session()
    response = session.get(url, headers=headers, stream=True, timeout=timeout, allow_redirects=True)
    response.raise_for_status()

    # Google Drive confirmation page check
    if "drive.google.com" in response.url and "confirm=" not in url:
        for key, value in response.cookies.items():
            if key.startswith("download_warning"):
                url = f"{url}&confirm={value}"
                response = session.get(url, headers=headers, stream=True, timeout=timeout, allow_redirects=True)
                break

    filename = extract_filename_from_url(response.url, response)
    dest_path = os.path.join(target_dir, filename)

    total_size = int(response.headers.get("content-length", 0))
    downloaded = 0
    chunk_size = 64 * 1024  # 64 KB

    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    pct = int(downloaded * 100 / total_size) if total_size > 0 else 0
                    msg = f"Downloading: {downloaded / (1024 * 1024):.2f} MB" + (
                        f" / {total_size / (1024 * 1024):.2f} MB" if total_size > 0 else ""
                    )
                    progress_callback(downloaded, total_size, msg)

    if not is_valid_zip_or_apk(dest_path):
        # Inspect first few bytes to give a helpful error
        with open(dest_path, "rb") as f:
            sample = f.read(256)
        if b"<html" in sample.lower() or b"<!doctype html" in sample.lower():
            os.remove(dest_path)
            raise ValueError("The provided URL returned an HTML web page instead of a direct APK file binary. Please provide a direct download link.")
        os.remove(dest_path)
        raise ValueError("Downloaded file is corrupt or not a valid Android APK (ZIP signature missing).")

    if progress_callback:
        progress_callback(100, 100, f"Download complete: {filename}")

    return dest_path
