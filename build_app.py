"""
Build Script for Conditioning Control Panel
============================================
Creates a distributable Windows executable using PyInstaller.

Usage:
    python build_app.py
    
Requirements:
    pip install pyinstaller
"""

import os
import shutil
import subprocess
import sys
import time

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
OUTPUT_NAME = "ConditioningControlPanel"  # No spaces for exe name

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
    "*.psd",
    "*.ai",
    "*.sketch",
    "Thumbs.db",
    ".DS_Store",
    "*.bak",
    "*.tmp",
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
            print_info(f"Removing {folder}/")
            shutil.rmtree(folder)

    # Remove spec files
    for spec in [f"{APP_NAME}.spec", f"{OUTPUT_NAME}.spec"]:
        if os.path.exists(spec):
            os.remove(spec)

    # Remove old release zips
    for old_file in os.listdir('.'):
        if old_file.endswith('_Release.zip') or old_file.endswith('_Setup.exe'):
            os.remove(old_file)
            print_info(f"Removed old {old_file}")


def run_pyinstaller():
    """Runs the PyInstaller command to freeze the Python code."""
    print_step(f"Compiling v{VERSION} with PyInstaller...")

    # Hidden imports for modules loaded dynamically
    hidden_imports = [
        # System tray and audio
        "pystray", "pystray._win32",
        "pycaw", "pycaw.pycaw",
        "comtypes", "comtypes.client",
        
        # Display
        "screeninfo",
        
        # Image processing
        "PIL", "PIL._tkinter_finder", "PIL.Image", "PIL.ImageTk",
        
        # Video/Media
        "cv2", "imageio", "imageio_ffmpeg",
        
        # UI
        "customtkinter", "darkdetect",
        
        # Selenium (browser)
        "selenium", "selenium.webdriver",
        
        # Our modules
        "engine", "gui", "utils", "config", "security",
        "browser", "ui_components", "progression_system", 
        "bubble_game", "Overlay_spiral", "main",
    ]
    
    # Exclude unnecessary modules to reduce size
    excludes = [
        "matplotlib", "numpy.testing", "scipy",
        "pandas", "notebook", "IPython",
        "pytest", "unittest", "doctest",
        "tkinter.test", "lib2to3",
    ]

    cmd = [
        "pyinstaller",
        "--noconsole",        # No console window
        "--onedir",           # Folder output (faster startup than onefile)
        "--clean",            # Clean cache
        "--noconfirm",        # Overwrite without asking
        f"--name={OUTPUT_NAME}",
        
        # Version info (Windows)
        f"--add-data=config.py;.",
        
        # Collect required packages
        "--collect-all=customtkinter",
        "--collect-all=darkdetect",
        "--collect-all=PIL",
        
        # Imageio metadata
        "--copy-metadata=imageio",
        "--copy-metadata=imageio_ffmpeg",
    ]

    # Add icon if found
    if ICON_FILE:
        cmd.append(f"--icon={ICON_FILE}")
        print_info(f"Using icon: {ICON_FILE}")
    else:
        print_info("No icon found, using default")

    # Add hidden imports
    for lib in hidden_imports:
        cmd.append(f"--hidden-import={lib}")
    
    # Add excludes
    for exc in excludes:
        cmd.append(f"--exclude-module={exc}")

    # Main script last
    cmd.append(MAIN_SCRIPT)

    print_info(f"Running PyInstaller...")
    
    try:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL if not os.getenv('VERBOSE') else None)
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] PyInstaller failed with code {e.returncode}")
        print("Try running with VERBOSE=1 for more details")
        sys.exit(1)
    except FileNotFoundError:
        print("\n[ERROR] PyInstaller not found. Install it with:")
        print("  pip install pyinstaller")
        sys.exit(1)


def copy_assets():
    """Copies the assets folder into the dist folder."""
    print_step("Copying Assets...")

    dist_folder = os.path.join("dist", OUTPUT_NAME)
    target_assets = os.path.join(dist_folder, ASSETS_DIR)

    if not os.path.exists(ASSETS_DIR):
        print_info("[WARNING] No assets folder found!")
        os.makedirs(target_assets, exist_ok=True)
        return

    if os.path.exists(target_assets):
        shutil.rmtree(target_assets)

    # Copy with filtering
    def ignore_patterns(dir, files):
        ignored = []
        for f in files:
            for pattern in EXCLUDE_PATTERNS:
                if pattern.startswith('*'):
                    if f.endswith(pattern[1:]):
                        ignored.append(f)
                elif f == pattern:
                    ignored.append(f)
        return ignored

    shutil.copytree(ASSETS_DIR, target_assets, ignore=ignore_patterns)
    
    # Count files
    file_count = sum(len(files) for _, _, files in os.walk(target_assets))
    print_info(f"Copied {file_count} asset files")


def copy_documentation():
    """Copies documentation to the dist folder."""
    print_step("Copying Documentation...")
    
    dist_folder = os.path.join("dist", OUTPUT_NAME)
    
    copied = 0
    for filename in INCLUDE_FILES:
        if os.path.exists(filename):
            shutil.copy2(filename, os.path.join(dist_folder, filename))
            copied += 1
    
    print_info(f"Copied {copied} documentation files")


def create_version_file():
    """Creates a VERSION.txt file in the dist."""
    print_step("Creating version info...")
    
    dist_folder = os.path.join("dist", OUTPUT_NAME)
    version_file = os.path.join(dist_folder, "VERSION.txt")
    
    with open(version_file, 'w') as f:
        f.write(f"{APP_NAME}\n")
        f.write(f"Version: {VERSION}\n")
        f.write(f"Built: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print_info(f"Version: {VERSION}")


def calculate_size():
    """Calculate the total size of the dist folder."""
    dist_folder = os.path.join("dist", OUTPUT_NAME)
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(dist_folder):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def zip_package():
    """Zips the final result."""
    print_step("Creating Release Package...")

    output_filename = f"{OUTPUT_NAME}_v{VERSION}"
    shutil.make_archive(output_filename, 'zip', root_dir='dist', base_dir=OUTPUT_NAME)
    
    zip_path = f"{output_filename}.zip"
    zip_size = os.path.getsize(zip_path) / (1024 * 1024)
    
    print_info(f"Created: {zip_path} ({zip_size:.1f} MB)")
    return zip_path


def main():
    """Main build process."""
    print(f"\n🎀 Building {APP_NAME} v{VERSION} 🎀\n")
    
    start_time = time.time()

    # Run build steps
    clean_previous_builds()
    run_pyinstaller()
    copy_assets()
    copy_documentation()
    create_version_file()
    
    # Calculate size before zipping
    dist_size = calculate_size() / (1024 * 1024)
    print_info(f"Distribution size: {dist_size:.1f} MB")
    
    zip_file = zip_package()

    elapsed = round(time.time() - start_time, 1)
    
    print_step(f"BUILD COMPLETE! ({elapsed}s)")
    print(f"""
📦 Output Files:
   • Folder: dist/{OUTPUT_NAME}/
   • Zip:    {zip_file}

📋 Next Steps:
   1. Test the exe: dist/{OUTPUT_NAME}/{OUTPUT_NAME}.exe
   2. If working, upload {zip_file} to GitHub Releases
   3. Optional: Build installer with Inno Setup using installer.iss

🎀 Ready for distribution! 🎀
""")


if __name__ == "__main__":
    main()

