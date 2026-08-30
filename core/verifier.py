import os
import re
import difflib
from typing import List, Dict, Any
from .models import VerificationResult, PatchItem

INJECTED_LINE_REGEX = re.compile(r"^\s*const/4\s+([vp]\d+),\s*0x1\s*$")

def verify_file_diff(original_file: str, patched_file: str, expected_patches: List[PatchItem]) -> List[str]:
    """
    Performs a strict line-by-line audit of original vs patched smali file.
    Returns a list of error strings if any unauthorized change is detected.
    """
    errors: List[str] = []

    with open(original_file, "r", encoding="utf-8", errors="replace") as f_orig:
        orig_lines = [l.rstrip("\r\n") for l in f_orig.readlines()]

    with open(patched_file, "r", encoding="utf-8", errors="replace") as f_patch:
        patch_lines = [l.rstrip("\r\n") for l in f_patch.readlines()]

    matcher = difflib.SequenceMatcher(None, orig_lines, patch_lines)
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        elif tag == "delete":
            errors.append(f"Illegal line deletion in {os.path.basename(original_file)} around line {i1+1}: {orig_lines[i1:i2]}")
        elif tag == "replace":
            errors.append(f"Illegal line replacement in {os.path.basename(original_file)} around line {i1+1}. Expected only injection, but found replacement: {orig_lines[i1:i2]} -> {patch_lines[j1:j2]}")
        elif tag == "insert":
            # For every inserted line, it must be an authorized const/4 <reg>, 0x1
            inserted_lines = patch_lines[j1:j2]
            for idx, ins_line in enumerate(inserted_lines):
                match = INJECTED_LINE_REGEX.match(ins_line)
                if not match:
                    errors.append(f"Unauthorized inserted line in {os.path.basename(original_file)}: '{ins_line}'")
                    continue
                
                injected_reg = match.group(1)
                # The line before insertion must have been an IS_INTERNATIONAL_BUILD read instruction
                prev_orig_line = orig_lines[i1 - 1] if (i1 - 1) >= 0 else ""
                if "IS_INTERNATIONAL_BUILD" not in prev_orig_line:
                    errors.append(f"Inserted const/4 {injected_reg}, 0x1 in {os.path.basename(original_file)} without preceding IS_INTERNATIONAL_BUILD read: '{prev_orig_line}'")
                
                # Check that the register matches
                if not re.search(rf"\b{injected_reg}\b", prev_orig_line):
                    errors.append(f"Register mismatch in {os.path.basename(original_file)}: injected '{injected_reg}' but preceding line was '{prev_orig_line}'")

    return errors

def verify_all_dex_diffs(
    orig_smali_dirs: Dict[str, str],  # {"classes.dex": "/path/to/orig_smali", ...}
    patched_smali_dirs: Dict[str, str],
    all_patches: List[PatchItem]
) -> VerificationResult:
    """
    Performs full pre/post verification across all DEX smali directories.
    """
    errors: List[str] = []
    diff_summaries: List[Dict[str, Any]] = []
    verified_patch_count = 0

    patches_by_file: Dict[str, List[PatchItem]] = {}
    for p in all_patches:
        patches_by_file.setdefault(os.path.normpath(p.file_path), []).append(p)

    for dex_name, orig_dir in orig_smali_dirs.items():
        patched_dir = patched_smali_dirs.get(dex_name)
        if not patched_dir or not os.path.exists(patched_dir):
            errors.append(f"Patched directory for {dex_name} does not exist.")
            continue

        for root, _, files in os.walk(orig_dir):
            for file in files:
                if file.endswith(".smali"):
                    orig_file = os.path.join(root, file)
                    rel_path = os.path.relpath(orig_file, orig_dir)
                    patched_file = os.path.join(patched_dir, rel_path)

                    if not os.path.exists(patched_file):
                        errors.append(f"File missing from patched directory: {rel_path}")
                        continue

                    norm_patched_file = os.path.normpath(patched_file)
                    expected_file_patches = patches_by_file.get(norm_patched_file, [])

                    file_errors = verify_file_diff(orig_file, patched_file, expected_file_patches)
                    if file_errors:
                        errors.extend(file_errors)
                    else:
                        verified_patch_count += len(expected_file_patches)
                        if expected_file_patches:
                            diff_summaries.append({
                                "dex": dex_name,
                                "file": rel_path,
                                "patch_count": len(expected_file_patches),
                                "patches": [
                                    {
                                        "line": p.line_number,
                                        "class": p.class_name,
                                        "method": p.method_name,
                                        "opcode": p.opcode,
                                        "reg": p.register,
                                        "original": p.original_line,
                                        "injected": p.injected_line
                                    }
                                    for p in expected_file_patches
                                ]
                            })

    is_valid = (len(errors) == 0) and (verified_patch_count == len(all_patches))

    return VerificationResult(
        is_valid=is_valid,
        total_patches_verified=verified_patch_count,
        errors=errors,
        diff_summary=diff_summaries
    )
