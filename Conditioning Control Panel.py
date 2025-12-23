import tkinter as tk
from tkinter import messagebox, simpledialog, colorchooser
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import random
import os
import sys
import glob
import pygame
import imageio.v3 as iio
import imageio_ffmpeg
import subprocess
import json
import time
import threading
import cv2
import math
import ctypes
import datetime
import shutil
from ctypes import windll, wintypes

# --- LIBRARIES FOR SYSTEM TRAY & AUDIO DUCKING ---
try:
    import pystray
    from pystray import MenuItem as item

    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    print("[DEBUG] Warning: 'pystray' not installed.")

# Audio Ducking Libraries (Windows WASAPI)
try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    AUDIO_CONTROL_AVAILABLE = True
except ImportError:
    AUDIO_CONTROL_AVAILABLE = False
    print("[DEBUG] Warning: 'pycaw' or 'comtypes' not installed.")

# Screen Info
try:
    from screeninfo import get_monitors

    SCREENINFO_AVAILABLE = True
except ImportError:
    SCREENINFO_AVAILABLE = False
    print("[DEBUG] Warning: 'screeninfo' not installed.")

# --- Constants ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
IMG_DIR = os.path.join(ASSETS_DIR, "images")
SND_DIR = os.path.join(ASSETS_DIR, "sounds")
SUB_AUDIO_DIR = os.path.join(ASSETS_DIR, "sub_audio")
STARTLE_VID_DIR = os.path.join(ASSETS_DIR, "startle_videos")

SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
PRESETS_FILE = os.path.join(BASE_DIR, "presets.json")
TEMP_AUDIO_FILE = os.path.join(ASSETS_DIR, "temp_spot_audio.wav")

# Browser Profile for Persistent Cookies
BROWSER_PROFILE_DIR = os.path.join(BASE_DIR, "BambiBrowserData")
BAMBI_URL = "https://bambicloud.com/"

STARTUP_FOLDER = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
STARTUP_FILE_NAME = "ConditioningApp_AutoRun.bat"
STARTUP_FILE_PATH = os.path.join(STARTUP_FOLDER, STARTUP_FILE_NAME)

# --- MODERNIZED BAMBI THEME ---
THEME = {
    "bg": "#FF69B4",
    "header_bg": "#C51162",
    "card_bg": "#FFE4E1",
    "fg": "#4B0082",
    "fg_sub": "#880E4F",
    "font_family": "Segoe UI",
    "btn_bg": "#D500F9",
    "btn_hover": "#AA00FF",
    "accent": "#FF4081",
    "warning": "#D32F2F",
    "entry_bg": "#FFFFFF",
    "entry_text": "#4A148C",
    "tooltip_bg": "#F8BBD0",
    "tooltip_fg": "#880E4F",
    "list_select": "#E1BEE7",
    "xp_bar": "#FF00CC",  # <--- CHANGED TO FLUO PINK
    "xp_bg": "#880E4F"
}

# --- TEXT POOL (MATCHING AUDIO) ---
BAMBI_TEXT_LIST = [
    "BAMBI FREEZE", "BAMBI RESET", "BAMBI SLEEP", "BAMBI UNIFORM LOCK",
    "BIMBO DOLL", "COCK ZOMBIE NOW", "DROP FOR COCK", "GIGGLETIME",
    "GOOD GIRL", "ZAP COCK DRAIN OBEY"
]
BAMBI_POOL_DICT = {text: True for text in BAMBI_TEXT_LIST}

DEFAULT_SETTINGS = {
    "player_level": 1,
    "player_xp": 0.0,
    "flash_enabled": True,
    "min_interval": 20, "max_interval": 180,
    "flash_clickable": True,
    "flash_hydra_limit": 30,
    "startle_enabled": True,
    "startle_freq": 6,
    "startle_strict": False,
    "force_startle_on_launch": False,
    "fade_duration": 0.4, "volume": 0.4,
    "dual_monitor": True,
    "sim_min": 4, "sim_max": 6, "image_scale": 0.9,
    "image_alpha": 1.0,
    "run_on_startup": False,
    "start_minimized": False, "auto_start_engine": False,
    "last_preset": "DEFAULT",
    "subliminal_enabled": False,
    "subliminal_freq": 5,
    "subliminal_duration": 2,
    "subliminal_opacity": 0.8,
    "subliminal_pool": BAMBI_POOL_DICT.copy(),
    "sub_bg_color": "#000000",
    "sub_bg_transparent": False,
    "sub_text_color": "#FF00FF",
    "sub_text_transparent": False,
    "sub_border_color": "#FFFFFF",
    "sub_audio_enabled": False,
    "sub_audio_volume": 0.5,
    "bg_audio_enabled": True,
    "bg_audio_max": 15,
    "disable_panic_esc": False,
    "audio_ducking_enabled": True,
    "audio_ducking_strength": 100,
    "attention_enabled": False,
    "attention_density": 3,
    "attention_lifespan": 5,
    "attention_size": 70,
    "attention_pool": BAMBI_POOL_DICT.copy(),
    "scheduler_enabled": False,
    "scheduler_duration_min": 60,
    "scheduler_multiplier": 1.0,
    "scheduler_link_alpha": False,
    "time_schedule_enabled": False,
    "time_start_str": "16:00",
    "time_end_str": "18:00",
    "active_weekdays": [0, 1, 2, 3, 4, 5, 6]
}


# --- UTILS & CLASSES ---

class SingleInstanceChecker:
    def __init__(self, app_name):
        self.mutex_name = f"Global\\{app_name}_Mutex_v1.5_BROWSER"
        self.mutex = None
        self.last_error = 0

    def check(self):
        try:
            self.mutex = windll.kernel32.CreateMutexW(None, False, self.mutex_name)
            self.last_error = windll.kernel32.GetLastError()
        except Exception:
            pass

    def is_already_running(self):
        return self.last_error == 183

    def focus_existing_window(self, window_title):
        SW_RESTORE = 9
        try:
            hwnd = windll.user32.FindWindowW(None, window_title)
            if hwnd:
                windll.user32.ShowWindow(hwnd, SW_RESTORE)
                windll.user32.SetForegroundWindow(hwnd)
                return True
        except Exception:
            pass
        return False


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.schedule_show)
        self.widget.bind("<Leave>", self.hide_tip)
        self.widget.bind("<ButtonPress>", self.hide_tip)
        self.widget.bind("<Destroy>", self.hide_tip)

    def schedule_show(self, event=None):
        self.unschedule()
        self.id = self.widget.after(600, self.show_tip)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def show_tip(self, event=None):
        if self.tip_window or not self.text: return
        try:
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + 20
        except:
            return

        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        self.tip_window.attributes('-topmost', True)

        frame = tk.Frame(self.tip_window, background=THEME["fg"])
        frame.pack(fill="both", expand=True)

        label = tk.Label(frame, text=self.text, justify="left",
                         background=THEME["tooltip_bg"], fg=THEME["tooltip_fg"],
                         padx=10, pady=6, font=("Segoe UI", 10), wraplength=250, relief="flat")
        label.pack(padx=1, pady=1, fill="both")

    def hide_tip(self, event=None):
        self.unschedule()
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except:
                pass
            self.tip_window = None


class BrowserManager:
    def __init__(self):
        self.process = None
        self.chrome_path = self._find_browser()
        self.container_hwnd = None
        self.browser_hwnd = None
        self.check_thread = None
        self.stop_thread = False
        # How many pixels to shift up to hide the bar.
        # 40px is usually enough for Chrome/Edge app mode headers.
        self.header_offset = 30

    def _find_browser(self):
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        return None

    def launch_embedded(self, container_widget):
        if not self.chrome_path: return
        if self.process: return  # Already running

        # Get HWND of the Tkinter container frame
        self.container_hwnd = container_widget.winfo_id()

        # Ensure user data dir exists
        if not os.path.exists(BROWSER_PROFILE_DIR):
            os.makedirs(BROWSER_PROFILE_DIR)

        # Launch in App Mode
        cmd = [
            self.chrome_path,
            f"--app={BAMBI_URL}",
            f"--user-data-dir={BROWSER_PROFILE_DIR}",
            "--force-device-scale-factor=1.00",
            "--window-position=0,0",
            "--window-size=800,600",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--new-window"
        ]

        try:
            self.process = subprocess.Popen(cmd)
            self.stop_thread = False
            self.check_thread = threading.Thread(target=self._embed_loop, daemon=True)
            self.check_thread.start()
        except Exception as e:
            print(f"Failed to launch browser: {e}")

    def _embed_loop(self):
        found = False
        attempts = 0
        while not found and attempts < 40 and not self.stop_thread:
            time.sleep(0.25)
            attempts += 1
            if self.process:
                def callback(hwnd, extra):
                    # Check if window is visible
                    if not windll.user32.IsWindowVisible(hwnd): return True

                    # Check process ID
                    pid = wintypes.DWORD()
                    windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value == self.process.pid:
                        self.browser_hwnd = hwnd
                        return False  # Stop enumerating
                    return True

                CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                windll.user32.EnumWindows(CMPFUNC(callback), 0)

                if self.browser_hwnd:
                    # 1. Basic Style Removal (We keep WS_CHILD, remove popup/caption)
                    GWL_STYLE = -16
                    WS_CAPTION = 0x00C00000
                    WS_THICKFRAME = 0x00040000
                    WS_POPUP = 0x80000000
                    WS_CHILD = 0x40000000

                    style = windll.user32.GetWindowLongW(self.browser_hwnd, GWL_STYLE)
                    style &= ~(WS_CAPTION | WS_THICKFRAME | WS_POPUP)
                    style |= WS_CHILD

                    windll.user32.SetWindowLongW(self.browser_hwnd, GWL_STYLE, style)

                    # 2. Reparent to our Tkinter Frame
                    windll.user32.SetParent(self.browser_hwnd, self.container_hwnd)

                    # 3. Apply changes
                    SWP_NOMOVE = 0x0002
                    SWP_NOSIZE = 0x0001
                    SWP_NOZORDER = 0x0004
                    SWP_FRAMECHANGED = 0x0020
                    windll.user32.SetWindowPos(self.browser_hwnd, 0, 0, 0, 0, 0,
                                               SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)

                    found = True
                    self.resize_to_container()

    def resize_to_container(self):
        if self.browser_hwnd and self.container_hwnd:
            rect = wintypes.RECT()
            windll.user32.GetClientRect(self.container_hwnd, ctypes.byref(rect))

            # Container dimensions
            container_w = rect.right - rect.left
            container_h = rect.bottom - rect.top

            # SHIFT LOGIC:
            # We set Y to negative 'header_offset'.
            # We increase Height by 'header_offset' so the bottom still reaches the bottom of container.
            x = 0
            y = -self.header_offset
            w = container_w
            h = container_h + self.header_offset

            windll.user32.MoveWindow(self.browser_hwnd, x, y, w, h, True)

    def close(self):
        self.stop_thread = True
        if self.process:
            try:
                self.process.terminate()
            except:
                pass
            self.process = None
            self.browser_hwnd = None

class SystemAudioDucker:
    def __init__(self):
        self.original_volumes = {}
        self.is_ducked = False
        self.browser_names = ["chrome.exe", "msedge.exe", "firefox.exe"]

    def duck(self, strength_percent=100):
        if not AUDIO_CONTROL_AVAILABLE or self.is_ducked: return
        if strength_percent <= 0: return
        factor = 1.0 - (strength_percent / 100.0)
        factor = max(0.0, min(1.0, factor))
        try:
            sessions = AudioUtilities.GetAllSessions()
            current_pid = os.getpid()
            for session in sessions:
                volume = session.SimpleAudioVolume
                if session.Process:
                    is_me = (session.ProcessId == current_pid)
                    is_browser = (session.Process.name().lower() in self.browser_names)
                    if not is_me and not is_browser:
                        orig = volume.GetMasterVolume()
                        self.original_volumes[session.ProcessId] = orig
                        volume.SetMasterVolume(orig * factor, None)
            self.is_ducked = True
        except Exception:
            pass

    def unduck(self):
        if not AUDIO_CONTROL_AVAILABLE or not self.is_ducked: return
        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and session.ProcessId in self.original_volumes:
                    volume = session.SimpleAudioVolume
                    volume.SetMasterVolume(self.original_volumes[session.ProcessId], None)
            self.original_volumes.clear()
            self.is_ducked = False
        except Exception:
            pass


class TextManagerDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, data_dict, on_update_callback):
        super().__init__(parent)
        self.title(title)
        self.geometry("500x400")
        self.configure(fg_color=THEME["bg"])
        self.attributes('-topmost', True)
        self.data = data_dict
        self.on_update = on_update_callback
        self.selected_keys = set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ctk.CTkLabel(header_frame, text=f"{title} Manager", font=(THEME["font_family"], 16, "bold"),
                     text_color=THEME["fg"]).pack(side="left")
        ctk.CTkButton(header_frame, text="Sort A-Z", width=80, height=24, fg_color=THEME["accent"],
                      command=self.sort_list).pack(side="right")

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=THEME["card_bg"])
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.grid(row=1, column=1, sticky="ns", padx=(5, 10), pady=5)

        ctk.CTkButton(ctrl_frame, text="Add +", fg_color=THEME["btn_bg"], command=self.add_item).pack(pady=5, fill="x")
        self.btn_toggle_all = ctk.CTkButton(ctrl_frame, text="Toggle All", fg_color=THEME["btn_bg"],
                                            command=self.toggle_all)
        self.btn_toggle_all.pack(pady=5, fill="x")
        ctk.CTkButton(ctrl_frame, text="Remove", fg_color=THEME["warning"], command=self.remove_selected).pack(pady=20,
                                                                                                               fill="x")
        ctk.CTkButton(ctrl_frame, text="Close", fg_color="gray", command=self.destroy).pack(side="bottom", pady=10)
        self.refresh_list()

    def refresh_list(self):
        for widget in self.scroll_frame.winfo_children(): widget.destroy()
        for key in self.data: self.create_row(key, self.data[key])

    def sort_list(self):
        sorted_keys = sorted(self.data.keys(), key=lambda k: k.lower())
        for widget in self.scroll_frame.winfo_children(): widget.destroy()
        for key in sorted_keys: self.create_row(key, self.data[key])

    def create_row(self, key, active):
        row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent", corner_radius=5)
        row.pack(fill="x", pady=2)
        is_selected = key in self.selected_keys
        row.configure(fg_color=THEME["list_select"] if is_selected else "transparent")
        var = ctk.BooleanVar(value=active)

        def on_check():
            self.data[key] = var.get()
            self.on_update()

        ctk.CTkCheckBox(row, text="", variable=var, width=24, command=on_check,
                        fg_color=THEME["btn_bg"], hover_color=THEME["btn_hover"]).pack(side="left", padx=5)
        lbl = ctk.CTkLabel(row, text=key, text_color=THEME["fg"], anchor="w")
        lbl.pack(side="left", fill="x", expand=True, padx=5)

        def toggle_select(event):
            if key in self.selected_keys:
                self.selected_keys.remove(key)
                row.configure(fg_color="transparent")
            else:
                self.selected_keys.add(key)
                row.configure(fg_color=THEME["list_select"])

        lbl.bind("<Button-1>", toggle_select)
        row.bind("<Button-1>", toggle_select)

    def add_item(self):
        text = simpledialog.askstring("Add Item", "Enter new text/trigger:")
        if text:
            clean = text.strip()
            if clean:
                self.data[clean] = True
                self.on_update()
                self.refresh_list()

    def toggle_all(self):
        all_active = all(self.data.values())
        new_state = not all_active
        for k in self.data: self.data[k] = new_state
        self.on_update()
        self.refresh_list()
        self.btn_toggle_all.configure(text="Deactivate All" if new_state else "Activate All")

    def remove_selected(self):
        if not self.selected_keys: return
        if messagebox.askyesno("Remove", f"Remove {len(self.selected_keys)} items?"):
            for k in list(self.selected_keys):
                if k in self.data: del self.data[k]
            self.selected_keys.clear()
            self.on_update()
            self.refresh_list()


