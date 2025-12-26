"""
Build Script for Conditioning Control Panel (Fixed)
===================================================
Creates a distributable Windows executable using PyInstaller.
- ENABLES error output for debugging
- Handles OS-specific separators
- Increases recursion limit for GUI libraries

Usage:
    python build_app.py
"""

import os
import shutil
import subprocess
import sys
import time
import platform

# Import version from config
try:
    from config import VERSION, APP_NAME as CONFIG_APP_NAME
    APP_NAME = CONFIG_APP_NAME
except ImportError:
    VERSION = "2.1.0"
    APP_NAME = "Conditioning Control Panel"

# --- CONFIGURATION ---
MAIN_SCRIPT = "main.py"
ASSETS_DIR = "assets"
OUTPUT_NAME = "ConditioningControlPanel"

# Try to find the icon
ICON_FILE = None
for icon_name in ["Conditioning Control Panel.ico", "icon.ico", "assets/icon.ico"]:
    if os.path.exists(icon_name):
        ICON_FILE = icon_name
        break

# Files to include in the release
INCLUDE_FILES = [
    "README.md",
    "CHANGELOG.md",
    "requirements.txt",
    "presets.json",
]

# Exclude these from assets to reduce size
EXCLUDE_PATTERNS = [
    "*.psd", "*.ai", "*.sketch", "Thumbs.db", ".DS_Store", "*.bak", "*.tmp",
]

def print_step(msg):
    print(f"\n{'=' * 60}\n[BUILD] {msg}\n{'=' * 60}")

def print_info(msg):
    print(f"  → {msg}")

def clean_previous_builds():
    """Removes old build/dist folders to ensure a fresh start."""
    print_step("Cleaning previous builds...")
    folders = ['build', 'dist', '__pycache__']
    for folder in folders:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print_info(f"Removed {folder}/")
            except OSError as e:
                print_info(f"Could not remove {folder}: {e}")

    # Remove spec files
    for spec in [f"{APP_NAME}.spec", f"{OUTPUT_NAME}.spec"]:
        if os.path.exists(spec):
            os.remove(spec)

    # Remove old release zips
    for old_file in os.listdir('.'):
        if old_file.endswith('_Release.zip') or old_file.endswith('_Setup.exe'):
            os.remove(old_file)

def check_requirements():
    """Checks if critical packages are installed before starting."""
    required = ["PyInstaller", "customtkinter", "PIL", "cv2"]
    missing = []
    import importlib.util

    # Map pip names to import names where they differ
    mapping = {"PIL": "PIL", "cv2": "cv2"}

    for pkg in required:
        import_name = mapping.get(pkg, pkg)
        if importlib.util.find_spec(import_name) is None:
            # Special check for cv2 which is 'opencv-python' in pip
            if pkg == "cv2":
                try:
                    import cv2
                except ImportError:
                    missing.append(pkg)
            else:
                missing.append(pkg)

    if missing:
        print("\n[CRITICAL ERROR] Missing required packages for build:")
        print(f"  {', '.join(missing)}")
        print("Please run: pip install " + " ".join(missing))
        sys.exit(1)

