import os
import re
from typing import List, Tuple, Optional
from .models import PatchItem, SkippedItem, DexScanResult

# Regex matching executable field read instructions for IS_INTERNATIONAL_BUILD
# Matches:
#   sget-boolean v0, Lcom/miui/gallery/util/BuildUtil;->IS_INTERNATIONAL_BUILD:Z
#   sget-boolean/jumbo p1, Lmiui/os/Build;->IS_INTERNATIONAL_BUILD:Z
#   sget v2, Lcom/example/Build;->IS_INTERNATIONAL_BUILD:Z
#   iget-boolean v0, p0, Lcom/example/Config;->IS_INTERNATIONAL_BUILD:Z
#   iget v0, p1, Lcom/example/Config;->IS_INTERNATIONAL_BUILD:Z
OPCODE_READ_REGEX = re.compile(
    r"^(\s*)(sget-boolean|sget-boolean/jumbo|sget|iget-boolean|iget)\s+([vp]\d+)(?:,\s*[vp]\d+)?,\s*(L[^;]+;->IS_INTERNATIONAL_BUILD:[^\s]+)$"
)

CLASS_DEF_REGEX = re.compile(r"^\.class\s+.*?(L[a-zA-Z0-9_\$/]+;)")
METHOD_DEF_REGEX = re.compile(r"^\.method\s+.*?\s+([a-zA-Z0-9_<>$]+\(.*?\)[^\s]+)")

def patch_smali_file(file_path: str) -> Tuple[List[str], List[PatchItem], List[SkippedItem]]:
    """
    Parses and patches a single Smali file following strict rules:
    - Only patches executable field reads inside method bodies.
    - Preserves all original code lines.
    - Injects `const/4 <reg>, 0x1` immediately beneath each valid IS_INTERNATIONAL_BUILD read.
    - Leaves field declarations, strings, annotations, and outside-method code untouched.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    modified_lines: List[str] = []
    patches: List[PatchItem] = []
    skipped: List[SkippedItem] = []

    in_method = False
    in_annotation = False
    current_class = ""
    current_method = ""

    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Track class declaration
        if stripped.startswith(".class"):
            match = CLASS_DEF_REGEX.search(stripped)
            if match:
                current_class = match.group(1)

        # Track method boundaries
        if stripped.startswith(".method"):
            in_method = True
            m_match = METHOD_DEF_REGEX.search(stripped)
            current_method = m_match.group(1) if m_match else stripped
        elif stripped.startswith(".end method"):
            in_method = False
            current_method = ""

        # Track annotation boundaries inside or outside methods
        if stripped.startswith(".annotation"):
            in_annotation = True
        elif stripped.startswith(".end annotation"):
            in_annotation = False

        # Check if line references IS_INTERNATIONAL_BUILD
        if "IS_INTERNATIONAL_BUILD" in line:
            if stripped.startswith("#"):
                skipped.append(SkippedItem(
                    file_path=file_path,
                    line_number=line_idx,
                    reason="COMMENT",
                    line_content=line.rstrip("\r\n")
                ))
                modified_lines.append(line)
                continue

            if not in_method:
                reason = "FIELD_DECLARATION" if stripped.startswith(".field") else "OUTSIDE_METHOD"
                skipped.append(SkippedItem(
                    file_path=file_path,
                    line_number=line_idx,
                    reason=reason,
                    line_content=line.rstrip("\r\n")
                ))
                modified_lines.append(line)
                continue

            if in_annotation:
                skipped.append(SkippedItem(
                    file_path=file_path,
                    line_number=line_idx,
                    reason="ANNOTATION",
                    line_content=line.rstrip("\r\n")
                ))
                modified_lines.append(line)
                continue

            # Inside method and not annotation
            if stripped.startswith("const-string"):
                skipped.append(SkippedItem(
                    file_path=file_path,
                    line_number=line_idx,
                    reason="STRING_LITERAL",
                    line_content=line.rstrip("\r\n")
                ))
                modified_lines.append(line)
                continue

            if stripped.startswith("."):
                # Smali directive (.param, .local, etc.)
                skipped.append(SkippedItem(
                    file_path=file_path,
                    line_number=line_idx,
                    reason="DIRECTIVE",
                    line_content=line.rstrip("\r\n")
                ))
                modified_lines.append(line)
                continue

            # Check if it is an executable field read
            opcode_match = OPCODE_READ_REGEX.match(line.rstrip("\r\n"))
            if opcode_match:
                indent = opcode_match.group(1)
                opcode = opcode_match.group(2)
                dest_reg = opcode_match.group(3)
                field_ref = opcode_match.group(4)

                # Determine line endings (\n or \r\n)
                line_ending = "\r\n" if line.endswith("\r\n") else "\n"
                
                # Keep original instruction intact
                modified_lines.append(line)

                # Inject const/4 <same_register>, 0x1
                injected_instruction = f"{indent}const/4 {dest_reg}, 0x1{line_ending}"
                modified_lines.append(injected_instruction)

                # Collect context lines for logging and UI diffing
                start_ctx = max(0, line_idx - 3)
                end_ctx = min(len(lines), line_idx + 2)
                context = [l.rstrip("\r\n") for l in lines[start_ctx:end_ctx]]

                patches.append(PatchItem(
                    file_path=file_path,
                    class_name=current_class or os.path.basename(file_path),
                    method_name=current_method or "unknown_method",
                    line_number=line_idx,
                    opcode=opcode,
                    register=dest_reg,
                    field_ref=field_ref,
                    original_line=line.rstrip("\r\n"),
                    injected_line=injected_instruction.rstrip("\r\n"),
                    context=context
                ))
            else:
                # Other non-read usage or put instruction
                skipped.append(SkippedItem(
                    file_path=file_path,
                    line_number=line_idx,
                    reason="NON_READ_OR_UNRECOGNIZED_OPCODE",
                    line_content=line.rstrip("\r\n")
                ))
                modified_lines.append(line)
        else:
            modified_lines.append(line)

    return modified_lines, patches, skipped

def patch_smali_directory(smali_dir: str, dex_name: str = "classes.dex") -> DexScanResult:
    """
    Recursively scans and patches all .smali files in smali_dir.
    Overwrites modified files in-place only if patches were applied.
    """
    scan_result = DexScanResult(dex_name=dex_name)

    for root, _, files in os.walk(smali_dir):
        for file in files:
            if file.endswith(".smali"):
                scan_result.total_files_scanned += 1
                file_path = os.path.join(root, file)

                # Fast check to avoid full parsing of files that don't contain the keyword
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as quick_check:
                        content = quick_check.read()
                        if "IS_INTERNATIONAL_BUILD" not in content:
                            continue
                except Exception:
                    continue

                modified_lines, patches, skipped = patch_smali_file(file_path)

                if skipped:
                    scan_result.skipped.extend(skipped)

                if patches:
                    scan_result.total_files_modified += 1
                    scan_result.patches.extend(patches)
                    
                    # Write modified smali back
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.writelines(modified_lines)

    return scan_result
