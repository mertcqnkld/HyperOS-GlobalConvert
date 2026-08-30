import os
import shutil
import tempfile
import unittest
from core.patcher import patch_smali_directory
from core.verifier import verify_all_dex_diffs, verify_file_diff

VALID_SMALI = """
.class public Lcom/example/Utils;
.super Ljava/lang/Object;

.method public static check()Z
    .registers 2
    .prologue
    sget-boolean v0, Lcom/example/Utils;->IS_INTERNATIONAL_BUILD:Z
    return v0
.end method
"""

class TestDiffVerifier(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_dir = os.path.join(self.temp_dir, "orig")
        self.work_dir = os.path.join(self.temp_dir, "work")

        os.makedirs(self.orig_dir)
        with open(os.path.join(self.orig_dir, "Utils.smali"), "w", encoding="utf-8") as f:
            f.write(VALID_SMALI)

        shutil.copytree(self.orig_dir, self.work_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_patch_passes_verification(self):
        scan_res = patch_smali_directory(self.work_dir, dex_name="classes.dex")
        self.assertEqual(len(scan_res.patches), 1)

        v_res = verify_all_dex_diffs(
            {"classes.dex": self.orig_dir},
            {"classes.dex": self.work_dir},
            scan_res.patches
        )

        self.assertTrue(v_res.is_valid)
        self.assertEqual(v_res.total_patches_verified, 1)
        self.assertEqual(len(v_res.errors), 0)

    def test_illegal_mutation_fails_verification(self):
        scan_res = patch_smali_directory(self.work_dir, dex_name="classes.dex")
        
        # Tamper with the patched file by inserting an unauthorized line
        patched_file = os.path.join(self.work_dir, "Utils.smali")
        with open(patched_file, "a", encoding="utf-8") as f:
            f.write("\n    const-string v0, 'illegal_injected_code'\n")

        v_res = verify_all_dex_diffs(
            {"classes.dex": self.orig_dir},
            {"classes.dex": self.work_dir},
            scan_res.patches
        )

        self.assertFalse(v_res.is_valid)
        self.assertGreater(len(v_res.errors), 0)
        self.assertTrue(any("Unauthorized inserted line" in err for err in v_res.errors))

    def test_register_mismatch_fails_verification(self):
        # Manually create a file where sget loads into v0 but const/4 injects into v1
        patched_file = os.path.join(self.work_dir, "Utils.smali")
        with open(patched_file, "w", encoding="utf-8") as f:
            f.write("""
.class public Lcom/example/Utils;
.super Ljava/lang/Object;

.method public static check()Z
    .registers 2
    .prologue
    sget-boolean v0, Lcom/example/Utils;->IS_INTERNATIONAL_BUILD:Z
    const/4 v1, 0x1
    return v0
.end method
""")
        orig_file = os.path.join(self.orig_dir, "Utils.smali")
        errors = verify_file_diff(orig_file, patched_file, [])
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Register mismatch" in err for err in errors))

if __name__ == "__main__":
    unittest.main()
