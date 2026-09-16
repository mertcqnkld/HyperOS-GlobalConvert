import os
import shutil
import tempfile
import traceback
from typing import Callable, Optional, List, Dict
from .models import PipelineResult, PatchItem, SkippedItem, VerificationResult
from .downloader import download_apk
from .dex_extractor import extract_dex_files, repackage_apk_with_new_dex
from .smali_tools import ensure_smali_tools, disassemble_dex, assemble_smali
from .patcher import patch_smali_directory
from .verifier import verify_all_dex_diffs
from .signer import sign_and_align_apk

ProgressCallback = Callable[[int, str, str, Optional[Dict]], None]

def run_patch_pipeline(
    apk_source: str,
    output_dir: str = "output",
    work_dir: Optional[str] = None,
    progress_callback: Optional[ProgressCallback] = None,
    keep_temp: bool = False
) -> PipelineResult:
    """
    Executes the end-to-end automated APK patch pipeline:
    1. Download / Load APK
    2. Extract DEX files (classes*.dex)
    3. Disassemble DEX to Smali
    4. Patch IS_INTERNATIONAL_BUILD in executable method code
    5. Perform strict diff verification
    6. Reassemble Smali to DEX
    7. Repackage into pristine APK container
    8. Align & Sign final APK
    """
    logs: List[str] = []
    
    def log(msg: str, stage: str = "INFO", pct: int = -1, data: Optional[Dict] = None):
        formatted = f"[{stage}] {msg}"
        logs.append(formatted)
        if progress_callback and pct >= 0:
            progress_callback(pct, msg, stage, data)

    temp_root = work_dir or tempfile.mkdtemp(prefix="apk_patcher_")
    output_apk_path = None
    all_patches: List[PatchItem] = []
    all_skipped: List[SkippedItem] = []
    verification: Optional[VerificationResult] = None

    try:
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(temp_root, exist_ok=True)

        # -------------------------------------------------------------
        # STEP 1: Download / Acquire APK
        # -------------------------------------------------------------
        log("Downloading / loading target APK...", stage="DOWNLOAD", pct=10)
        download_dir = os.path.join(temp_root, "download")
        local_apk = download_apk(
            apk_source,
            download_dir,
            progress_callback=lambda cur, tot, msg: log(msg, stage="DOWNLOAD", pct=10 + int(10 * (cur / max(tot, 1))))
        )
        apk_filename = os.path.basename(local_apk)
        log(f"Acquired APK: {apk_filename}", stage="DOWNLOAD", pct=20)

        # Ensure tooling is ready
        log("Checking Smali/Baksmali environment...", stage="INIT", pct=25)
        baksmali_jar, smali_jar = ensure_smali_tools(progress_callback=lambda msg: log(msg, stage="INIT"))

        # -------------------------------------------------------------
        # STEP 2: Extract DEX files
        # -------------------------------------------------------------
        log("Extracting classes*.dex from APK...", stage="EXTRACT", pct=30)
        extracted_dex_dir = os.path.join(temp_root, "dex_extracted")
        dex_paths = extract_dex_files(local_apk, extracted_dex_dir)
        total_dex_count = len(dex_paths)
        log(f"Found {total_dex_count} DEX file(s): {[os.path.basename(p) for p in dex_paths]}", stage="EXTRACT", pct=35)

        # -------------------------------------------------------------
        # STEP 3 & 4: Disassemble DEX to Smali & Prepare Verification Baseline
        # -------------------------------------------------------------
        orig_smali_dirs: Dict[str, str] = {}
        work_smali_dirs: Dict[str, str] = {}

        smali_base_dir = os.path.join(temp_root, "smali_work")
        for i, dex_path in enumerate(dex_paths):
            dex_name = os.path.basename(dex_path)
            dex_tag = os.path.splitext(dex_name)[0]
            
            orig_dir = os.path.join(smali_base_dir, f"{dex_tag}_orig")
            work_dir_dex = os.path.join(smali_base_dir, f"{dex_tag}_work")

            log(f"Disassembling {dex_name}...", stage="DISASSEMBLE", pct=35 + int(15 * (i / total_dex_count)))
            disassemble_dex(dex_path, orig_dir, baksmali_jar)
            
            # Create working copy for patching
            shutil.copytree(orig_dir, work_dir_dex)

            orig_smali_dirs[dex_name] = orig_dir
            work_smali_dirs[dex_name] = work_dir_dex

        # -------------------------------------------------------------
        # STEP 5: Scan & Patch Smali Files
        # -------------------------------------------------------------
        log("Scanning & patching IS_INTERNATIONAL_BUILD usages...", stage="PATCH", pct=55)
        for dex_name, work_dir_dex in work_smali_dirs.items():
            scan_res = patch_smali_directory(work_dir_dex, dex_name=dex_name)
            all_patches.extend(scan_res.patches)
            all_skipped.extend(scan_res.skipped)
            log(f"{dex_name}: {len(scan_res.patches)} executable patches applied, {len(scan_res.skipped)} non-executable references skipped.", stage="PATCH")

        total_patches = len(all_patches)
        log(f"Total executable patches identified: {total_patches}", stage="PATCH", pct=65)

        # -------------------------------------------------------------
        # STEP 6: Strict Diff Verification
        # -------------------------------------------------------------
        log("Performing strict pre/post diff verification...", stage="VERIFY", pct=70)
        verification = verify_all_dex_diffs(orig_smali_dirs, work_smali_dirs, all_patches)

        if not verification.is_valid:
            error_details = "\n".join(verification.errors)
            raise RuntimeError(
                f"Diff verification FAILED! Unauthorized or invalid code modifications detected:\n{error_details}"
            )
        
        log(f"Verification PASSED! {verification.total_patches_verified} patch(es) audited and 100% compliant with strict rules.", stage="VERIFY", pct=75)

        # -------------------------------------------------------------
        # STEP 7: Reassemble Smali back to DEX
        # -------------------------------------------------------------
        new_dex_map: Dict[str, str] = {}
        new_dex_dir = os.path.join(temp_root, "dex_assembled")
        os.makedirs(new_dex_dir, exist_ok=True)

        for i, (dex_name, work_dir_dex) in enumerate(work_smali_dirs.items()):
            log(f"Reassembling {dex_name}...", stage="ASSEMBLE", pct=75 + int(10 * (i / total_dex_count)))
            out_dex_file = os.path.join(new_dex_dir, dex_name)
            assemble_smali(work_dir_dex, out_dex_file, smali_jar)
            new_dex_map[dex_name] = out_dex_file

        # -------------------------------------------------------------
        # STEP 8: Lossless Repackaging
        # -------------------------------------------------------------
        log("Repackaging APK with modified DEX files...", stage="REPACKAGE", pct=85)
        base_name_no_ext = os.path.splitext(apk_filename)[0]
        patched_unsigned_apk = os.path.join(temp_root, f"{base_name_no_ext}_patched_unsigned.apk")
        repackage_apk_with_new_dex(local_apk, new_dex_map, patched_unsigned_apk)

        # -------------------------------------------------------------
        # STEP 9: ZipAlign & Sign
        # -------------------------------------------------------------
        log("Signing and aligning APK...", stage="SIGN", pct=90)
        final_apk_name = f"{base_name_no_ext}_global_patched.apk"
        final_output_path = os.path.join(output_dir, final_apk_name)

        output_apk_path = sign_and_align_apk(patched_unsigned_apk, final_output_path, progress_callback=lambda msg: log(msg, stage="SIGN"))
        output_file_size = os.path.getsize(output_apk_path) if os.path.exists(output_apk_path) else 0
        log(f"Successfully generated patched APK: {final_apk_name} ({output_file_size / (1024 * 1024):.2f} MB)", stage="COMPLETE", pct=95)

        # -------------------------------------------------------------
        # STEP 10: Generate Magisk Module & Audit Report
        # -------------------------------------------------------------
        magisk_zip_path = None
        try:
            from .magisk_generator import MagiskModuleGenerator
            magisk_filename = f"{base_name_no_ext}_Global_Magisk.zip"
            magisk_out = os.path.join(output_dir, magisk_filename)
            log("Generating flashable Magisk / KernelSU module...", stage="MAGISK", pct=96)
            magisk_zip_path = MagiskModuleGenerator.create_module(output_apk_path, magisk_out)
            log(f"Magisk module generated: {magisk_filename}", stage="MAGISK", pct=98)
        except Exception as mex:
            log(f"Magisk module generation skipped: {mex}", stage="MAGISK")

        report_path = os.path.join(output_dir, f"{base_name_no_ext}_patch_report.json")
        try:
            import json
            report_data = {
                "source": apk_source,
                "output_apk": final_apk_name,
                "file_size_bytes": output_file_size,
                "total_dex_count": total_dex_count,
                "total_patches": total_patches,
                "patches": [
                    {
                        "class": p.class_name,
                        "method": p.method_name,
                        "line": p.line_number,
                        "opcode": p.opcode,
                        "register": p.register,
                        "original_line": p.original_line,
                        "injected_line": p.injected_line
                    }
                    for p in all_patches
                ],
                "skipped_count": len(all_skipped),
                "verification": {
                    "is_valid": verification.is_valid if verification else False,
                    "verified_patches": verification.total_patches_verified if verification else 0
                }
            }
            with open(report_path, "w", encoding="utf-8") as rf:
                json.dump(report_data, rf, indent=2, ensure_ascii=False)
            log(f"Audit report saved: {os.path.basename(report_path)}", stage="COMPLETE", pct=100)
        except Exception as rex:
            report_path = None
            log(f"Could not save report: {rex}", stage="WARNING")

        return PipelineResult(
            success=True,
            input_source=apk_source,
            output_apk_path=output_apk_path,
            output_filename=final_apk_name,
            file_size_bytes=output_file_size,
            magisk_zip_path=magisk_zip_path,
            report_path=report_path,
            total_dex_count=total_dex_count,
            total_patches=total_patches,
            patches=all_patches,
            skipped=all_skipped,
            verification=verification,
            logs=logs
        )

    except Exception as e:
        err_msg = f"{str(e)}\n{traceback.format_exc()}"
        log(f"Pipeline error: {str(e)}", stage="ERROR", pct=-1)
        return PipelineResult(
            success=False,
            input_source=apk_source,
            output_apk_path=None,
            output_filename=None,
            file_size_bytes=0,
            total_dex_count=0,
            total_patches=len(all_patches),
            patches=all_patches,
            skipped=all_skipped,
            verification=verification,
            error_message=str(e),
            logs=logs
        )

    finally:
        if not keep_temp and os.path.exists(temp_root):
            try:
                shutil.rmtree(temp_root, ignore_errors=True)
            except Exception:
                pass
