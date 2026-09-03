"""
HyperOS-GlobalConvert - Magisk / KernelSU / APatch Module Generator
Creates a systemless flashable zip for installing the patched APK.
"""

import os
import zipfile
import re

MODULE_PROP_TEMPLATE = """id=hyperos_global_{app_slug}
name=HyperOS Global Convert - {app_title}
version=v1.0.0
versionCode=100
author=mertcqnkld
description=Patched {app_title} system app with IS_INTERNATIONAL_BUILD forced to true (0x1) for global HyperOS features.
"""

CUSTOMIZE_SH_TEMPLATE = """SKIPUNZIP=1

ui_print "- Extracting module files..."
unzip -o "$ZIPFILE" 'module.prop' -d "$MODPATH" >&2

APP_NAME="{app_name}"
APP_FILENAME="{app_filename}"

# Auto-detect target path on device
TARGET_DIR=""
if [ -d "/system/priv-app/$APP_NAME" ]; then
    TARGET_DIR="$MODPATH/system/priv-app/$APP_NAME"
elif [ -d "/system_ext/priv-app/$APP_NAME" ]; then
    TARGET_DIR="$MODPATH/system_ext/priv-app/$APP_NAME"
elif [ -d "/product/priv-app/$APP_NAME" ]; then
    TARGET_DIR="$MODPATH/product/priv-app/$APP_NAME"
elif [ -d "/system/app/$APP_NAME" ]; then
    TARGET_DIR="$MODPATH/system/app/$APP_NAME"
elif [ -d "/product/app/$APP_NAME" ]; then
    TARGET_DIR="$MODPATH/product/app/$APP_NAME"
else
    # Default fallback to system/priv-app
    TARGET_DIR="$MODPATH/system/priv-app/$APP_NAME"
fi

ui_print "- Target installation path: $TARGET_DIR"
mkdir -p "$TARGET_DIR"

ui_print "- Copying patched APK..."
unzip -o "$ZIPFILE" "$APP_FILENAME" -d "$TARGET_DIR" >&2
if [ "$APP_FILENAME" != "$APP_NAME.apk" ]; then
    mv -f "$TARGET_DIR/$APP_FILENAME" "$TARGET_DIR/$APP_NAME.apk" 2>/dev/null
fi

set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$TARGET_DIR/$APP_NAME.apk" 0 0 0644

ui_print "- GlobalConvert patch installed systemlessly!"
ui_print "- Please reboot your device to apply changes."
"""

class MagiskModuleGenerator:
    @staticmethod
    def create_module(patched_apk_path: str, output_zip_path: str) -> str:
        if not os.path.exists(patched_apk_path):
            raise FileNotFoundError(f"Patched APK not found: {patched_apk_path}")

        os.makedirs(os.path.dirname(os.path.abspath(output_zip_path)), exist_ok=True)
        apk_filename = os.path.basename(patched_apk_path)
        base_name = os.path.splitext(apk_filename)[0]
        # Clean clean app name: remove suffixes like _global_patched, _patched, etc.
        clean_name = re.sub(r'(_global_patched|_patched|_aligned|-debugSigned)$', '', base_name, flags=re.IGNORECASE)
        app_slug = re.sub(r'[^a-zA-Z0-9_]', '_', clean_name).lower()
        app_title = clean_name.replace('_', ' ').replace('-', ' ').title()

        module_prop = MODULE_PROP_TEMPLATE.format(
            app_slug=app_slug,
            app_title=app_title
        )

        customize_sh = CUSTOMIZE_SH_TEMPLATE.format(
            app_name=clean_name,
            app_filename=apk_filename
        )

        with zipfile.ZipFile(output_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("module.prop", module_prop)
            zf.writestr("customize.sh", customize_sh)
            zf.write(patched_apk_path, apk_filename)
            zf.write(patched_apk_path, f"system/priv-app/{clean_name}/{clean_name}.apk")

        return output_zip_path
