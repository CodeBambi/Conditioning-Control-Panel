#!/usr/bin/env python3
"""
Conditioning Control Panel - Main Entry Point
==============================================

This is the secure entry point for the application.
It initializes logging, validates the environment, and starts the GUI.

Usage:
    python main.py
"""

import sys
import os
import traceback

# Ensure we can import local modules
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    APP_DIR = os.path.dirname(sys.executable)
else:
    # Running as script
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, APP_DIR)
os.chdir(APP_DIR)


def check_dependencies() -> list:
    """
    Check if all required dependencies are installed.
    
    Returns:
        List of missing module names
    """
    required = [
        ('customtkinter', 'customtkinter'),
        ('PIL', 'Pillow'),
        ('pygame', 'pygame'),
        ('cv2', 'opencv-python'),
    ]
    
    optional = [
        ('pystray', 'pystray'),
        ('pycaw', 'pycaw'),
        ('screeninfo', 'screeninfo'),
        ('selenium', 'selenium'),
    ]
    
    missing = []
    
    for module_name, pip_name in required:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(pip_name)
    
    # Just warn about optional dependencies
    for module_name, pip_name in optional:
        try:
            __import__(module_name)
        except ImportError:
            print(f"Optional: {pip_name} not installed (some features may be unavailable)")
    
    return missing


def show_error_dialog(title: str, message: str):
    """Show an error dialog using tkinter (fallback if customtkinter fails)."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        # Last resort: print to console
        print(f"ERROR: {title}")
        print(message)


def verify_assets_folder():
    """Verify assets folder exists and create if needed."""
    assets_dir = os.path.join(APP_DIR, "assets")
    subdirs = ["images", "sounds", "startle_videos", "sub_audio", "backgrounds"]
    
    if not os.path.exists(assets_dir):
        try:
            os.makedirs(assets_dir)
            print(f"Created assets folder: {assets_dir}")
        except OSError as e:
            print(f"Warning: Could not create assets folder: {e}")
            return False
    
    for subdir in subdirs:
        subdir_path = os.path.join(assets_dir, subdir)
        if not os.path.exists(subdir_path):
            try:
                os.makedirs(subdir_path)
            except OSError:
                pass  # Non-critical
    
    return True


def main():
    """Main entry point with proper error handling."""
    
    # Step 1: Check dependencies
    missing = check_dependencies()
    if missing:
        msg = f"Missing required packages:\n{', '.join(missing)}\n\n"
        msg += "Please run:\npip install " + " ".join(missing)
        show_error_dialog("Missing Dependencies", msg)
        sys.exit(1)
    
    # Step 2: Initialize logging
    try:
        from security import setup_logging, logger
        logger = setup_logging()
        logger.info("Application starting...")
    except ImportError:
        # Fallback if security module not available
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("ConditioningPanel")
        logger.warning("Security module not found, using basic logging")
    except Exception as e:
        print(f"Warning: Could not initialize logging: {e}")
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("ConditioningPanel")
    
    # Step 3: Verify assets folder
    verify_assets_folder()
    
    # Step 4: Check for single instance
    try:
        from utils import SingleInstanceChecker
        instance_checker = SingleInstanceChecker("ConditioningControlPanel_v2")
        if not instance_checker.is_single_instance():
            logger.warning("Another instance is already running")
            show_error_dialog(
                "Already Running",
                "Another instance of Conditioning Control Panel is already running.\n\n"
                "Check your system tray for the existing instance."
            )
            sys.exit(0)
    except ImportError:
        logger.warning("SingleInstanceChecker not available")
    except Exception as e:
        logger.warning(f"Could not check for single instance: {e}")
    
    # Step 5: Initialize and run GUI
    try:
        import customtkinter as ctk
        from gui import ControlPanel
        
        logger.info("Initializing GUI...")
        
        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main window
        root = ctk.CTk()
        
        # Initialize application
        app = ControlPanel(root)
        
        logger.info("Starting main loop...")
        root.mainloop()
        
        logger.info("Application closed normally")
        
    except ImportError as e:
        error_msg = f"Failed to import required module: {e}\n\n"
        error_msg += "Please ensure all dependencies are installed:\n"
        error_msg += "pip install -r requirements.txt"
        logger.error(error_msg)
        show_error_dialog("Import Error", error_msg)
        sys.exit(1)
        
    except Exception as e:
        error_msg = f"Unexpected error during startup:\n\n{e}\n\n"
        error_msg += "Check logs/app.log for details."
        logger.exception("Unexpected error during startup")
        show_error_dialog("Startup Error", error_msg)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        # Absolute last resort error handling
        print(f"\nFATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
