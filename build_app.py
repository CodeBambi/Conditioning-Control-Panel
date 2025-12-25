import os
import shutil
import subprocess
import sys
import time

# --- CONFIGURATION ---
APP_NAME = "Conditioning Control Panel"
# [IMPORTANT] Pointing to your new entry point
MAIN_SCRIPT = "main.py"
ASSETS_DIR = "assets"
# Try to find the icon (checking multiple common extensions)
ICON_FILE = "Conditioning Control Panel.ico"
if not os.path.exists(ICON_FILE):
    ICON_FILE = "icon.ico"

# Files to include in the release
INCLUDE_FILES = [
    "README.md",
    "CHANGELOG.md",
    "requirements.txt",
]


def print_step(msg):
    print(f"\n{'=' * 60}\n[BUILD] {msg}\n{'=' * 60}")


def clean_previous_builds():
    """Removes old build/dist folders to ensure a fresh start."""
    print_step("Cleaning previous builds...")
    folders = ['build', 'dist', '__pycache__']
    for folder in folders:
        if os.path.exists(folder):
            print(f" - Removing {folder}...")
            shutil.rmtree(folder)

    # Remove spec file if it exists
    spec_file = f"{APP_NAME}.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)
    
    # Remove old release zip if exists
    old_zip = f"{APP_NAME}_Release.zip"
    if os.path.exists(old_zip):
        os.remove(old_zip)
        print(f" - Removed old {old_zip}")


def run_pyinstaller():
    """Runs the PyInstaller command to freeze the Python code."""
    print_step("Compiling with PyInstaller...")

    # Define libraries that might be missed due to try/except blocks
    hidden_imports = [
        "pystray",
        "pycaw",
        "comtypes",
        "screeninfo",
        "PIL",
        "cv2",
        "imageio",
        "engine",  # Your local modules
        "gui",
        "utils",
        "config",
        "browser",
        "ui_components",
        "progression_system",
        "bubble_game",
        "Overlay_spiral",
    ]

    cmd = [
        "pyinstaller",
        "--noconsole",  # Don't show the black command window
        "--onedir",  # Create a folder (easier for debugging assets)
        "--clean",
        "--name", APP_NAME,

        # Collect CustomTkinter assets (themes, etc.)
        "--collect-all", "customtkinter",

        # Fix for imageio dependency issues
        "--copy-metadata=imageio",
        "--copy-metadata=imageio_ffmpeg",

        # Main Entry Point
        MAIN_SCRIPT
    ]

    # Append Hidden Imports
    for lib in hidden_imports:
        cmd.append(f"--hidden-import={lib}")

    # Add icon if it exists
    if os.path.exists(ICON_FILE):
        cmd.insert(3, f"--icon={ICON_FILE}")
        print(f" - Using icon: {ICON_FILE}")
    else:
        print(" - No icon.ico found, using default icon.")

    print(f" - Command: {' '.join(cmd)}")

    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        print("\n[ERROR] PyInstaller failed.")
        print("Make sure it is installed: pip install pyinstaller")
        sys.exit(1)


def copy_assets():
    """Copies the assets folder into the new dist folder."""
    print_step("Copying Assets...")

    # The folder PyInstaller created
    dist_folder = os.path.join("dist", APP_NAME)

    # Where the assets should go inside that folder
    target_assets = os.path.join(dist_folder, ASSETS_DIR)

    if os.path.exists(ASSETS_DIR):
        if os.path.exists(target_assets):
            shutil.rmtree(target_assets)
        shutil.copytree(ASSETS_DIR, target_assets)
        print(f" - Success! Copied '{ASSETS_DIR}' to '{target_assets}'")
    else:
        print(f" - [WARNING] Could not find source '{ASSETS_DIR}' folder!")
        print("   The app might crash if it looks for images/sounds that aren't there.")


def copy_documentation():
    """Copies README, CHANGELOG, and other docs to the dist folder."""
    print_step("Copying Documentation...")
    
    dist_folder = os.path.join("dist", APP_NAME)
    
    for filename in INCLUDE_FILES:
        if os.path.exists(filename):
            target_path = os.path.join(dist_folder, filename)
            shutil.copy2(filename, target_path)
            print(f" - Copied {filename}")
        else:
            print(f" - [WARNING] {filename} not found, skipping...")


def zip_package():
    """Zips the final result so it's ready for upload."""
    print_step("Zipping Release...")

    output_filename = f"{APP_NAME}_Release"

    # Create the zip file from the 'dist' folder content
    shutil.make_archive(output_filename, 'zip', root_dir='dist', base_dir=APP_NAME)

    print(f" - Created: {output_filename}.zip")
    return f"{output_filename}.zip"


if __name__ == "__main__":
    # 1. Check for PyInstaller
    if shutil.which("pyinstaller") is None:
        print("[ERROR] PyInstaller not found. Please run: pip install pyinstaller")
        sys.exit(1)

    start_time = time.time()

    # 2. Run Steps
    clean_previous_builds()
    run_pyinstaller()
    copy_assets()
    copy_documentation()
    zip_file = zip_package()

    elapsed = round(time.time() - start_time, 2)
    print_step(f"BUILD COMPLETE in {elapsed} seconds!")
    print(f"Your ready-to-upload file is here:\n --> {os.path.abspath(zip_file)}")

    print("\n🎀 Ready for distribution! 🎀")
