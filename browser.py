import os
import subprocess
import threading
import time
import ctypes
from ctypes import windll, wintypes
from config import BROWSER_PROFILE_DIR, BAMBI_URL

# --- Windows API Constants ---
GWL_STYLE = -16
GWL_EXSTYLE = -20
GWLP_HWNDPARENT = -8

WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_POPUP = 0x80000000
WS_CHILD = 0x40000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

# Positioning Flags
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040

# Clipping Functions
CreateRectRgn = windll.gdi32.CreateRectRgn
SetWindowRgn = windll.user32.SetWindowRgn


class BrowserManager:
    def __init__(self):
        # We still set this to ensure the app draws crisply,
        # but we won't use it for coordinate math anymore.
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass

        self.process = None
        self.chrome_path = self._find_browser()
        self.container = None
        self.browser_hwnd = None
        self.stop_thread = False
        self.sync_thread = None

        # --- CONFIG ---
        self.crop_top = 50  # Hide the top 50px (Address bar)
        self.vertical_adjustment = 0  # Set to 0 initially since GetWindowRect is exact

    def _find_browser(self):
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        ]
        for p in paths:
            if os.path.exists(p): return p
        return None

    def launch_embedded(self, container_widget):
        if not self.chrome_path: return

        # 1. AGGRESSIVE CLEANUP: Kill any old instances before starting
        self._kill_zombies()

        if self.process: return

        self.container = container_widget
        self.container.bind("<Configure>", self._on_container_move)
        try:
            self.container.winfo_toplevel().bind("<Configure>", self._on_container_move)
        except:
            pass

        if not os.path.exists(BROWSER_PROFILE_DIR):
            os.makedirs(BROWSER_PROFILE_DIR)

        cmd = [
            self.chrome_path,
            f"--app={BAMBI_URL}",
            f"--user-data-dir={BROWSER_PROFILE_DIR}",
            "--window-position=3000,3000",
            "--window-size=800,600",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--new-window"
        ]

        try:
            self.process = subprocess.Popen(cmd)
            self.stop_thread = False
            self.sync_thread = threading.Thread(target=self._search_and_dock_loop, daemon=True)
            self.sync_thread.start()
        except Exception as e:
            print(f"Failed to launch browser: {e}")

    def _kill_zombies(self):
        """
        Robustly finds and kills ANY chrome process using our specific
        User Data Directory. This fixes 'ghost' processes that are headless.
        """
        try:
            # We sanitize the path for the WMIC query (doubling backslashes)
            target_path = BROWSER_PROFILE_DIR.replace("\\", "\\\\")

            # This WMIC command finds processes where the Command Line contains our Profile Directory
            # This ensures we NEVER kill the user's personal Chrome, only our embedded instances.
            cmd = f"wmic process where \"name='chrome.exe' and commandline like '%{target_path}%'\" call terminate"

            subprocess.call(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Also try taskkill on the window title just in case
            subprocess.call(['taskkill', '/F', '/FI', 'WINDOWTITLE eq Bambi Cloud'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        except Exception as e:
            print(f"Cleanup warning: {e}")

    def _search_and_dock_loop(self):
        found = False
        attempts = 0
        while not found and attempts < 60 and not self.stop_thread:
            time.sleep(0.25)
            attempts += 1
            if self.process:
                self.browser_hwnd = self._find_window_by_pid(self.process.pid)
            if not self.browser_hwnd:
                self.browser_hwnd = self._find_window_by_title("Bambi Cloud")

            if self.browser_hwnd:
                found = True
                time.sleep(0.2)
                self._apply_embedded_style()
                self._force_sync_position()

        while not self.stop_thread and self.process and self.browser_hwnd:
            if self.container and self.container.winfo_exists():
                try:
                    if not self.container.winfo_viewable():
                        windll.user32.ShowWindow(self.browser_hwnd, 0)
                    else:
                        if windll.user32.IsWindowVisible(self.browser_hwnd) == 0:
                            windll.user32.ShowWindow(self.browser_hwnd, 1)
                        self._force_sync_position()
                        if attempts % 30 == 0: self._apply_clipping()
                except:
                    pass
            time.sleep(0.02)
            attempts += 1

    def _find_window_by_pid(self, target_pid):
        result = None

        def callback(hwnd, extra):
            nonlocal result
            if not windll.user32.IsWindowVisible(hwnd): return True
            pid = wintypes.DWORD()
            windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == target_pid:
                result = hwnd
                return False
            return True

        windll.user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(callback), 0)
        return result

    def _find_window_by_title(self, title_snippet):
        result = None

        def callback(hwnd, extra):
            nonlocal result
            if not windll.user32.IsWindowVisible(hwnd): return True
            length = windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                if title_snippet.lower() in buff.value.lower():
                    class_buff = ctypes.create_unicode_buffer(256)
                    windll.user32.GetClassNameW(hwnd, class_buff, 256)
                    if "Chrome_WidgetWin_1" in class_buff.value:
                        result = hwnd
                        return False
            return True

        windll.user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(callback), 0)
        return result

    def _apply_embedded_style(self):
        if not self.browser_hwnd: return
        try:
            main_app_hwnd = self.container.winfo_toplevel().winfo_id()
            windll.user32.SetWindowLongPtrW(self.browser_hwnd, GWLP_HWNDPARENT, main_app_hwnd)
        except:
            pass

        style = windll.user32.GetWindowLongW(self.browser_hwnd, GWL_STYLE)
        style &= ~WS_CAPTION
        style &= ~WS_THICKFRAME
        windll.user32.SetWindowLongW(self.browser_hwnd, GWL_STYLE, style)

        ex_style = windll.user32.GetWindowLongW(self.browser_hwnd, GWL_EXSTYLE)
        ex_style |= WS_EX_TOOLWINDOW
        windll.user32.SetWindowLongW(self.browser_hwnd, GWL_EXSTYLE, ex_style)

        windll.user32.SetWindowPos(self.browser_hwnd, 0, 0, 0, 0, 0,
                                   SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
        self._apply_clipping()

    def _on_container_move(self, event):
        self._force_sync_position()

    def _force_sync_position(self):
        if not self.browser_hwnd or not self.container: return
        try:
            if not self.container.winfo_viewable(): return

            # --- THE SILVER BULLET FIX ---
            # Instead of asking Tkinter for coordinates (which fails with DPI),
            # we ask Windows for the exact bounding box of the white container.
            rect = wintypes.RECT()
            windll.user32.GetWindowRect(self.container.winfo_id(), ctypes.byref(rect))

            x = rect.left
            y = rect.top
            w = rect.right - rect.left
            h = rect.bottom - rect.top

            # Apply positioning logic based on exact screen pixels
            final_y = y - self.crop_top + self.vertical_adjustment
            final_h = h + self.crop_top - self.vertical_adjustment

            if w > 10 and h > 10:
                windll.user32.MoveWindow(self.browser_hwnd, x, final_y, w, final_h, True)
                windll.user32.SetWindowPos(self.browser_hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
                self._apply_clipping(w, final_h)
        except Exception:
            pass

    def _apply_clipping(self, w=None, h=None):
        if not self.browser_hwnd: return
        if w is None or h is None:
            rect = wintypes.RECT()
            windll.user32.GetWindowRect(self.browser_hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top

        rgn = CreateRectRgn(0, self.crop_top, w, h)
        SetWindowRgn(self.browser_hwnd, rgn, True)

    def resize_to_container(self):
        self._force_sync_position()

    def close(self):
        self.stop_thread = True
        if self.container:
            try:
                self.container.unbind("<Configure>")
                self.container.winfo_toplevel().unbind("<Configure>")
            except:
                pass

        # Kill the specific process object if we have it
        if self.process:
            try:
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.process.pid)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
            self.process = None

        # FINAL SWEEP: Clean up any stragglers
        self._kill_zombies()
        self.browser_hwnd = None