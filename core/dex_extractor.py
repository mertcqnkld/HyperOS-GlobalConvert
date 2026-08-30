import os
import re
import zipfile
import shutil
from typing import List, Dict

def get_dex_sort_key(dex_filename: str) -> int:
    """Natural sorting key for DEX files (classes.dex -> 1, classes2.dex -> 2, ...)."""
    match = re.match(r"^classes(\d*)\.dex$", dex_filename, re.IGNORECASE)
    if not match:
        return 999999
    num_str = match.group(1)
    return int(num_str) if num_str else 1

def extract_dex_files(apk_path: str, output_dir: str) -> List[str]:
    """
    Extracts all classes*.dex files from the APK into output_dir.
    Returns a sorted list of absolute paths to extracted DEX files.
    """
    os.makedirs(output_dir, exist_ok=True)
    extracted_dex_files = []

    with zipfile.ZipFile(apk_path, "r") as zf:
        namelist = zf.namelist()
        dex_names = [n for n in namelist if re.match(r"^classes\d*\.dex$", n, re.IGNORECASE)]
        dex_names.sort(key=get_dex_sort_key)

        if not dex_names:
            raise ValueError(f"No classes*.dex files found in APK archive: {apk_path}")

        for dex_name in dex_names:
            out_file = os.path.join(output_dir, os.path.basename(dex_name))
            with zf.open(dex_name) as source, open(out_file, "wb") as target:
                shutil.copyfileobj(source, target)
            extracted_dex_files.append(out_file)

    return extracted_dex_files

def repackage_apk_with_new_dex(
    original_apk_path: str,
    new_dex_map: Dict[str, str],  # {"classes.dex": "/path/to/new_classes.dex", ...}
    output_apk_path: str
) -> str:
    """
    Creates a new APK from original_apk_path by replacing only the DEX files specified
    in new_dex_map. All other files (resources, manifest, assets, native libs) remain
    100% bit-exact and untouched.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_apk_path)), exist_ok=True)
    temp_apk = output_apk_path + ".tmp"

    with zipfile.ZipFile(original_apk_path, "r") as zin, zipfile.ZipFile(temp_apk, "w") as zout:
        # Copy all items except the ones in new_dex_map and old signature files (META-INF/*.SF, *.RSA, *.MF)
        for item in zin.infolist():
            filename = item.filename
            
            # Skip old signature files since we will re-sign the APK cleanly
            if filename.startswith("META-INF/") and (filename.endswith(".SF") or filename.endswith(".RSA") or filename.endswith(".DSA") or filename.endswith(".MF") or filename.endswith(".EC")):
                continue

            if filename in new_dex_map:
                # Replace with newly compiled DEX
                new_dex_file = new_dex_map[filename]
                with open(new_dex_file, "rb") as df:
                    data = df.read()
                
                # DEX files in APKs are typically stored with DEFLATE
                zinfo = zipfile.ZipInfo(filename=filename, date_time=item.date_time)
                zinfo.compress_type = zipfile.ZIP_DEFLATED
                zinfo.create_system = item.create_system
                zout.writestr(zinfo, data)
            else:
                # Copy original untouched file
                data = zin.read(filename)
                zinfo = zipfile.ZipInfo(filename=filename, date_time=item.date_time)
                zinfo.compress_type = item.compress_type
                zinfo.create_system = item.create_system
                zout.writestr(zinfo, data)

    if os.path.exists(output_apk_path):
        os.remove(output_apk_path)
    os.rename(temp_apk, output_apk_path)

    return output_apk_path
