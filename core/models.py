from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class PatchItem:
    """Represents a single patched instruction in a Smali file."""
    file_path: str
    class_name: str
    method_name: str
    line_number: int
    opcode: str
    register: str
    field_ref: str
    original_line: str
    injected_line: str
    context: List[str] = field(default_factory=list)

@dataclass
class SkippedItem:
    """Represents an IS_INTERNATIONAL_BUILD occurrence that was deliberately ignored."""
    file_path: str
    line_number: int
    reason: str  # e.g., 'FIELD_DECLARATION', 'OUTSIDE_METHOD', 'STRING_LITERAL', 'COMMENT', 'UNKNOWN'
    line_content: str

@dataclass
class DexScanResult:
    """Results of scanning and patching a single DEX/Smali folder."""
    dex_name: str
    total_files_scanned: int = 0
    total_files_modified: int = 0
    patches: List[PatchItem] = field(default_factory=list)
    skipped: List[SkippedItem] = field(default_factory=list)

@dataclass
class VerificationResult:
    """Outcome of the strict before/after diff audit."""
    is_valid: bool
    total_patches_verified: int = 0
    errors: List[str] = field(default_factory=list)
    diff_summary: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class PipelineResult:
    """Final outcome of the full APK patching pipeline."""
    success: bool
    input_source: str
    output_apk_path: Optional[str] = None
    output_filename: Optional[str] = None
    file_size_bytes: int = 0
    total_dex_count: int = 0
    total_patches: int = 0
    patches: List[PatchItem] = field(default_factory=list)
    skipped: List[SkippedItem] = field(default_factory=list)
    verification: Optional[VerificationResult] = None
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)
