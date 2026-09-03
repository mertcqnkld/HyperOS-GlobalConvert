import os
import zipfile
import tempfile
import unittest
from core.dex_extractor import extract_dex_files, repackage_apk_with_new_dex, get_dex_sort_key

class TestDexExtractorAndRepackager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_apk_path = os.path.join(self.temp_dir, "sample.apk")
        
        # Create a mock APK containing classes.dex, classes2.dex, and AndroidManifest.xml
        with zipfile.ZipFile(self.mock_apk_path, "w") as zf:
            zf.writestr("AndroidManifest.xml", b"<mock-binary-manifest>")
            zf.writestr("resources.arsc", b"<mock-arsc>")
            zf.writestr("res/drawable/icon.png", b"<png-data>")
            zf.writestr("classes.dex", b"DEX_CLASSES_1_MOCK")
            zf.writestr("classes2.dex", b"DEX_CLASSES_2_MOCK")
            zf.writestr("META-INF/CERT.SF", b"OLD_SIGNATURE")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dex_sorting_order(self):
        files = ["classes10.dex", "classes2.dex", "classes.dex", "classes3.dex"]
        files.sort(key=get_dex_sort_key)
        self.assertEqual(files, ["classes.dex", "classes2.dex", "classes3.dex", "classes10.dex"])

    def test_extract_dex_files(self):
        extract_dir = os.path.join(self.temp_dir, "extracted")
        extracted = extract_dex_files(self.mock_apk_path, extract_dir)

        self.assertEqual(len(extracted), 2)
        self.assertEqual([os.path.basename(f) for f in extracted], ["classes.dex", "classes2.dex"])

    def test_repackage_apk_lossless(self):
        new_dex1 = os.path.join(self.temp_dir, "new_classes.dex")
        new_dex2 = os.path.join(self.temp_dir, "new_classes2.dex")

        with open(new_dex1, "wb") as f:
            f.write(b"NEW_PATCHED_DEX_1")
        with open(new_dex2, "wb") as f:
            f.write(b"NEW_PATCHED_DEX_2")

        out_apk = os.path.join(self.temp_dir, "repackaged.apk")
        repackage_apk_with_new_dex(
            self.mock_apk_path,
            {"classes.dex": new_dex1, "classes2.dex": new_dex2},
            out_apk
        )

        self.assertTrue(os.path.exists(out_apk))

        # Verify APK contents
        with zipfile.ZipFile(out_apk, "r") as zf:
            namelist = zf.namelist()
            self.assertIn("AndroidManifest.xml", namelist)
            self.assertIn("resources.arsc", namelist)
            self.assertIn("res/drawable/icon.png", namelist)
            self.assertNotIn("META-INF/CERT.SF", namelist)  # Old signature stripped for re-signing
            
            # Verify DEX replacement
            self.assertEqual(zf.read("classes.dex"), b"NEW_PATCHED_DEX_1")
            self.assertEqual(zf.read("classes2.dex"), b"NEW_PATCHED_DEX_2")
            self.assertEqual(zf.read("AndroidManifest.xml"), b"<mock-binary-manifest>")

    def test_magisk_module_generation(self):
        from core.magisk_generator import MagiskModuleGenerator
        fake_apk = os.path.join(self.temp_dir, "MiuiGallery_global_patched.apk")
        with open(fake_apk, "wb") as f:
            f.write(b"FAKE_APK_CONTENT")

        out_zip = os.path.join(self.temp_dir, "MiuiGallery_Magisk.zip")
        res_zip = MagiskModuleGenerator.create_module(fake_apk, out_zip)
        self.assertTrue(os.path.exists(res_zip))

        with zipfile.ZipFile(res_zip, "r") as zf:
            namelist = zf.namelist()
            self.assertIn("module.prop", namelist)
            self.assertIn("customize.sh", namelist)
            self.assertIn("MiuiGallery_global_patched.apk", namelist)
            prop_content = zf.read("module.prop").decode("utf-8")
            self.assertIn("id=hyperos_global_miuigallery", prop_content)

if __name__ == "__main__":
    unittest.main()