class TransparentTextWindow(tk.Toplevel):
    def __init__(self, parent, text, x, y, bounds_w, bounds_h, offset_x, offset_y, font_size, on_click_callback):
        super().__init__(parent)
        self.on_click = on_click_callback
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.clicked = False
        self.pos_x = float(x)
        self.pos_y = float(y)
        speed = 2.0
        angle = random.uniform(0, 2 * math.pi)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.min_x = offset_x
        self.max_x = offset_x + bounds_w
        self.min_y = offset_y
        self.max_y = offset_y + bounds_h
        TRANS_KEY = "#000001"
        self.config(bg=TRANS_KEY)
        self.wm_attributes("-transparentcolor", TRANS_KEY)
        self.attributes("-alpha", 1.0)
        self.canvas = tk.Canvas(self, bg=TRANS_KEY, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        font_spec = ("Impact", int(font_size), "normal")
        wrap_w = int(font_size * 10)
        temp_id = self.canvas.create_text(0, 0, text=text, font=font_spec, width=wrap_w, anchor="nw")
        bbox = self.canvas.bbox(temp_id)
        self.canvas.delete(temp_id)
        if not bbox: bbox = (0, 0, 200, 100)
        pad = 20
        self.w_width = (bbox[2] - bbox[0]) + pad * 2
        self.w_height = (bbox[3] - bbox[1]) + pad * 2
        self.geometry(f"{self.w_width}x{self.w_height}+{int(x)}+{int(y)}")
        center_x, center_y = self.w_width // 2, self.w_height // 2

        try:
            hwnd = windll.user32.GetParent(self.winfo_id())
            windll.user32.SetWindowLongW(hwnd, -20, 0x08000000 | 0x00000008)
        except:
            pass

        border_thickness = 3
        steps = 12
        for i in range(steps):
            angle_rad = (2 * math.pi * i) / steps
            ox = border_thickness * math.cos(angle_rad)
            oy = border_thickness * math.sin(angle_rad)
            t = self.canvas.create_text(center_x + ox, center_y + oy, text=text, font=font_spec,
                                        width=wrap_w, fill="black", justify="center")
            self.canvas.tag_bind(t, "<Button-1>", self.handle_click)
        self.text_id = self.canvas.create_text(center_x, center_y, text=text, font=font_spec,
                                               width=wrap_w, fill="#FF00FF", justify="center")
        self.canvas.tag_bind(self.text_id, "<Button-1>", self.handle_click)
        self.canvas.bind("<Button-1>", self.handle_click)
        self.animate_move()

    def animate_move(self):
        if not self.winfo_exists() or self.clicked: return
        self.pos_x += self.vx
        self.pos_y += self.vy
        if self.pos_x <= self.min_x:
            self.pos_x = self.min_x;
            self.vx *= -1
        elif (self.pos_x + self.w_width) >= self.max_x:
            self.pos_x = self.max_x - self.w_width;
            self.vx *= -1
        if self.pos_y <= self.min_y:
            self.pos_y = self.min_y;
            self.vy *= -1
        elif (self.pos_y + self.w_height) >= self.max_y:
            self.pos_y = self.max_y - self.w_height;
            self.vy *= -1
        try:
            self.geometry(f"+{int(self.pos_x)}+{int(self.pos_y)}")
            self.lift()
            self.attributes('-topmost', True)
            self.after(20, self.animate_move)
        except Exception:
            pass

    def handle_click(self, event):
        if self.clicked: return
        self.clicked = True
        self.on_click()
        self.start_fade_out()

    def start_fade_out(self):
        if not self.winfo_exists(): return
        try:
            alpha = self.attributes("-alpha")
            if alpha > 0.05:
                alpha -= 0.15
                self.attributes("-alpha", alpha)
                self.after(30, self.start_fade_out)
            else:
                self.destroy()
        except Exception:
            pass

class FlasherEngine:
    def __init__(self, root_tk_ref, panic_callback):
        self.running = False
        self.run_token = 0
        self.root = root_tk_ref
        self.panic_callback = panic_callback
        self.settings = DEFAULT_SETTINGS.copy()
        self.active_windows = []
        self.active_rects = []
        self.busy = False
        self.virtual_end_time = 0
        self.video_running = False
        self.strict_active = False
        self.events_pending_reschedule = set()
        self.ducker = SystemAudioDucker()
        self.browser = BrowserManager()
        self.penalty_loop_count = 0
        self.gui_update_callback = None
        self.scheduler_update_callback = None
        self.xp_update_callback = None
        self.attention_spawns = []
        self.targets_total = 0
        self.targets_hit = 0
        self.session_targets_clicked = 0
        self.current_video_duration = 0
        self.retry_video_path = None
        self.active_floating_texts = []
        self.gj_sound = None
        self.session_start_time = 0
        self.current_intensity_progress = 0.0
        self.bg_audio_accumulator = 0.0
        self.last_heartbeat_time = time.time()
        self.paths = {
            "images": IMG_DIR,
            "sounds": SND_DIR,
            "startle_videos": STARTLE_VID_DIR,
            "sub_audio": SUB_AUDIO_DIR
        }
        for path in self.paths.values(): os.makedirs(path, exist_ok=True)
        self.media_queues = {'startle': [], 'flash': []}

        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=8, buffer=4096)
            pygame.display.init()
        except:
            pass
        self.load_gj_sound()
        self.esc_listener_active = True
        self.esc_thread = threading.Thread(target=self._monitor_global_esc, daemon=True)
        self.esc_thread.start()
        self.clock_monitor_thread = threading.Thread(target=self._monitor_time_schedule, daemon=True)
        self.clock_monitor_thread.start()
        self.heartbeat()

    def _monitor_global_esc(self):
        while self.esc_listener_active:
            if ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000:
                self._handle_esc_press()
                time.sleep(0.5)
            time.sleep(0.05)

    def _monitor_time_schedule(self):
        while True:
            time.sleep(5)
            if not self.settings.get('time_schedule_enabled', False): continue
            now = datetime.datetime.now()
            active_days = self.settings.get('active_weekdays', [0, 1, 2, 3, 4, 5, 6])
            if now.weekday() not in active_days:
                if self.running: self.root.after(0, self.stop)
                continue
            start_str = self.settings.get('time_start_str', "16:00")
            end_str = self.settings.get('time_end_str', "18:00")
            try:
                t_start = datetime.datetime.strptime(start_str, "%H:%M").time()
                t_end = datetime.datetime.strptime(end_str, "%H:%M").time()
                current_time = now.time()
                is_in_window = False
                if t_start < t_end:
                    is_in_window = t_start <= current_time < t_end
                else:
                    is_in_window = current_time >= t_start or current_time < t_end
                if is_in_window and not self.running:
                    self.root.after(0, lambda: self.start(is_startup=True))
                elif not is_in_window and self.running:
                    self.root.after(0, self.stop)
            except ValueError:
                pass

    def _handle_esc_press(self):
        if self.settings.get('disable_panic_esc', False): return
        if self.video_running and self.settings.get('startle_strict', False): return
        self.root.after(0, self.trigger_panic_from_window)

    def set_gui_callback(self, cb):
        self.gui_update_callback = cb

    def set_scheduler_callback(self, cb):
        self.scheduler_update_callback = cb

    def set_xp_callback(self, cb):
        self.xp_update_callback = cb

    def load_gj_sound(self):
        pattern = os.path.join(ASSETS_DIR, "GJ1.*")
        found = glob.glob(pattern)
        if found:
            try:
                self.gj_sound = pygame.mixer.Sound(found[0])
            except:
                pass

    def play_gj(self):
        if self.gj_sound:
            try:
                self.gj_sound.play()
            except:
                pass

    def update_settings(self, new_settings):
        needs_reschedule = False
        check_keys = ['min_interval', 'max_interval', 'flash_enabled', 'subliminal_enabled', 'subliminal_freq',
                      'startle_enabled', 'startle_freq', 'sub_audio_enabled']
        for k in check_keys:
            if new_settings.get(k) != self.settings.get(k): needs_reschedule = True; break

        # --- FIX: REMOVED XP BLOCKERS ---
        # The lines that overwrote 'player_level' and 'player_xp' were deleted here.
        # This allows the engine to actually accept the XP loaded from your save file.

        self.settings = new_settings
        if self.running and needs_reschedule: self.reschedule_timers()
    def reschedule_timers(self):
        if not self.running: return
        self.run_token += 1
        if self.settings.get('flash_enabled', True): self.schedule_next("flash")
        if self.settings.get('startle_enabled'): self.schedule_next("startle")
        if self.settings.get('subliminal_enabled'): self.schedule_next("subliminal")

    def start(self, is_startup=False):
        if self.running: return
        self.running = True
        self.run_token += 1
        self.events_pending_reschedule.clear()
        self.session_start_time = time.time()
        self.current_intensity_progress = 0.0
        self.bg_audio_accumulator = 0.0
        self.last_heartbeat_time = time.time()
        delay_loops = 0
        if self.settings.get('force_startle_on_launch'):
            self.busy = True
            self.root.after(5000, self._startup_startle_trigger)
            delay_loops = 20000
        self.root.after(delay_loops, self._start_loops)

    def get_effective_value(self, key, base_val=None):
        val = base_val if base_val is not None else self.settings.get(key)
        if key == 'image_alpha':
            if self.settings.get('scheduler_enabled', False) and self.settings.get('scheduler_link_alpha', False):
                return 0.3 + (0.7 * self.current_intensity_progress)
            return val
        if not self.settings.get('scheduler_enabled', False): return val
        progress = self.current_intensity_progress
        multiplier = self.settings.get('scheduler_multiplier', 1.0)
        if key == 'min_interval' or key == 'max_interval':
            target = val / max(1.0, multiplier)
            return int(val - ((val - target) * progress))
        elif key == 'startle_freq':
            target = min(35, val * multiplier)
            return int(val + ((target - val) * progress))
        elif key == 'subliminal_freq':
            target = val * multiplier
            return int(val + ((target - val) * progress))
        elif key == 'volume':
            bonus = (multiplier - 1.0) * 0.15
            target = val + bonus
            current_vol = val + ((target - val) * progress)
            return min(1.0, current_vol)
        return val

    def _update_scheduler_progress(self):
        if not self.running or not self.settings.get('scheduler_enabled', False):
            self.current_intensity_progress = 0.0;
            return
        duration_sec = self.settings.get('scheduler_duration_min', 60) * 60
        elapsed = time.time() - self.session_start_time
        prog = elapsed / max(1, duration_sec)
        self.current_intensity_progress = min(1.0, max(0.0, prog))
        if self.scheduler_update_callback:
            multiplier = self.settings.get('scheduler_multiplier', 1.0)
            remaining = max(0, duration_sec - elapsed)
            self.scheduler_update_callback(self.current_intensity_progress, multiplier, remaining)

    def _startup_startle_trigger(self):
        self.busy = True
        self.trigger_event("startle", strict_override=True)

    def _start_loops(self):
        if not self.running: return
        if not self.video_running: self.busy = False
        if self.settings.get('flash_enabled', True): self.schedule_next("flash")
        if self.settings.get('startle_enabled'): self.schedule_next("startle")
        if self.settings.get('subliminal_enabled'): self.schedule_next("subliminal")

    def stop(self):
        self.running = False
        self.ducker.unduck()
        self.root.after(0, self.panic_stop)

    def trigger_panic_from_window(self, event=None):
        if self.settings.get('disable_panic_esc', False): return
        if self.video_running and self.settings.get('startle_strict', False): return
        self.panic_stop()
        if self.panic_callback: self.root.after(0, self.panic_callback)

    def panic_stop(self, event=None):
        self.running = False;
        self.busy = False;
        self.video_running = False
        try:
            pygame.mixer.stop()
        except:
            pass
        self.ducker.unduck()
        for win in self.active_windows:
            try:
                win.destroy()
            except:
                pass
        self.active_windows.clear();
        self.active_rects.clear()
        for t in self.active_floating_texts:
            try:
                t.destroy()
            except:
                pass
        self.active_floating_texts.clear()
        if hasattr(self, 'cap') and self.cap: self.cap.release()
        self.events_pending_reschedule.clear()
        self.strict_active = False
        try:
            self.root.deiconify();
            self.root.lift()
        except:
            pass

    def schedule_next(self, event_type):
        if not self.running: return
        seconds = 10
        if event_type == "startle":
            base_freq = max(1, self.settings.get('startle_freq', 10))
            eff_freq = self.get_effective_value('startle_freq', base_freq)
            seconds = int((60 / max(1, eff_freq)) * 60) + random.randint(-30, 30);
            seconds = max(5, seconds)
        elif event_type == "flash":
            min_i = self.get_effective_value('min_interval')
            max_i = self.get_effective_value('max_interval')
            if max_i < min_i: max_i = min_i + 1
            seconds = random.randint(min_i, max_i)
        elif event_type == "subliminal":
            base_freq = max(1, self.settings.get('subliminal_freq', 10))
            eff_freq = self.get_effective_value('subliminal_freq', base_freq)
            base = 60 / max(1, eff_freq)
            seconds = base + random.uniform(-base * 0.2, base * 0.2);
            seconds = max(1, seconds)
        elif event_type == "sub_audio":
            base_freq = max(1, self.settings.get('subliminal_freq', 10))
            base = 60 / max(1, base_freq)
            seconds = base + random.uniform(-base * 0.3, base * 0.3)
            seconds = max(2, seconds)
        token_at_schedule = self.run_token
        self.root.after(int(seconds * 1000), lambda: self._safe_trigger(event_type, token_at_schedule))

    def _safe_trigger(self, event_type, token):
        if token != self.run_token: return
        self.trigger_event(event_type)

    def get_files(self, folder):
        valid_ext = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.mp4', '*.mov', '*.mp3', '*.wav']
        files = []
        if os.path.exists(folder):
            for ext in valid_ext: files.extend(glob.glob(os.path.join(folder, ext)))
        return files

    def extract_audio_from_video(self, video_path):
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [ffmpeg_exe, '-y', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2',
                   TEMP_AUDIO_FILE]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(TEMP_AUDIO_FILE): return TEMP_AUDIO_FILE
        except:
            pass
        return None

    def _do_duck(self):
        if self.settings.get('audio_ducking_enabled', True):
            strength = self.settings.get('audio_ducking_strength', 100)
            self.ducker.duck(strength)

    def _duck_subliminal_channel(self, should_duck):
        try:
            sub_vol = self.settings.get('sub_audio_volume', 0.5)
            if should_duck:
                pygame.mixer.Channel(2).set_volume(sub_vol * 0.2)
            else:
                pygame.mixer.Channel(2).set_volume(sub_vol)
        except:
            pass

    def trigger_event(self, event_type, strict_override=False):
        if not self.running: return

        if event_type == "subliminal":
            self._flash_subliminal();
            self.schedule_next("subliminal");
            return

        if event_type == "startle":
            if self.video_running: self.events_pending_reschedule.add(event_type); return
            self.busy = True
        else:
            if not self.settings.get('flash_enabled', True): return
            self.events_pending_reschedule.add(event_type)
            if len(self.active_windows) > 0 or self.busy or self.video_running: return
            self.busy = True

        if event_type == "startle":
            video_path = self.get_next_media('startle', self.paths['startle_videos'])
            if not video_path: self.busy = False; return
            is_strict = self.settings.get('startle_strict', False) or strict_override
            self.penalty_loop_count = 0
            threading.Thread(target=self._prep_startle_video, args=(video_path, is_strict), daemon=True).start()
            return

        media_pool = self.get_files(self.paths['images'])
        sound_pool = self.get_files(self.paths['sounds'])
        if not media_pool: self.busy = False; return
        sound_path = random.choice(sound_pool) if sound_pool else None
        monitors = self._get_monitors_safe()
        min_sim = max(1, self.settings.get('sim_min', 1))
        max_sim = max(min_sim, self.settings.get('sim_max', 1))
        num_images = random.randint(min_sim, max_sim)
        selected_images = []
        for _ in range(num_images):
            img = self.get_next_media('flash', self.paths['images'])
            if img: selected_images.append(img)
        if not selected_images: self.busy = False; return
        base_scale = self.settings.get('image_scale', 1.0)
        threading.Thread(target=self._background_loader,
                         args=(selected_images, sound_path, False, False, monitors, base_scale), daemon=True).start()

    def get_next_media(self, category, folder_path):
        if not self.media_queues.get(category):
            files = self.get_files(folder_path)
            if not files: return None
            random.shuffle(files)
            self.media_queues[category] = files
        if self.media_queues[category]:
            item = self.media_queues[category].pop()
            return os.path.abspath(item)
        return None

    def _flash_subliminal(self):
        pool = self.settings.get('subliminal_pool', {})
        active_subs = [text for text, active in pool.items() if active]
        if not active_subs: return
        text_content = random.choice(active_subs)
        linked_audio_path = None
        clean_text = text_content.strip()
        for ext in ['.mp3', '.wav', '.ogg']:
            path = os.path.join(self.paths['sub_audio'], clean_text + ext)
            if os.path.exists(path):
                linked_audio_path = path
                break
            path_lower = os.path.join(self.paths['sub_audio'], clean_text.lower() + ext)
            if os.path.exists(path_lower):
                linked_audio_path = path_lower
                break

        if linked_audio_path and self.settings.get('sub_audio_enabled', False):
            self._do_duck()
            try:
                snd = pygame.mixer.Sound(linked_audio_path)
                vol = self.settings.get('sub_audio_volume', 0.5)
                chan = pygame.mixer.Channel(2)
                chan.set_volume(vol)
                chan.play(snd)
                length = snd.get_length()
                self._add_xp(1)
                self.root.after(int(length * 1000) + 500, self.ducker.unduck)
            except:
                self.ducker.unduck()
            self.root.after(300, lambda: self._show_subliminal_visuals(text_content))
        else:
            self._show_subliminal_visuals(text_content)

    def _show_subliminal_visuals(self, text_content):
        duration_ms = int(self.settings.get('subliminal_duration', 1) * 16.6)
        if duration_ms < 100: duration_ms = 100
        self._add_xp(1)
        target_opacity = self.settings.get('subliminal_opacity', 0.8)
        TRANS_KEY = "#000001"
        bg_color = self.settings.get("sub_bg_color", "#000000")
        is_bg_trans = self.settings.get("sub_bg_transparent", False)
        txt_color = self.settings.get("sub_text_color", "#FF00FF")
        is_txt_trans = self.settings.get("sub_text_transparent", False)
        border_color = self.settings.get("sub_border_color", "#FFFFFF")
        final_bg = TRANS_KEY if is_bg_trans else bg_color

        monitors = self._get_monitors_safe()
        for m in monitors:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True)
            win.config(bg=final_bg)
            win.geometry(f"{m['width']}x{m['height']}+{m['x']}+{m['y']}")
            win.attributes('-topmost', True)
            win.attributes('-alpha', 0.0)
            win.wm_attributes("-transparentcolor", TRANS_KEY)
            try:
                hwnd = windll.user32.GetParent(win.winfo_id())
                windll.user32.SetWindowLongW(hwnd, -20, 0x08000000 | 0x00000008)
            except:
                pass
            canvas = tk.Canvas(win, bg=final_bg, width=m['width'], height=m['height'], highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            cx, cy = m['width'] // 2, m['height'] // 2
            font_spec = ("Arial", 120, "bold")
            offsets = [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, -3), (0, 3), (-3, 0), (3, 0)]
            for ox, oy in offsets:
                canvas.create_text(cx + ox, cy + oy, text=text_content, font=font_spec, fill=border_color,
                                   justify="center")
            if is_txt_trans:
                canvas.create_text(cx, cy, text=text_content, font=font_spec, fill=final_bg, justify="center")
            else:
                canvas.create_text(cx, cy, text=text_content, font=font_spec, fill=txt_color, justify="center")
            self._animate_fade(win, 0.0, target_opacity, 5, duration_ms)

    def _animate_fade(self, win, current, target, step_ms, hold_ms):
        if not win.winfo_exists(): return
        if current < target:
            new_alpha = min(target, current + 0.1)
            win.attributes('-alpha', new_alpha)
            self.root.after(step_ms, lambda: self._animate_fade(win, new_alpha, target, step_ms, hold_ms))
        else:
            self.root.after(hold_ms, lambda: self._animate_fade_out(win, target, step_ms))

    def _animate_fade_out(self, win, current, step_ms):
        if not win.winfo_exists(): return
        if current > 0.0:
            new_alpha = max(0.0, current - 0.1)
            win.attributes('-alpha', new_alpha)
            self.root.after(step_ms, lambda: self._animate_fade_out(win, new_alpha, step_ms))
        else:
            win.destroy()

    def _get_monitors_safe(self):
        monitors = []
        if SCREENINFO_AVAILABLE:
            try:
                raw = get_monitors();
                monitors = [{'x': m.x, 'y': m.y, 'width': m.width, 'height': m.height, 'is_primary': m.is_primary} for m
                            in raw]
            except:
                pass
        if not monitors: monitors = [
            {'x': 0, 'y': 0, 'width': self.root.winfo_screenwidth(), 'height': self.root.winfo_screenheight(),
             'is_primary': True}]
        if not self.settings.get('dual_monitor', True):
            primary_monitor = [m for m in monitors if m.get('is_primary')]
            if primary_monitor:
                return primary_monitor
            elif monitors:
                return [monitors[0]]
        return monitors

    def _apply_window_lock(self, win, is_strict):
        # NOTE: This function applies strict locking.
        # Ensure overriding redirect is active in caller (it is in _start_startle_player)
        try:
            win.attributes("-toolwindow", 1)
        except:
            pass
        if is_strict:
            win.protocol("WM_DELETE_WINDOW", lambda: None)
            win.bind('<Alt-F4>', lambda e: "break");
            win.bind("<Tab>", lambda e: "break");
            win.bind("<Alt-Tab>", lambda e: "break")
            win.lift();
            win.focus_force()
        else:
            try:
                hwnd = windll.user32.GetParent(win.winfo_id())
                windll.user32.SetWindowLongW(hwnd, -20, 0x08000000 | 0x00000008)
            except:
                pass

    def _prep_startle_video(self, video_path, is_strict):
        audio_path = self.extract_audio_from_video(video_path)
        self.root.after(0, lambda: self._start_startle_player(video_path, audio_path, is_strict))

    def _start_startle_player(self, video_path, audio_path, is_strict):
        if not self.running: self.busy = False; return
        pygame.mixer.stop()
        for win in list(self.active_windows):
            try:
                win.destroy()
            except:
                pass
        self.active_windows.clear();
        self.active_rects.clear()
        if is_strict:
            self.strict_active = True
            try:
                self.root.withdraw();
                self.root.update()
            except:
                pass
        else:
            self.strict_active = False
        self.video_running = True;
        self._do_duck()
        self._duck_subliminal_channel(True)
        self.attention_spawns = [];
        self.targets_hit = 0;
        self.targets_total = 0;
        self.session_targets_clicked = 0
        self.retry_video_path = None
        self._add_xp(50, is_video_context=True)

        if audio_path and os.path.exists(audio_path):
            try:
                self.vid_sound = pygame.mixer.Sound(audio_path);
                self.vid_channel = pygame.mixer.Channel(1)
                vol = self.settings.get('volume', 1.0);
                curved_vol = vol ** 2
                self.vid_channel.set_volume(curved_vol)
                self.vid_channel.play(self.vid_sound)
            except:
                pass
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened(): self._cleanup_video(); return
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        duration_sec = (self.cap.get(cv2.CAP_PROP_FRAME_COUNT) / self.video_fps)
        self.current_video_duration = duration_sec
        if self.settings.get('attention_enabled', False):
            density = self.settings.get('attention_density', 2)
            count = int((duration_sec / 30.0) * density);
            self.targets_total = count
            if count > 0:
                safe_end = max(2.0, duration_sec - 5.0)
                for _ in range(count): t = random.uniform(2.0, safe_end); self.attention_spawns.append(t)
                self.attention_spawns.sort();
                self.retry_video_path = video_path
        self.video_windows = []
        monitors = self._get_monitors_safe()
        for m in monitors:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True);  # Critical: removes title bar and borders
            win.config(bg='black')
            win.geometry(f"{m['width']}x{m['height']}+{m['x']}+{m['y']}")
            win.attributes('-topmost', True);
            win.is_locked_spot = True
            self._apply_window_lock(win, is_strict)
            lbl = tk.Label(win, bg='black', bd=0);
            lbl.pack(expand=True, fill='both')
            self.video_windows.append({"win": win, "lbl": lbl, "w": m['width'], "h": m['height']})
            self.active_windows.append(win)
        self.video_start_time = time.time()
        self.current_spot_strict = is_strict
        self._video_loop()

    def _video_loop(self):
        if not self.video_running or not self.running: self._cleanup_video(); return
        if getattr(self, 'current_spot_strict', False) and self.video_windows:
            try:
                self.video_windows[0]['win'].focus_force()
            except:
                pass
        if self.active_floating_texts:
            for t in self.active_floating_texts:
                try:
                    t.lift()
                except:
                    pass
        elapsed = time.time() - self.video_start_time
        if elapsed > self.current_video_duration + 0.5: self._cleanup_video(); return
        if self.attention_spawns:
            if elapsed >= self.attention_spawns[0]: self._spawn_attention_target(); self.attention_spawns.pop(0)
        target_frame_num = int(elapsed * self.video_fps)
        current_frame_num = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        if current_frame_num < target_frame_num:
            gap = target_frame_num - current_frame_num
            if gap > 5:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_num)
            else:
                for _ in range(gap): self.cap.grab()
        ret, frame = self.cap.read()
        if not ret or frame is None: self._cleanup_video(); return
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        last_dims = None;
        last_tk_img = None
        for vw in self.video_windows:
            try:
                tw, th = vw['w'], vw['h']
                h, w = rgb_frame.shape[:2]
                scale = min(tw / w, th / h)
                nw, nh = int(w * scale), int(h * scale)
                if (nw, nh) == last_dims and last_tk_img:
                    tk_img = last_tk_img
                else:
                    resized = cv2.resize(rgb_frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
                    img = Image.fromarray(resized);
                    tk_img = ImageTk.PhotoImage(image=img)
                    last_dims = (nw, nh);
                    last_tk_img = tk_img
                vw['lbl'].configure(image=tk_img);
                vw['lbl'].image = tk_img
            except:
                pass
        self.root.after(15, self._video_loop)

    def _spawn_attention_target(self):
        if not self.video_windows: return
        pool = self.settings.get('attention_pool', {})
        active_texts = [t for t, a in pool.items() if a]
        text = random.choice(active_texts) if active_texts else "CLICK ME"
        try:
            target_win_data = random.choice(self.video_windows)
        except IndexError:
            return
        win_x = target_win_data['win'].winfo_x();
        win_y = target_win_data['win'].winfo_y()
        w = target_win_data['w'];
        h = target_win_data['h']
        size = self.settings.get('attention_size', 40)
        min_offset = 20
        safe_max_x = max(min_offset, w - int(size * 10));
        safe_max_x = max(safe_max_x, min_offset + 10)
        safe_max_y = max(min_offset, h - int(size * 3));
        safe_max_y = max(safe_max_y, min_offset + 10)
        rx = win_x + random.randint(min_offset, safe_max_x)
        ry = win_y + random.randint(min_offset, safe_max_y)

        def on_hit():
            self.targets_hit += 1;
            self.session_targets_clicked += 1
            self.play_gj()
            self._add_xp(5, is_video_context=True)

        try:
            t_win = TransparentTextWindow(self.root, text, rx, ry, w, h, win_x, win_y, size, on_hit)
            self.active_floating_texts.append(t_win)
        except Exception:
            return
        lifespan_sec = self.settings.get('attention_lifespan', 4)

        def expire():
            if t_win in self.active_floating_texts:
                self.active_floating_texts.remove(t_win)
                try:
                    t_win.destroy()
                except:
                    pass

        self.root.after(int(lifespan_sec * 1000), expire)

    def _cleanup_video(self):
        self.video_running = False;
        self.busy = False
        if hasattr(self, 'cap') and self.cap: self.cap.release()
        for vw in self.video_windows:
            try:
                vw['win'].destroy()
            except:
                pass
        self.video_windows = []
        for t in self.active_floating_texts:
            try:
                t.destroy()
            except:
                pass
        self.active_floating_texts.clear()
        if os.path.exists(TEMP_AUDIO_FILE):
            try:
                os.remove(TEMP_AUDIO_FILE)
            except:
                pass
        self.ducker.unduck()
        self._duck_subliminal_channel(False)
        loop_needed = False;
        is_troll_loop = False
        if self.settings.get('attention_enabled', False):
            passed = (self.targets_total == 0) or (self.targets_hit >= self.targets_total)
            if not passed:
                loop_needed = True
            elif random.random() < 0.10:
                loop_needed = True;
                is_troll_loop = True
            if passed:
                self._add_xp(10, is_video_context=True)
                if self.session_targets_clicked >= 10:
                    self._add_xp(20, is_video_context=True)

        if loop_needed and self.retry_video_path:
            self.penalty_loop_count += 1
            if self.penalty_loop_count >= 3:
                self.trigger_mercy_card()
            else:
                self.trigger_penalty_loop(is_troll=is_troll_loop)
            return
        if self.strict_active:
            self.strict_active = False
            try:
                self.root.deiconify();
                self.root.lift()
            except:
                pass
        if self.settings.get('startle_enabled'): self.schedule_next("startle")
        if self.settings.get('subliminal_enabled'): self.schedule_next("subliminal")
        if self.events_pending_reschedule:
            for ev in list(self.events_pending_reschedule): self.schedule_next(ev)
            self.events_pending_reschedule.clear()

    def trigger_mercy_card(self):
        self._add_xp(10, is_video_context=True)
        monitors = self._get_monitors_safe()
        mercy_wins = []
        for m in monitors:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True);
            win.config(bg='black')
            win.geometry(f"{m['width']}x{m['height']}+{m['x']}+{m['y']}")
            win.attributes('-topmost', True);
            win.lift();
            win.focus_force()
            lbl = tk.Label(win, text="BAMBI IS SO DUMB\nBAMBI RESET\n DROP FOR COCK", fg="#FF00FF", bg="black",
                           font=("Impact", 85, "bold"))
            lbl.pack(expand=True);
            mercy_wins.append(win)

        def finish_mercy():
            for w in mercy_wins: w.destroy()
            if self.strict_active:
                self.strict_active = False
                try:
                    self.root.deiconify();
                    self.root.lift()
                except:
                    pass
            if self.settings.get('startle_enabled'): self.schedule_next("startle")
            if self.settings.get('subliminal_enabled'): self.schedule_next("subliminal")
            if self.events_pending_reschedule:
                for ev in list(self.events_pending_reschedule): self.schedule_next(ev)
                self.events_pending_reschedule.clear()

        self.root.after(2500, finish_mercy)

    def trigger_penalty_loop(self, is_troll=False):
        self._add_xp(20, is_video_context=True)
        if self.settings.get('startle_strict', False):
            self.strict_active = True
            try:
                self.root.withdraw();
                self.root.update()
            except:
                pass
        monitors = self._get_monitors_safe()
        penalty_wins = []
        if is_troll:
            msg = "SUCH A GOOD SLUT BAMBI \nYOU DID IT...BUT\n SUCH GOOD GIRLS MUST AGAIN 😈";
            f_size = 85
        else:
            msg = "WHAT A DUMB BAMBI\n DUMB BIMBOS MUST TRY AGAIN";
            f_size = 100
        for m in monitors:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True);
            win.config(bg='black')
            win.geometry(f"{m['width']}x{m['height']}+{m['x']}+{m['y']}")
            win.attributes('-topmost', True)
            lbl = tk.Label(win, text=msg, fg="#FF00FF", bg="black", font=("Impact", f_size, "bold"))
            lbl.pack(expand=True);
            penalty_wins.append(win)

        def restart():
            for w in penalty_wins: w.destroy()
            is_strict = self.settings.get('startle_strict', False)
            threading.Thread(target=self._prep_startle_video, args=(self.retry_video_path, is_strict),
                             daemon=True).start()

        self.root.after(1500, restart)

    def on_image_click(self, win, is_startle, event_type):
        if hasattr(win, 'is_locked_spot') and win.is_locked_spot: return
        if not self.settings.get('flash_clickable', True): return
        if win in self.active_windows:
            self.active_windows.remove(win)
            self.active_rects = [r for r in self.active_rects if r['win'] != win]
        win.destroy();
        max_hydra = self.settings.get('flash_hydra_limit', 30)
        current_count = len(self.active_windows)
        if current_count < max_hydra:
            self.trigger_multiplication(is_startle, event_type)

    def trigger_multiplication(self, is_startle, event_type):
        if not self.running: return
        media_pool = self.get_files(self.paths['images'])
        if not media_pool: return
        selected = [random.choice(media_pool), random.choice(media_pool)]
        monitors = self._get_monitors_safe()
        scale = self.settings.get('image_scale', 1.0)
        threading.Thread(target=self._background_loader, args=(selected, None, is_startle, True, monitors, scale),
                         daemon=True).start()

    def _is_overlapping(self, x, y, w, h, current_rects):
        for r in current_rects:
            dx = min(x + w, r['x'] + r['w']) - max(x, r['x'])
            dy = min(y + h, r['y'] + r['h']) - max(y, r['y'])
            if (dx >= 0) and (dy >= 0):
                if (dx * dy) > (w * h * 0.3): return True
        return False

    def _calculate_geometry(self, orig_w, orig_h, monitor, is_startle, scale):
        base_w, base_h = monitor['width'] * 0.4, monitor['height'] * 0.4
        ratio = min(base_w / orig_w, base_h / orig_h) * scale
        tgt_w, tgt_h = int(orig_w * ratio), int(orig_h * ratio)
        win_w, win_h = tgt_w, tgt_h
        win_x = monitor['x'] + random.randint(0, max(0, monitor['width'] - win_w))
        win_y = monitor['y'] + random.randint(0, max(0, monitor['height'] - win_h))
        return win_x, win_y, win_w, win_h, tgt_w, tgt_h

    def _background_loader(self, media_paths, sound_path, is_startle, is_multiplication, monitors, scale):
        if not self.running: return
        try:
            processed_data = []
            for i, path in enumerate(media_paths):
                raw_frames, delay = self._load_raw_frames(path)
                if not raw_frames: continue
                target_mon = random.choice(monitors)
                wx, wy, ww, wh, tw, th = self._calculate_geometry(raw_frames[0].size[0], raw_frames[0].size[1],
                                                                  target_mon, is_startle, scale)
                resized = [rf.resize((max(1, tw), max(1, th)), Image.Resampling.LANCZOS) for rf in raw_frames]
                processed_data.append(
                    {'frames': resized, 'delay': delay, 'x': wx, 'y': wy, 'w': ww, 'h': wh, 'monitor': target_mon,
                     'is_startle': is_startle})
            payload = {"processed_data": processed_data, "sec_data": None, "sound_path": sound_path,
                       "is_multiplication": is_multiplication}
            self.root.after(0, lambda: self._finalize_show_images(payload))
        except:
            if not is_multiplication: self.root.after(0, lambda: self.busy.__setattr__('busy', False))

    def _load_raw_frames(self, path):
        pil_images = [];
        delay = 0.033
        try:
            frames_iter = iio.imiter(path)
            try:
                meta = iio.immeta(path);
                duration = meta.get('duration', 0)
                if duration > 0: delay = duration / 1000.0; delay = max(delay, 0.04)
            except:
                pass
            raw_frames = []
            for i, frame in enumerate(frames_iter):
                if i > 60: break
                raw_frames.append(frame)
            step = 1
            if len(raw_frames) > 60: step = len(raw_frames) // 60; delay *= step
            for i in range(0, len(raw_frames), step): pil_images.append(Image.fromarray(raw_frames[i]))
        except:
            try:
                pil_images.append(Image.open(path))
            except:
                pass
        return pil_images, delay

    def _finalize_show_images(self, data):
        if not self.running:
            if not data['is_multiplication']: self.busy = False
            return
        duration = 5.0
        if data['sound_path']:
            self._do_duck()
            self._duck_subliminal_channel(True)
            try:
                if data.get('processed_data') and data['processed_data'][0]['is_startle']:
                    threading.Thread(target=self._delayed_audio_start, args=(data['sound_path'],)).start()
                else:
                    effect = pygame.mixer.Sound(data['sound_path']);
                    vol = self.settings.get('volume', 1.0);
                    curved_vol = vol ** 2
                    effect.set_volume(curved_vol)
                    duration = effect.get_length()
                    effect.play()
                    self._add_xp(2)
                    self.root.after(int(duration * 1000) + 1500, self.ducker.unduck)
                    self.root.after(int(duration * 1000) + 500, lambda: self._duck_subliminal_channel(False))
            except Exception:
                self.ducker.unduck()
                self._duck_subliminal_channel(False)
        self.virtual_end_time = time.time() + duration
        if not data['processed_data']:
            if not data['is_multiplication']: self.busy = False
            return
        for i, item in enumerate(data['processed_data']):
            delay_ms = 0 if item['is_startle'] else (i * 100 if data['is_multiplication'] else i * 500)

            def spawn_later(it=item):
                final_x, final_y = it['x'], it['y']
                mon = it['monitor']
                max_x, max_y = mon['width'] - it['w'], mon['height'] - it['h']
                for _ in range(10):
                    if not self._is_overlapping(final_x, final_y, it['w'], it['h'], self.active_rects): break
                    final_x = mon['x'] + random.randint(0, max(0, max_x))
                    final_y = mon['y'] + random.randint(0, max(0, max_y))
                self._spawn_window_final(final_x, final_y, it['w'], it['h'],
                                         [ImageTk.PhotoImage(img) for img in it['frames']], it['delay'], False, False)

            self.root.after(delay_ms, spawn_later)
        if not data['is_multiplication']: self.busy = False

    def _delayed_audio_start(self, sound_path):
        time.sleep(2.0)
        if self.running:
            try:
                effect = pygame.mixer.Sound(sound_path);
                vol = self.settings.get('volume', 1.0);
                curved_vol = vol ** 2
                effect.set_volume(curved_vol)
                effect.play();
                duration = effect.get_length()
                self.root.after(int(duration * 1000) + 1500, self.ducker.unduck)
            except:
                self.root.after(0, self.ducker.unduck)

    def _spawn_window_final(self, x, y, w, h, tk_frames, delay, is_startle, is_secondary):
        if not self.running: return
        win = tk.Toplevel(self.root)
        win.overrideredirect(True);
        win.attributes('-topmost', True);
        win.config(bg='black')
        win.geometry(f"{w}x{h}+{x}+{y}");
        win.attributes('-alpha', 0.0)
        self._apply_window_lock(win, False)
        if self.settings.get('flash_clickable', True):
            win.config(cursor="hand2")
        else:
            win.config(cursor="X_cursor")
        self._add_xp(1)
        lbl = tk.Label(win, bg='black', bd=0);
        lbl.pack(expand=True, fill='both')
        lbl.bind('<Button-1>', lambda e: self.on_image_click(win, False, None))
        win.frames = tk_frames;
        win.frame_delay = delay;
        win.start_time = time.time()
        self.active_windows.append(win);
        self.active_rects.append({'win': win, 'x': x, 'y': y, 'w': w, 'h': h})

    def _add_xp(self, base_points, is_video_context=False):
        multiplier = 1.0
        if self.settings.get('disable_panic_esc', False): multiplier *= 2.0
        if is_video_context and self.settings.get('startle_strict', False): multiplier *= 2.0
        points_to_add = base_points * multiplier
        self.settings['player_xp'] += points_to_add
        self._check_level_up()
        self._update_ui_xp()

    def _check_level_up(self):
        current_xp = self.settings.get('player_xp', 0.0)
        current_level = self.settings.get('player_level', 1)
        xp_needed = 500.0 * (current_level ** 1.5)
        while current_xp >= xp_needed:
            current_xp -= xp_needed
            current_level += 1
            xp_needed = 500.0 * (current_level ** 1.5)
        self.settings['player_xp'] = current_xp
        self.settings['player_level'] = current_level

    def _update_ui_xp(self):
        if self.xp_update_callback:
            lvl = self.settings.get('player_level', 1)
            xp = self.settings.get('player_xp', 0.0)
            req = 500.0 * (lvl ** 1.5)
            progress = xp / req
            self.xp_update_callback(lvl, progress, xp, req)

    def heartbeat(self):
        now = time.time()
        dt = now - self.last_heartbeat_time
        self.last_heartbeat_time = now
        if self.running and self.settings.get('bg_audio_enabled'):
            self.bg_audio_accumulator += dt
            if self.bg_audio_accumulator >= 120.0:
                self.bg_audio_accumulator -= 120.0
                self._add_xp(1)
        try:
            self._update_scheduler_progress()
        except:
            pass
        if self.video_running: self.root.after(100, self.heartbeat); return
        max_alpha = self.get_effective_value('image_alpha', self.settings.get('image_alpha', 1.0))
        max_alpha = min(1.0, max(0.0, max_alpha))
        show_images = time.time() < self.virtual_end_time
        target_alpha_val = max_alpha if show_images else 0.0
        if not show_images and not self.active_windows:
            self.active_rects.clear()
            if self.events_pending_reschedule:
                for ev in list(self.events_pending_reschedule): self.schedule_next(ev)
                self.events_pending_reschedule.clear()
        for win in self.active_windows[:]:
            if not win.winfo_exists(): self.active_windows.remove(win); continue
            if hasattr(win, 'is_locked_spot'): continue
            try:
                cur = win.attributes('-alpha')
                if target_alpha_val > cur:
                    win.attributes('-alpha', min(target_alpha_val, cur + 0.08))
                elif target_alpha_val < cur:
                    new_a = max(0.0, cur - 0.08);
                    win.attributes('-alpha', new_a)
                    if new_a == 0.0: win.destroy(); self.active_windows.remove(win); self.active_rects = [r for r in
                                                                                                          self.active_rects
                                                                                                          if r[
                                                                                                              'win'] != win]
            except:
                pass
            if hasattr(win, 'frames') and len(win.frames) > 1:
                now = time.time();
                idx = int((now - win.start_time) / win.frame_delay) % len(win.frames)
                try:
                    win.winfo_children()[0].configure(image=win.frames[idx])
                except:
                    pass
        self.root.after(33, self.heartbeat)


