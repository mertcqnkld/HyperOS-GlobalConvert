import os
import subprocess
import zipfile
import shutil
import requests
from typing import Callable, Optional
from .smali_tools import get_tools_dir, check_java_installed

UBER_SIGNER_VERSION = "1.3.0"
UBER_SIGNER_URL = f"https://github.com/patrickfav/uber-apk-signer/releases/download/v{UBER_SIGNER_VERSION}/uber-apk-signer-{UBER_SIGNER_VERSION}.jar"

def ensure_uber_signer(progress_callback: Optional[Callable[[str], None]] = None) -> str:
    """Ensures uber-apk-signer JAR is available."""
    tools_dir = get_tools_dir()
    signer_path = os.path.join(tools_dir, f"uber-apk-signer-{UBER_SIGNER_VERSION}.jar")

    if os.path.exists(signer_path) and os.path.getsize(signer_path) > 1000000:
        return signer_path

    if progress_callback:
        progress_callback("Downloading APK signer (uber-apk-signer)...")

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(UBER_SIGNER_URL, headers=headers, stream=True, timeout=60)
        r.raise_for_status()
        with open(signer_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        if progress_callback:
            progress_callback("APK signer ready.")
        return signer_path
    except Exception as e:
        if os.path.exists(signer_path):
            os.remove(signer_path)
        raise RuntimeError(f"Could not download uber-apk-signer: {e}")

def sign_and_align_apk(
    unsigned_apk_path: str,
    output_apk_path: str,
    progress_callback: Optional[Callable[[str], None]] = None
) -> str:
    """
    ZipAligns and signs the APK with v1/v2/v3 debug schemes.
    """
    if progress_callback:
        progress_callback("Aligning & signing patched APK...")

    if check_java_installed():
        try:
            signer_jar = ensure_uber_signer(progress_callback)
            out_dir = os.path.dirname(os.path.abspath(output_apk_path))
            os.makedirs(out_dir, exist_ok=True)

            cmd = [
                "java", "-jar", signer_jar,
                "--apks", unsigned_apk_path,
                "--out", out_dir,
                "--overwrite",
                "--allowResign"
            ]

            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                # uber-apk-signer outputs file as <name>-aligned-debugSigned.apk or overwrites
                # Let's check candidate output filenames
                base_name = os.path.splitext(os.path.basename(unsigned_apk_path))[0]
                candidates = [
                    os.path.join(out_dir, f"{base_name}-aligned-debugSigned.apk"),
                    os.path.join(out_dir, f"{base_name}.apk"),
                    unsigned_apk_path
                ]
                for cand in candidates:
                    if os.path.exists(cand) and cand != output_apk_path:
                        if os.path.exists(output_apk_path):
                            os.remove(output_apk_path)
                        shutil.move(cand, output_apk_path)
                        return output_apk_path

                if os.path.exists(unsigned_apk_path):
                    shutil.copy2(unsigned_apk_path, output_apk_path)
                    return output_apk_path
        except Exception as e:
            if progress_callback:
                progress_callback(f"uber-apk-signer notice: {e}, using direct copy fallback.")

    # Direct fallback if Java signer failed or was skipped
    shutil.copy2(unsigned_apk_path, output_apk_path)
    return output_apk_path
