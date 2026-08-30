import os
import shutil
import subprocess
import requests
from typing import Callable, Optional

BAKSMALI_VERSION = "2.5.2"
SMALI_VERSION = "2.5.2"

BAKSMALI_URLS = [
    f"https://bitbucket.org/JesusFreke/smali/downloads/baksmali-{BAKSMALI_VERSION}.jar",
    f"https://github.com/JesusFreke/smali/releases/download/v{BAKSMALI_VERSION}/baksmali-{BAKSMALI_VERSION}.jar",
    f"https://raw.githubusercontent.com/skylot/jadx/master/jadx-core/src/test/resources/bin/baksmali-{BAKSMALI_VERSION}.jar",
]

SMALI_URLS = [
    f"https://bitbucket.org/JesusFreke/smali/downloads/smali-{SMALI_VERSION}.jar",
    f"https://github.com/JesusFreke/smali/releases/download/v{SMALI_VERSION}/smali-{SMALI_VERSION}.jar",
]

def get_tools_dir() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tools_dir = os.path.join(base_dir, "tools", "bin")
    os.makedirs(tools_dir, exist_ok=True)
    return tools_dir

def download_jar(urls: list, dest_path: str, name: str, progress_callback: Optional[Callable[[str], None]] = None):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 100000:
        return dest_path

    if progress_callback:
        progress_callback(f"Downloading {name} tool...")

    headers = {"User-Agent": "Mozilla/5.0"}
    last_error = None
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=30, stream=True)
            if r.status_code == 200:
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=32768):
                        if chunk:
                            f.write(chunk)
                if os.path.getsize(dest_path) > 100000:
                    if progress_callback:
                        progress_callback(f"{name} ready ({os.path.basename(dest_path)})")
                    return dest_path
        except Exception as e:
            last_error = e
            continue

    if not os.path.exists(dest_path) or os.path.getsize(dest_path) <= 100000:
        raise RuntimeError(f"Failed to download {name} from available mirrors. Last error: {last_error}")
    return dest_path

def ensure_smali_tools(progress_callback: Optional[Callable[[str], None]] = None) -> tuple:
    tools_dir = get_tools_dir()
    baksmali_path = os.path.join(tools_dir, f"baksmali-{BAKSMALI_VERSION}.jar")
    smali_path = os.path.join(tools_dir, f"smali-{SMALI_VERSION}.jar")

    baksmali_path = download_jar(BAKSMALI_URLS, baksmali_path, "baksmali", progress_callback)
    smali_path = download_jar(SMALI_URLS, smali_path, "smali", progress_callback)

    return baksmali_path, smali_path

def check_java_installed() -> bool:
    try:
        res = subprocess.run(["java", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0
    except Exception:
        return False

def disassemble_dex(
    dex_path: str,
    output_dir: str,
    baksmali_jar: Optional[str] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> str:
    """Disassembles a .dex file into a smali directory."""
    if not check_java_installed():
        raise RuntimeError("Java Runtime Environment (JRE/JDK) is required to run baksmali/smali but was not found in PATH.")

    if not baksmali_jar or not os.path.exists(baksmali_jar):
        baksmali_jar, _ = ensure_smali_tools(progress_callback)

    os.makedirs(output_dir, exist_ok=True)
    dex_name = os.path.basename(dex_path)

    if progress_callback:
        progress_callback(f"Disassembling {dex_name} -> smali...")

    cmd = ["java", "-jar", baksmali_jar, "d", dex_path, "-o", output_dir]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if res.returncode != 0:
        raise RuntimeError(f"baksmali failed on {dex_name}:\n{res.stderr}\n{res.stdout}")

    return output_dir

def assemble_smali(
    smali_dir: str,
    output_dex_path: str,
    smali_jar: Optional[str] = None,
    api_level: int = 28,
    progress_callback: Optional[Callable[[str], None]] = None
) -> str:
    """Assembles a smali directory back into a .dex file."""
    if not check_java_installed():
        raise RuntimeError("Java Runtime Environment (JRE/JDK) is required to run smali but was not found in PATH.")

    if not smali_jar or not os.path.exists(smali_jar):
        _, smali_jar = ensure_smali_tools(progress_callback)

    os.makedirs(os.path.dirname(os.path.abspath(output_dex_path)), exist_ok=True)
    dex_name = os.path.basename(output_dex_path)

    if progress_callback:
        progress_callback(f"Assembling smali -> {dex_name}...")

    cmd = ["java", "-jar", smali_jar, "a", smali_dir, "-o", output_dex_path, "--api", str(api_level)]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if res.returncode != 0:
        raise RuntimeError(f"smali assembly failed for {dex_name}:\n{res.stderr}\n{res.stdout}")

    if not os.path.exists(output_dex_path) or os.path.getsize(output_dex_path) == 0:
        raise RuntimeError(f"Generated DEX file is missing or 0 bytes: {output_dex_path}")

    return output_dex_path