# --- THE GUI ---
class ControlPanel:
    def __init__(self, root):
        self.root = root
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        self.root.title("Conditioning Control Panel - by CodeBambi")
        self.root.geometry("1150x950")
        self.root.configure(fg_color=THEME["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.root.after(10, self._apply_title_bar_color)
        self.icon = None
        if TRAY_AVAILABLE: self.create_tray_icon()
        self.presets = self.load_presets()
        self.settings = self.load_settings()

        # <--- CRITICAL FIX: PRESERVE XP START --->
        # We save the XP loaded from settings.json so the Preset doesn't kill it.
        saved_xp = self.settings.get('player_xp', 0.0)
        saved_lvl = self.settings.get('player_level', 1)
        # <--- CRITICAL FIX END --->

        self.day_buttons = []

        # Initialize Engine
        self.engine = FlasherEngine(self.root, self.restore_gui)
        self.engine.set_gui_callback(self.update_audio_ui)
        self.engine.set_scheduler_callback(self.update_scheduler_ui)
        self.engine.set_xp_callback(self.update_xp_ui)

        # UI Building
        self.build_ui()

        # Apply Settings
        self.apply_settings_to_ui(self.settings)
        last_preset_name = self.settings.get('last_preset', 'DEFAULT')
        if last_preset_name in self.presets:
            self.settings.update(self.presets[last_preset_name])

            # <--- CRITICAL FIX: RESTORE XP START --->
            # We put the real XP back after the preset tried to overwrite it.
            self.settings['player_xp'] = saved_xp
            self.settings['player_level'] = saved_lvl
            # <--- CRITICAL FIX END --->

            self.apply_settings_to_ui(self.settings)
            self.preset_menu.set(last_preset_name)

        self.engine.update_settings(self.settings)

        # Initial XP UI update
        lvl = self.settings.get('player_level', 1)
        xp = self.settings.get('player_xp', 0.0)
        req = 500.0 * (lvl ** 1.5)
        self.update_xp_ui(lvl, xp / req, xp, req)

        # Startup Logic
        if self.settings.get('start_minimized', False):
            if TRAY_AVAILABLE:
                self.root.withdraw()
            else:
                self.root.iconify()
        for path in self.engine.paths.values(): os.makedirs(path, exist_ok=True)

        # Launch Browser Embedded (Always on)
        self.root.after(1000, self._init_embedded_browser)

        if self.settings.get('force_startle_on_launch') or self.settings.get('auto_start_engine'):
            self.root.after(1500, lambda: self.btn_toggle.configure(text="STOP", fg_color=THEME["warning"],
                                                                    hover_color="#B71C1C"))
            self.engine.start(is_startup=True)

    def _init_embedded_browser(self):
        if hasattr(self, 'browser_container') and self.browser_container.winfo_exists():
            self.engine.browser.launch_embedded(self.browser_container)

    def create_tray_icon(self):
        image = Image.new('RGB', (64, 64), color=(255, 105, 180))
        d = ImageDraw.Draw(image)
        d.rectangle([16, 16, 48, 48], fill=(255, 255, 255))
        menu = (item('Show Control Panel', self.restore_gui), item('Exit', self.quit_app))
        self.icon = pystray.Icon("ConditioningApp", image, "Conditioning App", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def _apply_title_bar_color(self):
        try:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.windll.user32.GetParent(self.root.winfo_id()), 35,
                                                       ctypes.byref(ctypes.c_int(0x00B469FF)), 4)
        except:
            pass

    def minimize_to_tray(self):
        if TRAY_AVAILABLE:
            self.root.withdraw()
        else:
            self.root.iconify()

    def restore_gui(self, icon=None, item=None):
        self.root.deiconify();
        self.root.lift()
        if self.engine.running:
            self.btn_toggle.configure(text="STOP", fg_color=THEME["warning"], hover_color="#B71C1C")
        else:
            self.btn_toggle.configure(text="DROP", fg_color=THEME["btn_bg"], hover_color=THEME["btn_hover"])
        # Re-check browser resize on restore
        self.engine.browser.resize_to_container()

    def quit_app(self, icon=None, item=None):
        self.engine.panic_stop()
        self.engine.esc_listener_active = False
        self.engine.browser.close()
        self.save_settings()
        if self.icon: self.icon.stop()
        self.root.destroy();
        try:
            os._exit(0)
        except:
            pass

    def load_presets(self):
        presets = {"DEFAULT": DEFAULT_SETTINGS.copy()}
        if os.path.exists(PRESETS_FILE):
            try:
                with open(PRESETS_FILE, 'r') as f:
                    loaded = json.load(f);
                    presets.update(loaded)
            except:
                pass
        return presets

    def load_settings(self):
        settings = DEFAULT_SETTINGS.copy()
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    saved = json.load(f);
                    settings.update(saved)
            except:
                pass
        if 'subliminal_pool' not in settings or not settings['subliminal_pool']: settings[
            'subliminal_pool'] = BAMBI_POOL_DICT.copy()
        if 'attention_pool' not in settings or not settings['attention_pool']: settings[
            'attention_pool'] = BAMBI_POOL_DICT.copy()
        return settings

    def check_danger_toggle(self, switch_widget, name):
        if switch_widget.get() == 1:
            if not messagebox.askyesno(f"Enable {name}?",
                                       "⚠️ DANGER: SELF-LOCKING RISK ⚠️\n\nThis can lock you out until reboot.",
                                       icon='warning'):
                switch_widget.deselect();
                return
            if not messagebox.askyesno(f"Confirm {name}",
                                       "⛔ FINAL CONFIRMATION ⛔\n\nThere may be NO ESCAPE KEY if you proceed.",
                                       icon='error'):
                switch_widget.deselect();
                return
        self._notify_engine_live()

    def get_current_ui_values(self):
        active_days = [i for i, btn in enumerate(self.day_buttons) if btn._fg_color == THEME["btn_bg"]]

        # --- CRITICAL FIX: PULL LIVE XP FROM ENGINE ---
        # If we don't do this, it saves the XP you had when you OPENED the app,
        # ignoring everything you earned during the session.
        if hasattr(self, 'engine'):
            current_lvl = self.engine.settings.get('player_level', 1)
            current_xp = self.engine.settings.get('player_xp', 0.0)
        else:
            current_lvl = self.settings.get('player_level', 1)
            current_xp = self.settings.get('player_xp', 0.0)
        # -----------------------------------------------

        try:
            min_i = int(self.entry_min.get())
        except:
            min_i = 3
        try:
            max_i = int(self.entry_max.get())
        except:
            max_i = 10
        try:
            fade = float(self.entry_fade.get())
        except:
            fade = 0.5

        return {
            "player_level": current_lvl,  # Uses the LIVE level
            "player_xp": current_xp,  # Uses the LIVE XP
            "flash_enabled": self.sw_flash.get(),
            "min_interval": min_i, "max_interval": max_i,
            "flash_clickable": self.sw_clickable.get(),
            "flash_hydra_limit": int(self.slider_hydra.get()),
            "startle_enabled": self.sw_startle.get(), "startle_freq": int(self.slider_s_freq.get()),
            "startle_strict": self.sw_s_strict.get(),
            "subliminal_enabled": self.sw_sub.get(), "subliminal_freq": int(self.slider_sub_freq.get()),
            "subliminal_duration": int(self.slider_sub_dur.get()), "subliminal_pool": self.settings['subliminal_pool'],
            "subliminal_opacity": float(self.slider_sub_op.get()) / 100.0,
            "sub_bg_color": self.settings.get("sub_bg_color", "#000000"),
            "sub_bg_transparent": self.settings.get("sub_bg_transparent", False),
            "sub_text_color": self.settings.get("sub_text_color", "#FF00FF"),
            "sub_text_transparent": self.settings.get("sub_text_transparent", False),
            "sub_border_color": self.settings.get("sub_border_color", "#FFFFFF"),
            "sub_audio_enabled": self.sw_sub_aud.get(),
            "sub_audio_volume": float(self.slider_sub_vol.get()) / 100.0,
            "bg_audio_enabled": self.sw_bg_audio.get(),
            "bg_audio_max": 15,
            "fade_duration": fade, "volume": float(self.slider_vol.get()) / 100.0,
            "audio_ducking_enabled": self.sw_ducking.get(),
            "audio_ducking_strength": int(self.slider_ducking.get()),
            "dual_monitor": self.sw_dual.get(), "sim_min": int(self.slider_sim_min.get()),
            "sim_max": int(self.slider_sim_max.get()), "image_scale": float(self.slider_scale.get()) / 100.0,
            "image_alpha": float(self.slider_alpha.get()) / 100.0,
            "run_on_startup": self.sw_startup.get(),
            "force_startle_on_launch": self.sw_force.get(), "start_minimized": self.sw_min_start.get(),
            "auto_start_engine": self.sw_auto_start.get(), "last_preset": self.preset_menu.get(),
            "disable_panic_esc": self.sw_no_panic.get(),
            "attention_enabled": self.sw_attention.get(), "attention_pool": self.settings['attention_pool'],
            "attention_density": int(self.slider_attn_dens.get()),
            "attention_lifespan": int(self.slider_attn_life.get()),
            "attention_size": int(self.slider_attn_size.get()),
            "scheduler_enabled": self.sw_sched.get(), "scheduler_duration_min": int(self.slider_sched_dur.get()),
            "scheduler_multiplier": float(self.slider_sched_mult.get()),
            "scheduler_link_alpha": self.sw_link_alpha.get(),
            "time_schedule_enabled": self.sw_time_sched.get(),
            "time_start_str": self.entry_start_time.get(), "time_end_str": self.entry_end_time.get(),
            "active_weekdays": active_days
        }
    def _notify_engine_live(self, event=None):
        s = self.get_current_ui_values()
        self.settings = s
        self.engine.update_settings(s)

    def open_style_editor(self):
        dia = ctk.CTkToplevel(self.root)
        dia.title("Subliminal Styles")
        dia.geometry("300x400")
        dia.attributes('-topmost', True)

        def pick_color(key):
            color = colorchooser.askcolor(title="Choose Color")[1]
            if color:
                self.settings[key] = color
                self._notify_engine_live()

        def toggle_trans(key, var):
            self.settings[key] = bool(var.get())
            self._notify_engine_live()

        ctk.CTkLabel(dia, text="Background", font=("Arial", 14, "bold")).pack(pady=10)
        ctk.CTkButton(dia, text="Pick BG Color", command=lambda: pick_color("sub_bg_color")).pack(pady=5)
        bg_var = ctk.BooleanVar(value=self.settings.get("sub_bg_transparent", False))
        ctk.CTkCheckBox(dia, text="Transparent BG", variable=bg_var,
                        command=lambda: toggle_trans("sub_bg_transparent", bg_var)).pack(pady=5)
        ctk.CTkLabel(dia, text="Text Fill", font=("Arial", 14, "bold")).pack(pady=10)
        ctk.CTkButton(dia, text="Pick Text Color", command=lambda: pick_color("sub_text_color")).pack(pady=5)
        txt_var = ctk.BooleanVar(value=self.settings.get("sub_text_transparent", False))
        ctk.CTkCheckBox(dia, text="Transparent Text (Stroke Only)", variable=txt_var,
                        command=lambda: toggle_trans("sub_text_transparent", txt_var)).pack(pady=5)
        ctk.CTkLabel(dia, text="Stroke / Border", font=("Arial", 14, "bold")).pack(pady=10)
        ctk.CTkButton(dia, text="Pick Border Color", command=lambda: pick_color("sub_border_color")).pack(pady=5)
        ctk.CTkButton(dia, text="Close", fg_color="gray", command=dia.destroy).pack(pady=20)

    def open_sub_manager(self):
        TextManagerDialog(self.root, "Subliminals", self.settings['subliminal_pool'], self._notify_engine_live)

    def open_attn_manager(self):
        TextManagerDialog(self.root, "Attention Targets", self.settings['attention_pool'], self._notify_engine_live)

    def apply_settings_to_ui(self, s):
        def set_sw(sw, val):
            sw.select() if val else sw.deselect()

        set_sw(self.sw_flash, s.get('flash_enabled', True))
        self.entry_min.delete(0, 'end');
        self.entry_min.insert(0, s.get('min_interval', 3))
        self.entry_max.delete(0, 'end');
        self.entry_max.insert(0, s.get('max_interval', 10))
        set_sw(self.sw_clickable, s.get('flash_clickable', True))

        def set_slide(slider, label, val, fmt="{:.0f}"):
            slider.set(val)
            label.configure(text=fmt.format(val))

        set_slide(self.slider_hydra, self.lbl_hydra, s.get('flash_hydra_limit', 30))
        set_sw(self.sw_startle, s.get('startle_enabled'))
        set_slide(self.slider_s_freq, self.lbl_s_freq, s.get('startle_freq', 10))
        set_sw(self.sw_s_strict, s.get('startle_strict'))
        set_sw(self.sw_sub, s.get('subliminal_enabled'))
        set_slide(self.slider_sub_freq, self.lbl_sub_freq, s.get('subliminal_freq', 10))
        set_slide(self.slider_sub_dur, self.lbl_sub_dur, s.get('subliminal_duration', 1))
        set_slide(self.slider_sub_op, self.lbl_sub_op, s.get('subliminal_opacity', 0.8) * 100, "{:.0f}%")
        set_sw(self.sw_sub_aud, s.get('sub_audio_enabled', False))
        set_slide(self.slider_sub_vol, self.lbl_sub_vol, s.get('sub_audio_volume', 0.5) * 100, "{:.0f}%")
        set_sw(self.sw_bg_audio, s.get('bg_audio_enabled'))
        self.entry_fade.delete(0, 'end');
        self.entry_fade.insert(0, s.get('fade_duration', 0.5))
        set_slide(self.slider_vol, self.lbl_vol_val, s.get('volume', 1.0) * 100, "{:.0f}%")
        set_sw(self.sw_ducking, s.get('audio_ducking_enabled', True))
        set_slide(self.slider_ducking, self.lbl_ducking, s.get('audio_ducking_strength', 100), "{:.0f}%")
        set_sw(self.sw_dual, s.get('dual_monitor'))
        set_slide(self.slider_sim_min, self.lbl_sim_min, s.get('sim_min', 1))
        set_slide(self.slider_sim_max, self.lbl_sim_max, s.get('sim_max', 3))
        set_slide(self.slider_scale, self.lbl_scale, s.get('image_scale', 1.0) * 100, "{:.0f}%")
        set_slide(self.slider_alpha, self.lbl_alpha, s.get('image_alpha', 1.0) * 100, "{:.0f}%")
        set_sw(self.sw_startup, s.get('run_on_startup'))
        set_sw(self.sw_force, s.get('force_startle_on_launch'))
        set_sw(self.sw_auto_start, s.get('auto_start_engine'))
        set_sw(self.sw_min_start, s.get('start_minimized'))
        set_sw(self.sw_no_panic, s.get('disable_panic_esc'))
        set_sw(self.sw_attention, s.get('attention_enabled'))
        set_slide(self.slider_attn_dens, self.lbl_attn_dens, s.get('attention_density', 2))
        set_slide(self.slider_attn_life, self.lbl_attn_life, s.get('attention_lifespan', 4))
        set_slide(self.slider_attn_size, self.lbl_attn_size, s.get('attention_size', 40))
        set_sw(self.sw_sched, s.get('scheduler_enabled'))
        set_slide(self.slider_sched_dur, self.lbl_sched_dur, s.get('scheduler_duration_min', 60))
        set_slide(self.slider_sched_mult, self.lbl_sched_mult, s.get('scheduler_multiplier', 1.0), "{:.1f}x")
        set_sw(self.sw_link_alpha, s.get('scheduler_link_alpha'))
        set_sw(self.sw_time_sched, s.get('time_schedule_enabled'))
        self.entry_start_time.delete(0, 'end');
        self.entry_start_time.insert(0, s.get('time_start_str', "16:00"))
        self.entry_end_time.delete(0, 'end');
        self.entry_end_time.insert(0, s.get('time_end_str', "18:00"))
        active_days = s.get('active_weekdays', [0, 1, 2, 3, 4, 5, 6])
        for i, btn in enumerate(self.day_buttons):
            if i in active_days:
                btn.configure(fg_color=THEME["btn_bg"], text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=THEME["fg"])

    def save_settings(self):
        try:
            s = self.get_current_ui_values()
            current_preset = self.preset_menu.get()
            if current_preset == "DEFAULT":
                if messagebox.askyesno("Save Preset", "Create a NEW preset?"):
                    new_name = simpledialog.askstring("New Preset", "Enter Preset Name:")
                    if new_name:
                        if new_name in self.presets:
                            if not messagebox.askyesno("Overwrite?", f"'{new_name}' exists. Overwrite?"): return
                        self.presets[new_name] = s
                        current_preset = new_name
                        self.update_preset_menu()
                        self.preset_menu.set(new_name)
                    else:
                        return
                else:
                    pass
            elif current_preset != "Save New Preset...":
                self.presets[current_preset] = s

            try:
                with open(PRESETS_FILE, 'w') as f:
                    json.dump(self.presets, f)
            except Exception as e:
                print(f"Error saving presets: {e}")

            s['last_preset'] = current_preset
            self.settings = s
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(s, f)
            self.toggle_windows_startup(s['run_on_startup'])
            self.engine.update_settings(s)
            messagebox.showinfo("Saved", f"Configuration saved.\nPreset: {current_preset}")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers.")

    def reset_defaults(self):
        if messagebox.askyesno("Reset", "Reset all settings to default?"):
            self.apply_settings_to_ui(DEFAULT_SETTINGS)
            self.save_settings()

    def handle_preset_selection(self, choice):
        if choice == "Save New Preset...":
            name = simpledialog.askstring("New Preset", "Enter Preset Name:")
            if name:
                current_config = self.get_current_ui_values()
                self.presets[name] = current_config
                with open(PRESETS_FILE, 'w') as f: json.dump(self.presets, f)
                self.update_preset_menu()
                self.preset_menu.set(name)
        elif choice in self.presets:
            self.apply_settings_to_ui(self.presets[choice])
            self.preset_menu.set(choice)
            self._notify_engine_live()

    def update_preset_menu(self):
        vals = list(self.presets.keys());
        vals.sort();
        vals.append("Save New Preset...")
        self.preset_menu.configure(values=vals)

    def toggle_windows_startup(self, enable):
        try:
            if enable:
                python_exe = sys.executable.replace("python.exe", "pythonw.exe")
                script_dir = os.path.dirname(os.path.abspath(__file__))
                script_path = os.path.abspath(__file__)
                drive = os.path.splitdrive(script_dir)[0]
                bat_content = f'@echo off\n{drive}\ncd "{script_dir}"\nstart "" "{python_exe}" "{script_path}"'
                with open(STARTUP_FILE_PATH, "w") as f:
                    f.write(bat_content)
            else:
                if os.path.exists(STARTUP_FILE_PATH): os.remove(STARTUP_FILE_PATH)
        except:
            pass

    def toggle_engine(self, manual=True):
        if self.engine.running:
            self.engine.stop();
            self.restore_gui()
        else:
            self.engine.start(is_startup=not manual)
            self.btn_toggle.configure(text="STOP", fg_color=THEME["warning"], hover_color="#B71C1C")

    def update_audio_ui(self, progress, elapsed):
        pass

    def update_scheduler_ui(self, progress_percent, multiplier, remaining_sec):
        self.sched_progress.set(progress_percent)
        current_mult = 1.0 + ((multiplier - 1.0) * progress_percent)
        mins = remaining_sec // 60;
        secs = int(remaining_sec % 60)
        self.lbl_sched_status.configure(
            text=f"Current Intensity: {current_mult:.2f}x (Target: {multiplier}x)\nTime Left: {int(mins)}m {secs}s")

    def update_xp_ui(self, level, progress_percent, current_xp, needed_xp):
        # Update the Visuals
        self.lbl_level.configure(text=f"LVL {level}")
        self.xp_bar.set(progress_percent)
        self.lbl_xp_mult.configure(text=f"{int(current_xp)} / {int(needed_xp)} XP")

        # --- FIX: SYNC DATA FOR SAVING ---
        # This ensures get_current_ui_values() grabs the latest XP
        # when the user clicks Save or Exits.
        self.settings['player_level'] = level
        self.settings['player_xp'] = current_xp
    def toggle_day_btn(self, btn):
        if btn._fg_color == THEME["btn_bg"]:
            btn.configure(fg_color="transparent", text_color=THEME["fg"])
        else:
            btn.configure(fg_color=THEME["btn_bg"], text_color="white")
        self._notify_engine_live()

    # --- UI BUILDING HELPERS ---
    def create_card(self, parent, title, row, col, rowspan=1, colspan=1, sticky="nsew"):
        frame = ctk.CTkFrame(parent, corner_radius=15, fg_color=THEME["card_bg"], border_width=1,
                             border_color="#E1BEE7")
        frame.grid(row=row, column=col, rowspan=rowspan, columnspan=colspan, sticky=sticky, padx=8, pady=8)
        header = ctk.CTkLabel(frame, text=title, font=(THEME["font_family"], 16, "bold"), text_color=THEME["fg"])
        header.pack(pady=(10, 5), padx=10, anchor="w")
        return frame

    def add_tooltip_icon(self, parent, text):
        lbl = ctk.CTkLabel(parent, text="(?)", font=(THEME["font_family"], 12, "bold"), text_color=THEME["accent"],
                           cursor="hand2")
        lbl.pack(side="left", padx=(0, 5))
        lbl.tooltip = ToolTip(lbl, text)

    def create_labeled_slider(self, parent, text, min_val, max_val, format_str="{:.0f}"):
        row = ctk.CTkFrame(parent, fg_color="transparent");
        row.pack(fill="x", padx=10, pady=1)
        ctk.CTkLabel(row, text=text, text_color=THEME["fg"], width=80, anchor="w",
                     font=(THEME["font_family"], 12)).pack(side="left")
        val_lbl = ctk.CTkLabel(row, text=format_str.format(min_val), text_color=THEME["fg"], width=35,
                               font=(THEME["font_family"], 12))
        val_lbl.pack(side="right")

        def update_val(val):
            val_lbl.configure(text=format_str.format(val))
            self._notify_engine_live()

        slider = ctk.CTkSlider(row, from_=min_val, to=max_val, button_color=THEME["btn_bg"], command=update_val,
                               height=16)
        slider.pack(side="right", fill="x", expand=True, padx=5)
        return slider, val_lbl

    def switch_view(self, value):
        if value == "Main Settings":
            self.view_scheduler.pack_forget()
            self.view_settings.pack(fill="both", expand=True, padx=10, pady=5)
        else:
            self.view_settings.pack_forget()
            self.view_scheduler.pack(fill="both", expand=True, padx=10, pady=5)

    def build_ui(self):
        header_frame = ctk.CTkFrame(self.root, fg_color=THEME["header_bg"], corner_radius=0, height=80)
        header_frame.pack(fill="x")
        top_header = ctk.CTkFrame(header_frame, fg_color="transparent")
        top_header.pack(fill="x", padx=10, pady=(5, 0))
        ctk.CTkLabel(top_header, text="Conditioning Dashboard 1.3", font=("Segoe UI", 20, "bold"),
                     text_color="white").pack(side="left", padx=10)
        self.preset_menu = ctk.CTkOptionMenu(top_header, values=[], command=self.handle_preset_selection,
                                             fg_color="white", text_color=THEME["fg"], button_color=THEME["btn_bg"],
                                             height=28, width=140)
        self.update_preset_menu()
        self.preset_menu.pack(side="right", padx=10)
        self.preset_menu.set("DEFAULT")
        self.tab_selector = ctk.CTkSegmentedButton(top_header, values=["Main Settings", "Scheduler"],
                                                   command=self.switch_view, selected_color=THEME["btn_bg"],
                                                   selected_hover_color=THEME["btn_hover"], unselected_color="white",
                                                   unselected_hover_color="#EEE", text_color=THEME["fg"])
        self.tab_selector.pack(side="right", padx=20)
        self.tab_selector.set("Main Settings")

        xp_frame = ctk.CTkFrame(header_frame, fg_color=THEME["xp_bg"], height=30)
        xp_frame.pack(fill="x", padx=0, pady=(5, 0), side="bottom")
        self.lbl_level = ctk.CTkLabel(xp_frame, text="LVL 1", text_color=THEME["xp_bar"], font=("Impact", 16))
        self.lbl_level.pack(side="left", padx=15)
        self.xp_bar = ctk.CTkProgressBar(xp_frame, progress_color=THEME["xp_bar"], height=12, corner_radius=0)
        self.xp_bar.pack(side="left", fill="x", expand=True, padx=10)
        self.xp_bar.set(0)
        self.lbl_xp_mult = ctk.CTkLabel(xp_frame, text="0 / 500 XP", text_color="white", font=("Arial", 11, "bold"))
        self.lbl_xp_mult.pack(side="right", padx=15)

        self.content_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True)
        self.view_settings = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.view_scheduler = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.build_settings_tab(self.view_settings)
        self.build_scheduler_tab(self.view_scheduler)
        self.switch_view("Main Settings")

        footer = ctk.CTkFrame(self.root, fg_color="transparent")
        footer.pack(fill="x", side="bottom", pady=10, padx=20)
        self.btn_toggle = ctk.CTkButton(footer, text="DROP", fg_color=THEME["btn_bg"], hover_color=THEME["btn_hover"],
                                        corner_radius=25, height=45, font=("Segoe UI", 18, "bold"),
                                        command=lambda: self.toggle_engine(manual=True))
        self.btn_toggle.pack(fill="x", side="left", expand=True, padx=(0, 10))
        ctk.CTkButton(footer, text="SAVE", fg_color="transparent", border_width=2, border_color=THEME["btn_bg"],
                      text_color=THEME["btn_bg"], width=90, height=45, command=self.save_settings).pack(side="left")
        ctk.CTkButton(footer, text="EXIT", fg_color="transparent", text_color="red", width=70, height=45,
                      command=self.quit_app).pack(side="right")

    def build_settings_tab(self, parent):
        parent.columnconfigure(0, weight=1);
        parent.columnconfigure(1, weight=1);
        parent.columnconfigure(2, weight=1)
        parent.rowconfigure(0, weight=1)

        # --- COL 1: VISUALS ---
        col1 = ctk.CTkFrame(parent, fg_color="transparent");
        col1.grid(row=0, column=0, sticky="nsew", padx=4)
        c_flash = self.create_card(col1, "✨ Flash Images", 0, 0)
        r1 = ctk.CTkFrame(c_flash, fg_color="transparent");
        r1.pack(fill="x", padx=10, pady=2)
        self.add_tooltip_icon(r1, "Enable/Disable rapid flashing of image overlays.")
        self.sw_flash = ctk.CTkSwitch(r1, text="Enable Flashing", font=(THEME["font_family"], 12, "bold"),
                                      text_color=THEME["fg"], progress_color=THEME["accent"],
                                      command=self._notify_engine_live);
        self.sw_flash.pack(side="left")
        r1b = ctk.CTkFrame(c_flash, fg_color="transparent");
        r1b.pack(fill="x", padx=10, pady=2)
        self.add_tooltip_icon(r1b, "OFF = Ghost images (cannot be closed by clicking).")
        self.sw_clickable = ctk.CTkSwitch(r1b, text="Clickable?", font=(THEME["font_family"], 10),
                                          text_color=THEME["fg"], progress_color=THEME["accent"], height=16,
                                          command=self._notify_engine_live);
        self.sw_clickable.pack(side="left")
        r2 = ctk.CTkFrame(c_flash, fg_color="transparent");
        r2.pack(fill="x", padx=10, pady=5)
        self.add_tooltip_icon(r2, "Random delay (in seconds) between image flashes.")
        ctk.CTkLabel(r2, text="Min:", text_color=THEME["fg"]).pack(side="left")
        self.entry_min = ctk.CTkEntry(r2, width=40);
        self.entry_min.pack(side="left", padx=5);
        self.entry_min.bind("<FocusOut>", self._notify_engine_live)
        ctk.CTkLabel(r2, text="Max:", text_color=THEME["fg"]).pack(side="left", padx=(10, 0))
        self.entry_max = ctk.CTkEntry(r2, width=40);
        self.entry_max.pack(side="left", padx=5);
        self.entry_max.bind("<FocusOut>", self._notify_engine_live)
        self.slider_hydra, self.lbl_hydra = self.create_labeled_slider(c_flash, "Max Scrn:", 1, 30)
        self.slider_hydra.tooltip = ToolTip(self.slider_hydra, "Maximum number of images allowed on screen at once.")

        c_vis = self.create_card(col1, "🎨 Visual Parameters", 1, 0)
        self.slider_sim_min, self.lbl_sim_min = self.create_labeled_slider(c_vis, "Min Img:", 1, 20)
        self.slider_sim_max, self.lbl_sim_max = self.create_labeled_slider(c_vis, "Max Img:", 1, 20)
        self.slider_scale, self.lbl_scale = self.create_labeled_slider(c_vis, "Scale:", 50, 250, "{:.0f}%")
        self.slider_alpha, self.lbl_alpha = self.create_labeled_slider(c_vis, "Opacity:", 10, 100, "{:.0f}%")
        r_fade = ctk.CTkFrame(c_vis, fg_color="transparent");
        r_fade.pack(fill="x", padx=10, pady=5)
        self.add_tooltip_icon(r_fade, "How many seconds audio takes to fade in/out.")
        ctk.CTkLabel(r_fade, text="Fade (s):", text_color=THEME["fg"]).pack(side="left")
        self.entry_fade = ctk.CTkEntry(r_fade, width=50);
        self.entry_fade.pack(side="right");
        self.entry_fade.bind("<FocusOut>", self._notify_engine_live)

        # LOGO
        col1.rowconfigure(2, weight=1)
        c_logo_left = ctk.CTkFrame(col1, fg_color="transparent", border_width=0, corner_radius=0)
        c_logo_left.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        c_logo_left.grid_columnconfigure(0, weight=1);
        c_logo_left.grid_rowconfigure(0, weight=1)
        logo_path = os.path.join(ASSETS_DIR, "Conditioning Control Panel.png")
        if not os.path.exists(logo_path): logo_path = os.path.join(BASE_DIR, "Conditioning Control Panel.png")
        if os.path.exists(logo_path):
            try:
                pil_img = Image.open(logo_path)
                w, h = pil_img.size;
                aspect = w / h;
                target_w = 400;
                target_h = int(target_w / aspect)
                pil_img = pil_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                img_obj = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_w, target_h))
                ctk.CTkLabel(c_logo_left, text="", image=img_obj).grid(row=0, column=0)
            except Exception:
                ctk.CTkLabel(c_logo_left, text="LOGO ERROR", font=("Arial", 12), text_color="red").grid(row=0, column=0)
        else:
            ctk.CTkLabel(c_logo_left, text="LOGO NOT FOUND", font=("Arial", 12), text_color="gray").grid(row=0,
                                                                                                         column=0)

        # --- COL 2: EVENTS & SYSTEM ---
        col2 = ctk.CTkFrame(parent, fg_color="transparent");
        col2.grid(row=0, column=1, sticky="nsew", padx=4)
        col2.rowconfigure(2, weight=0)

        # Startle
        c_startle = self.create_card(col2, "👻 Mandatory Video", 0, 0)
        r_st = ctk.CTkFrame(c_startle, fg_color="transparent");
        r_st.pack(fill="x", padx=10)
        self.add_tooltip_icon(r_st, "Play a full-screen, unskippable video interruption periodically.")
        self.sw_startle = ctk.CTkSwitch(r_st, text="Enable", font=(THEME["font_family"], 12, "bold"),
                                        text_color=THEME["fg"], progress_color=THEME["accent"],
                                        command=self._notify_engine_live);
        self.sw_startle.pack(side="left")
        test_btn = ctk.CTkButton(r_st, text="Test", height=20, width=50, fg_color=THEME["warning"],
                                 command=lambda: self.engine.trigger_event("startle", strict_override=False))
        test_btn.pack(side="right");
        test_btn.tooltip = ToolTip(test_btn, "Test the video player now.")
        self.slider_s_freq, self.lbl_s_freq = self.create_labeled_slider(c_startle, "Freq/Hr:", 1, 60)
        r_strict = ctk.CTkFrame(c_startle, fg_color="transparent");
        r_strict.pack(fill="x", padx=10, pady=5)
        self.sw_s_strict = ctk.CTkSwitch(r_strict, text="Strict Lock (Danger)", text_color=THEME["warning"],
                                         progress_color=THEME["warning"],
                                         command=lambda: self.check_danger_toggle(self.sw_s_strict, "Strict Lock"));
        self.sw_s_strict.pack(side="left")
        c_attn = ctk.CTkFrame(c_startle, fg_color="transparent");
        c_attn.pack(fill="x", pady=5)
        ctk.CTkLabel(c_attn, text="--- Mini-Game ---", font=(THEME["font_family"], 10, "bold"),
                     text_color="gray").pack()
        self.sw_attention = ctk.CTkSwitch(c_attn, text="Enable Checks", text_color=THEME["fg"],
                                          command=self._notify_engine_live);
        self.sw_attention.pack()
        self.slider_attn_dens, self.lbl_attn_dens = self.create_labeled_slider(c_attn, "Targets:", 1, 60)
        self.slider_attn_life, self.lbl_attn_life = self.create_labeled_slider(c_attn, "Time(s):", 2, 10)
        self.slider_attn_size, self.lbl_attn_size = self.create_labeled_slider(c_attn, "Size:", 20, 100)
        self.btn_attn = ctk.CTkButton(c_attn, text="Manage List...", fg_color=THEME["btn_bg"], height=24,
                                      command=self.open_attn_manager)
        self.btn_attn.pack(pady=5)

        # Subliminals
        c_sub = self.create_card(col2, "🧠 Subliminals", 1, 0)
        r_sub = ctk.CTkFrame(c_sub, fg_color="transparent");
        r_sub.pack(fill="x", padx=10)
        self.sw_sub = ctk.CTkSwitch(r_sub, text="Enable", text_color=THEME["fg"], progress_color=THEME["accent"],
                                    command=self._notify_engine_live);
        self.sw_sub.pack(side="left")
        style_btn = ctk.CTkButton(r_sub, text="🎨 Styles", width=60, height=20, fg_color=THEME["accent"],
                                  command=self.open_style_editor)
        style_btn.pack(side="right", padx=5)
        self.slider_sub_freq, self.lbl_sub_freq = self.create_labeled_slider(c_sub, "Freq/Min:", 1, 60)
        self.slider_sub_dur, self.lbl_sub_dur = self.create_labeled_slider(c_sub, "Dur(F):", 1, 10)
        self.slider_sub_op, self.lbl_sub_op = self.create_labeled_slider(c_sub, "Opacity:", 10, 100, "{:.0f}%")
        self.btn_sub = ctk.CTkButton(c_sub, text="Manage List...", fg_color=THEME["btn_bg"], height=24,
                                     command=self.open_sub_manager)
        self.btn_sub.pack(pady=5)
        c_sub_aud = ctk.CTkFrame(c_sub, fg_color="transparent");
        c_sub_aud.pack(fill="x", pady=5)
        ctk.CTkLabel(c_sub_aud, text="--- Audio Triggers ---", font=(THEME["font_family"], 10, "bold"),
                     text_color="gray").pack()
        self.sw_sub_aud = ctk.CTkSwitch(c_sub_aud, text="Enable Audio", text_color=THEME["fg"],
                                        command=self._notify_engine_live);
        self.sw_sub_aud.pack()
        self.slider_sub_vol, self.lbl_sub_vol = self.create_labeled_slider(c_sub_aud, "Vol:", 0, 100, "{:.0f}%")

        # System Card (Moved to Col 2)
        c_sys = self.create_card(col2, "⚙️ System", 2, 0)
        sys_grid_frame = ctk.CTkFrame(c_sys, fg_color="transparent")
        sys_grid_frame.pack(fill="both", expand=True, padx=5, pady=5)

        def add_sys_sw(txt, var, tooltip, r, c):
            f = ctk.CTkFrame(sys_grid_frame, fg_color="transparent");
            f.grid(row=r, column=c, sticky="w", padx=5, pady=2)
            self.add_tooltip_icon(f, tooltip)
            s = ctk.CTkSwitch(f, text=txt, text_color=THEME["fg"], font=(THEME["font_family"], 11), width=100,
                              height=20, command=self._notify_engine_live)
            s.pack(side="left");
            return s

        self.sw_dual = add_sys_sw("Dual Mon", None, "Span effects across all monitors.", 0, 0)
        if not SCREENINFO_AVAILABLE: self.sw_dual.configure(state="disabled")
        self.sw_startup = add_sys_sw("Startup", None, "Run automatically when you log in to Windows.", 0, 1)
        self.sw_startup.configure(command=lambda: self.check_danger_toggle(self.sw_startup, "Startup"))
        self.sw_force = add_sys_sw("Force Vid", None, "Play the video immediately when the app launches.", 1, 0)
        self.sw_auto_start = add_sys_sw("Auto Start", None, "Start the conditioning engine automatically on launch.", 1,
                                        1)
        self.sw_min_start = add_sys_sw("Minimized", None, "Start hidden in the System Tray.", 2, 0)
        self.sw_no_panic = add_sys_sw("No Panic", None, "Disable the ESC key safety kill switch. DANGEROUS.", 2, 1)
        self.sw_no_panic.configure(command=lambda: self.check_danger_toggle(self.sw_no_panic, "Disable Panic"))

        # --- COL 3: AUDIO & BROWSER ---
        col3 = ctk.CTkFrame(parent, fg_color="transparent");
        col3.grid(row=0, column=2, sticky="nsew", padx=4)
        col3.rowconfigure(1, weight=1)

        c_audio = self.create_card(col3, "☁️ Bambi Cloud / Audio", 0, 0)
        r_aud = ctk.CTkFrame(c_audio, fg_color="transparent");
        r_aud.pack(fill="x", padx=10)
        self.sw_bg_audio = ctk.CTkSwitch(r_aud, text="Enable Cloud", text_color=THEME["fg"],
                                         progress_color=THEME["accent"], command=self._notify_engine_live);
        self.sw_bg_audio.pack(side="left")
        r_duck = ctk.CTkFrame(c_audio, fg_color="transparent");
        r_duck.pack(fill="x", padx=10, pady=5)
        self.sw_ducking = ctk.CTkSwitch(r_duck, text="Audio Ducking", text_color=THEME["fg"],
                                        progress_color=THEME["accent"], font=("Segoe UI", 11), height=20,
                                        command=self._notify_engine_live);
        self.sw_ducking.pack(side="left")
        self.slider_ducking, self.lbl_ducking = self.create_labeled_slider(c_audio, "Duck Lvl:", 0, 100, "{:.0f}%")
        ctk.CTkLabel(c_audio, text="App Volume (Sound FX)", text_color=THEME["fg_sub"], font=("Arial", 10)).pack(
            pady=(10, 0))
        self.slider_vol, self.lbl_vol_val = self.create_labeled_slider(c_audio, "Master:", 0, 100, "{:.0f}%")

        # Browser Container (Replaces old System slot)
        self.browser_container = ctk.CTkFrame(col3, fg_color="white", corner_radius=15, border_width=2,
                                              border_color="#E1BEE7")
        self.browser_container.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        # Loading Placeholder
        ctk.CTkLabel(self.browser_container, text="Loading Bambi Cloud...", text_color="gray").place(relx=0.5, rely=0.5,
                                                                                                     anchor="center")

    def build_scheduler_tab(self, parent):
        parent.columnconfigure(0, weight=1);
        parent.columnconfigure(1, weight=1)
        c_ramp = self.create_card(parent, "📈 Intensity Ramping", 0, 0)
        r1 = ctk.CTkFrame(c_ramp, fg_color="transparent");
        r1.pack(fill="x", padx=10)
        self.sw_sched = ctk.CTkSwitch(r1, text="Enable Ramping", text_color=THEME["fg"], progress_color=THEME["accent"],
                                      command=self._notify_engine_live);
        self.sw_sched.pack(side="left")
        self.slider_sched_dur, self.lbl_sched_dur = self.create_labeled_slider(c_ramp, "Duration(m):", 1, 300)
        self.slider_sched_mult, self.lbl_sched_mult = self.create_labeled_slider(c_ramp, "Max Int:", 1.0, 3.0,
                                                                                 "{:.1f}x")
        r4 = ctk.CTkFrame(c_ramp, fg_color="transparent");
        r4.pack(fill="x", padx=10, pady=5)
        self.sw_link_alpha = ctk.CTkSwitch(r4, text="Link Opacity", text_color=THEME["fg"],
                                           progress_color=THEME["accent"], command=self._notify_engine_live);
        self.sw_link_alpha.pack(side="left")
        self.sched_progress = ctk.CTkProgressBar(c_ramp, progress_color=THEME["accent"], height=8);
        self.sched_progress.pack(fill="x", padx=20, pady=5);
        self.sched_progress.set(0)
        self.lbl_sched_status = ctk.CTkLabel(c_ramp, text="Inactive", text_color="gray",
                                             font=(THEME["font_family"], 11));
        self.lbl_sched_status.pack(pady=2)

        c_time = self.create_card(parent, "⏰ Daily Schedule", 0, 1)
        r_ts = ctk.CTkFrame(c_time, fg_color="transparent");
        r_ts.pack(fill="x", padx=10)
        self.sw_time_sched = ctk.CTkSwitch(r_ts, text="Enable Time Schedule", text_color=THEME["fg"],
                                           progress_color=THEME["accent"], command=self._notify_engine_live);
        self.sw_time_sched.pack(side="left")
        t_grid = ctk.CTkFrame(c_time, fg_color="transparent");
        t_grid.pack(pady=10)
        ctk.CTkLabel(t_grid, text="Start:", text_color=THEME["fg"]).pack(side="left")
        self.entry_start_time = ctk.CTkEntry(t_grid, width=50);
        self.entry_start_time.pack(side="left", padx=5);
        self.entry_start_time.bind("<FocusOut>", self._notify_engine_live)
        ctk.CTkLabel(t_grid, text="End:", text_color=THEME["fg"]).pack(side="left", padx=10)
        self.entry_end_time = ctk.CTkEntry(t_grid, width=50);
        self.entry_end_time.pack(side="left", padx=5);
        self.entry_end_time.bind("<FocusOut>", self._notify_engine_live)
        d_frame = ctk.CTkFrame(c_time, fg_color="transparent");
        d_frame.pack(pady=10)
        days = ["S", "M", "T", "W", "T", "F", "S"]
        self.day_buttons = []
        for d in days:
            btn = ctk.CTkButton(d_frame, text=d, width=30, height=30, corner_radius=15, fg_color=THEME["btn_bg"],
                                text_color="white", font=("Arial", 11, "bold"))
            btn.configure(command=lambda b=btn: self.toggle_day_btn(b))
            btn.pack(side="left", padx=2)
            self.day_buttons.append(btn)


if __name__ == "__main__":
    app_title = "Conditioning Control Panel"
    instance_checker = SingleInstanceChecker("ConditioningApp_Unique_ID_V1.5_BROWSER")
    instance_checker.check()

    if instance_checker.is_already_running():
        found = instance_checker.focus_existing_window(app_title)
        sys.exit(0)

    root = ctk.CTk()
    app = ControlPanel(root)

    if not app.settings.get('start_minimized', False):
        root.deiconify()
        root.lift()
        try:
            root.focus_force()
        except:
            pass

    root.mainloop()