def run_pyinstaller():
    """Runs the PyInstaller command to freeze the Python code."""
    print_step(f"Compiling v{VERSION} with PyInstaller...")

    # Detect OS separator (Windows uses ';', Mac/Linux uses ':')
    sep = ';' if os.name == 'nt' else ':'

    # Hidden imports for modules loaded dynamically
    hidden_imports = [
        "pystray", "pystray._win32", "pycaw", "pycaw.pycaw",
        "comtypes", "comtypes.client", "screeninfo",
        "PIL", "PIL._tkinter_finder", "PIL.Image", "PIL.ImageTk",
        "cv2", "numpy", "numpy.core._methods", "numpy.lib.format",  # cv2 requires numpy
        "imageio", "imageio_ffmpeg",
        "customtkinter", "darkdetect", "selenium", "selenium.webdriver",
        # Local modules
        "engine", "gui", "utils", "config", "security",
        "browser", "ui_components", "progression_system",
        "bubble_game", "Overlay_spiral", "main",
    ]

    # NOTE: Do NOT exclude numpy - opencv-python requires it!
    excludes = [
        "matplotlib", "scipy", "pandas", "notebook",
        "IPython", "pytest", "unittest", "doctest", "tkinter.test"
    ]

    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onedir",
        "--clean",
        "--noconfirm",
        f"--name={OUTPUT_NAME}",
        # FIX: Use dynamic separator for cross-platform compatibility
        f"--add-data=config.py{sep}.",
        "--collect-all=customtkinter",
        "--collect-all=darkdetect",
        "--collect-all=PIL",
        "--collect-all=cv2",  # FIX: Collect all cv2 binaries
        "--copy-metadata=imageio",
        "--copy-metadata=imageio_ffmpeg",
        # FIX: Increase recursion limit for GUI libraries
        "--additional-hooks-dir=.",
    ]

    if ICON_FILE:
        cmd.append(f"--icon={ICON_FILE}")

    for lib in hidden_imports:
        cmd.append(f"--hidden-import={lib}")

    for exc in excludes:
        cmd.append(f"--exclude-module={exc}")

    cmd.append(MAIN_SCRIPT)

    print_info("Executing PyInstaller (Output Enabled)...")
    print("-" * 60)

    try:
        # FIX: Removed stdout=subprocess.DEVNULL to show errors
        subprocess.check_call(cmd)
        print("-" * 60)
    except subprocess.CalledProcessError as e:
        print("-" * 60)
        print(f"\n[ERROR] PyInstaller failed with return code {e.returncode}.")
        print("Read the error message above to fix the issue.")
        sys.exit(1)

def copy_assets():
    """Copies the assets folder into the dist folder."""
    print_step("Copying Assets...")
    dist_folder = os.path.join("dist", OUTPUT_NAME)
    target_assets = os.path.join(dist_folder, ASSETS_DIR)

    if not os.path.exists(ASSETS_DIR):
        print_info("[WARNING] No assets folder found in source!")
        os.makedirs(target_assets, exist_ok=True)
        return

    if os.path.exists(target_assets):
        shutil.rmtree(target_assets)

    def ignore_patterns(dir, files):
        ignored = []
        for f in files:
            for pattern in EXCLUDE_PATTERNS:
                if pattern.startswith('*') and f.endswith(pattern[1:]):
                    ignored.append(f)
                elif f == pattern:
                    ignored.append(f)
        return ignored

    shutil.copytree(ASSETS_DIR, target_assets, ignore=ignore_patterns)
    print_info("Assets copied successfully.")

def copy_documentation():
    """Copies documentation to the dist folder."""
    print_step("Copying Documentation...")
    dist_folder = os.path.join("dist", OUTPUT_NAME)
    for filename in INCLUDE_FILES:
        if os.path.exists(filename):
            shutil.copy2(filename, os.path.join(dist_folder, filename))

def create_version_file():
    """Creates a VERSION.txt file in the dist."""
    dist_folder = os.path.join("dist", OUTPUT_NAME)
    if not os.path.exists(dist_folder): return

    with open(os.path.join(dist_folder, "VERSION.txt"), 'w') as f:
        f.write(f"{APP_NAME}\nVersion: {VERSION}\nBuilt: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

def zip_package():
    """Zips the final result."""
    print_step("Creating Release Package...")
    output_filename = f"{OUTPUT_NAME}_v{VERSION}"
    shutil.make_archive(output_filename, 'zip', root_dir='dist', base_dir=OUTPUT_NAME)
    print_info(f"Created: {output_filename}.zip")
    return f"{output_filename}.zip"

def main():
    print(f"\n🎀 Building {APP_NAME} v{VERSION} 🎀\n")
    start_time = time.time()

    check_requirements()
    clean_previous_builds()
    run_pyinstaller()
    copy_assets()
    copy_documentation()
    create_version_file()

    zip_file = zip_package()

    print_step(f"BUILD COMPLETE ({round(time.time() - start_time, 1)}s)")
    print(f"Output: dist/{OUTPUT_NAME}/{OUTPUT_NAME}.exe")
    print(f"Zip:    {zip_file}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Build cancelled by user.")
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")