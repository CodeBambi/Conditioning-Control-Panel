import sys
import customtkinter as ctk
from utils import SingleInstanceChecker
from gui import ControlPanel

if __name__ == "__main__":
    # Define the application title used for window matching
    app_title = "Conditioning Control Panel"

    # --- 1. Single Instance Check ---
    # Prevents multiple copies of the program from running simultaneously.
    instance_checker = SingleInstanceChecker("ConditioningApp_Unique_ID_V1.5_BROWSER")
    instance_checker.check()

    if instance_checker.is_already_running():
        # If already running, find the existing window, bring it to front, and close this new instance.
        found = instance_checker.focus_existing_window(app_title)
        sys.exit(0)

    # --- 2. Initialize Root Window ---
    root = ctk.CTk()

    # Initialize the main application logic (GUI + Engine)
    app = ControlPanel(root)

    # --- 3. Handle Visibility on Startup ---
    # If not set to start minimized, force the window to appear and take focus.
    # (If start_minimized is True, the ControlPanel class handles hiding it).
    if not app.settings.get('start_minimized', False):
        root.deiconify()
        root.lift()
        try:
            root.focus_force()
        except:
            pass

    # --- 4. Start Event Loop ---
    root.mainloop()