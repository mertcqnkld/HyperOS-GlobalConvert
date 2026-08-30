import os
import tempfile
import unittest
from core.patcher import patch_smali_file, patch_smali_directory

SAMPLE_SMALI = """
.class public Lcom/miui/gallery/util/BuildUtil;
.super Ljava/lang/Object;
.source "BuildUtil.java"

# Field declaration - MUST NOT BE TOUCHED
.field public static final IS_INTERNATIONAL_BUILD:Z = false
.field public static ANOTHER_FIELD:Ljava/lang/String; = "IS_INTERNATIONAL_BUILD"

# Direct method
.method public static isInternational()Z
    .registers 2

    .prologue
    .line 45
    sget-boolean v0, Lcom/miui/gallery/util/BuildUtil;->IS_INTERNATIONAL_BUILD:Z

    return v0
.end method

# Method with parameter register
.method public static checkRegion(Landroid/content/Context;)V
    .registers 3
    .param p0, "context"    # Landroid/content/Context;

    .prologue
    .line 52
    sget-boolean p1, Lmiui/os/Build;->IS_INTERNATIONAL_BUILD:Z

    if-eqz p1, :cond_0

    const-string v0, "International device detected"
    invoke-static {v0}, Lcom/example/Log;->d(Ljava/lang/String;)V

    :cond_0
    return-void
.end method

# Method with iget-boolean
.method public checkInstance()Z
    .registers 3

    .prologue
    .line 70
    iget-boolean v1, p0, Lcom/miui/gallery/util/BuildUtil;->IS_INTERNATIONAL_BUILD:Z

    return v1
.end method

# Method with string literal - MUST NOT BE TOUCHED
.method public static getBuildTag()Ljava/lang/String;
    .registers 1

    .prologue
    const-string v0, "IS_INTERNATIONAL_BUILD"

    return-object v0
.end method

# Comment only - MUST NOT BE TOUCHED
# sget-boolean v0, Lcom/miui/gallery/util/BuildUtil;->IS_INTERNATIONAL_BUILD:Z
"""

class TestSmaliPatcher(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sample_file = os.path.join(self.temp_dir, "BuildUtil.smali")
        with open(self.sample_file, "w", encoding="utf-8") as f:
            f.write(SAMPLE_SMALI)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_patch_smali_file_strict_rules(self):
        modified_lines, patches, skipped = patch_smali_file(self.sample_file)

        # We expect exactly 3 executable patches:
        # 1. sget-boolean v0, ... -> const/4 v0, 0x1
        # 2. sget-boolean p1, ... -> const/4 p1, 0x1
        # 3. iget-boolean v1, p0, ... -> const/4 v1, 0x1
        self.assertEqual(len(patches), 3, f"Expected 3 patches, got {len(patches)}")

        # Check patch 1
        p1 = patches[0]
        self.assertEqual(p1.register, "v0")
        self.assertEqual(p1.opcode, "sget-boolean")
        self.assertEqual(p1.injected_line.strip(), "const/4 v0, 0x1")

        # Check patch 2
        p2 = patches[1]
        self.assertEqual(p2.register, "p1")
        self.assertEqual(p2.opcode, "sget-boolean")
        self.assertEqual(p2.injected_line.strip(), "const/4 p1, 0x1")

        # Check patch 3
        p3 = patches[2]
        self.assertEqual(p3.register, "v1")
        self.assertEqual(p3.opcode, "iget-boolean")
        self.assertEqual(p3.injected_line.strip(), "const/4 v1, 0x1")

        # Check skipped items:
        # 1. Field declaration: .field public static final IS_INTERNATIONAL_BUILD:Z = false
        # 2. String in field: .field public static ANOTHER_FIELD ...
        # 3. String literal in getBuildTag: const-string v0, "IS_INTERNATIONAL_BUILD"
        # 4. Comment: # sget-boolean ...
        reasons = [s.reason for s in skipped]
        self.assertIn("FIELD_DECLARATION", reasons)
        self.assertIn("STRING_LITERAL", reasons)
        self.assertIn("COMMENT", reasons)

        # Verify field declarations in modified text remain untouched
        modified_text = "".join(modified_lines)
        self.assertIn(".field public static final IS_INTERNATIONAL_BUILD:Z = false", modified_text)
        self.assertIn('const-string v0, "IS_INTERNATIONAL_BUILD"', modified_text)

    def test_patch_smali_directory(self):
        res = patch_smali_directory(self.temp_dir, dex_name="classes.dex")
        self.assertEqual(res.total_files_scanned, 1)
        self.assertEqual(res.total_files_modified, 1)
        self.assertEqual(len(res.patches), 3)

if __name__ == "__main__":
    unittest.main()
