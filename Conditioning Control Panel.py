import tkinter as tk
from tkinter import messagebox, simpledialog
import customtkinter as ctk  # pip install customtkinter
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

if not getattr(sys, 'frozen', False) and not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR)

BG_MUSIC_DIR = os.path.join(ASSETS_DIR, "backgrounds")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
TEMP_AUDIO_FILE = os.path.join(ASSETS_DIR, "temp_spot_audio.wav")

STARTUP_FOLDER = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup')
STARTUP_FILE_NAME = "ConditioningApp_AutoRun.bat"
STARTUP_FILE_PATH = os.path.join(STARTUP_FOLDER, STARTUP_FILE_NAME)

# --- FLUO BUBBLEGUM THEME ---
THEME = {
    "bg": "#FF69B4", "header_bg": "#FF1493", "card_bg": "#FFC0CB",
    "fg": "#4B0082", "font_family": "Comic Sans MS",
    "btn_bg": "#C71585", "btn_hover": "#8B008B",
    "accent": "#9400D3", "warning": "#8B0000",
    "entry_bg": "#FFFFFF", "entry_text": "#800080"
}

# --- TEXT POOL ---
BAMBI_TEXT_LIST = [
    "POP", "BIMBO DOLL", "GOOD GIRL", "BAMBI SLEEP", "BAMBI FREEZE",
    "ZAP COCK DRAIN OBEY", "BAMBI UNIFORM LOCK", "PRIMPED AND PAMPERED",
    "SNAP AND FORGET", "BAMBI RESET", "SAFE AND SECURE", "GIGGLETIME",
    "BLONDE MOMENT", "BAMBI DOES AS SHE'S TOLD", "DROP FOR COCK",
    "BAMBI CUM AND COLLAPSE"
]
BAMBI_POOL_DICT = {text: True for text in BAMBI_TEXT_LIST}

DEFAULT_SETTINGS = {
    # Flash Settings
    "flash_enabled": True,
    "min_interval": 20, "max_interval": 180,

    # Startle Settings (Shorts)
    "startle_enabled": True,
    "startle_freq": 6,
    "startle_strict": False,  # Strict lock during startle
    "force_startle_on_launch": False,

    # Audio/Visual
    "fade_duration": 0.4, "volume": 0.4,
    "dual_monitor": True,
    "sim_min": 4, "sim_max": 6, "image_scale": 0.9,

    # System
    "run_on_startup": False,
    "start_minimized": False, "auto_start_engine": False,
    "last_preset": "DEFAULT",

    # Subliminals
    "subliminal_enabled": False,
    "subliminal_freq": 5,
    "subliminal_duration": 2,
    "subliminal_pool": BAMBI_POOL_DICT.copy(),

    # Audio
    "bg_audio_enabled": True,
    "bg_audio_max": 10,
    "disable_panic_esc": False,

    # Attention / Game
    "attention_enabled": False,
    "attention_density": 3,
    "attention_lifespan": 5,
    "attention_size": 70,
    "attention_pool": BAMBI_POOL_DICT.copy()
}


# --- SYSTEM AUDIO DUCKER ---
class SystemAudioDucker:
    def __init__(self):
        self.original_volumes = {}
        self.is_ducked = False

    def duck(self):
        if not AUDIO_CONTROL_AVAILABLE or self.is_ducked: return
        try:
            sessions = AudioUtilities.GetAllSessions()
            current_pid = os.getpid()
            for session in sessions:
                volume = session.SimpleAudioVolume
                if session.Process and session.ProcessId != current_pid:
                    self.original_volumes[session.ProcessId] = volume.GetMasterVolume()
                    volume.SetMasterVolume(0.1, None)
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


# --- TRANSPARENT FLOATING TEXT ---
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


# --- Custom Input Dialog ---
class CustomInputDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="Input", text="Enter value:"):
        super().__init__(parent)
        self.title(title)
        self.geometry("300x180")
        self.configure(fg_color=THEME["bg"])
        self.value = None
        self.transient(parent)
        self.grab_set()
        self.columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=text, font=(THEME["font_family"], 14, "bold"), text_color=THEME["fg"]).pack(
            pady=(20, 10))
        self.entry = ctk.CTkEntry(self, width=200, font=(THEME["font_family"], 12), fg_color=THEME["entry_bg"],
                                  text_color=THEME["entry_text"])
        self.entry.pack(pady=5);
        self.entry.focus()
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="transparent", border_width=2, border_color=THEME["btn_bg"],
                      text_color=THEME["btn_bg"], width=80, command=self.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="OK", fg_color=THEME["btn_bg"], hover_color=THEME["btn_hover"], width=80,
                      command=self.on_ok).pack(side="right", padx=10)
        self.after(10, self._apply_color)

    def on_ok(self):
        self.value = self.entry.get();
        self.destroy()

    def get_input(self):
        self.wait_window();
        return self.value

    def _apply_color(self):
        try:
            ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.windll.user32.GetParent(self.winfo_id()), 35,
                                                       ctypes.byref(ctypes.c_int(0x00B469FF)), 4)
        except:
            pass


# --- The Central Brain ---
class FlasherEngine:
    def __init__(self, root_tk_ref, panic_callback):
        self.running = False
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
        self.penalty_loop_count = 0

        self.bg_playlist = []
        self.current_bg_index = 0
        self.is_bg_playing = False
        self.bg_duration = 0
        self.bg_start_time = 0
        self.gui_update_callback = None
        self.attention_spawns = []
        self.targets_total = 0
        self.targets_hit = 0
        self.current_video_duration = 0
        self.retry_video_path = None
        self.active_floating_texts = []
        self.gj_sound = None

        self.paths = {
            "images": os.path.join(ASSETS_DIR, "images"),
            "sounds": os.path.join(ASSETS_DIR, "sounds"),
            "startle_videos": os.path.join(ASSETS_DIR, "startle_videos"),
            "startle_snd": os.path.join(ASSETS_DIR, "StartleSound"),
            "backgrounds": BG_MUSIC_DIR
        }
        for path in self.paths.values(): os.makedirs(path, exist_ok=True)
        self.media_queues = {'startle': [], 'flash': []}

        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=8, buffer=4096)
            pygame.display.init()
        except:
            pass

        self.refresh_bg_playlist()
        self.load_gj_sound()

        # Start Global ESC Polling Thread
        self.esc_listener_active = True
        self.esc_thread = threading.Thread(target=self._monitor_global_esc, daemon=True)
        self.esc_thread.start()

        self.heartbeat()

    def _monitor_global_esc(self):
        """Polls for ESC key globally, works even if minimized."""
        while self.esc_listener_active:
            # 0x1B is VK_ESCAPE
            if ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000:
                self._handle_esc_press()
                time.sleep(0.5)  # Debounce
            time.sleep(0.05)

    def _handle_esc_press(self):
        # 1. Check if ESC is globally disabled
        if self.settings.get('disable_panic_esc', False):
            return

        # 2. Check if a Startle is running AND Strict Startle Lock is ON
        # If strict startle is ON, ESC is disabled ONLY during the video
        if self.video_running and self.settings.get('startle_strict', False):
            return

        # 3. Otherwise, Panic
        self.root.after(0, self.trigger_panic_from_window)

    def set_gui_callback(self, cb):
        self.gui_update_callback = cb

    def load_gj_sound(self):
        pattern = os.path.join(ASSETS_DIR, "GJ1.*")
        found = glob.glob(pattern)
        if found:
            try:
                self.gj_sound = pygame.mixer.Sound(found[0])
            except Exception:
                pass

    def play_gj(self):
        if self.gj_sound:
            try:
                self.gj_sound.play()
            except:
                pass

    def refresh_bg_playlist(self):
        self.bg_playlist = []
        valid_ext = ['*.mp3', '*.wav', '*.ogg']
        for ext in valid_ext:
            self.bg_playlist.extend(glob.glob(os.path.join(self.paths["backgrounds"], ext)))
        self.bg_playlist.sort()

    def play_bg_music(self, index=None, start_pos=0.0):
        if not self.bg_playlist: return
        if index is not None: self.current_bg_index = index
        if self.current_bg_index >= len(self.bg_playlist): self.current_bg_index = 0
        track = self.bg_playlist[self.current_bg_index]
        try:
            pygame.mixer.music.load(track)
            vol = self.settings.get('volume', 1.0) * (self.settings.get('bg_audio_max', 30) / 100.0)
            pygame.mixer.music.set_volume(vol)
            pygame.mixer.music.play(loops=0, start=start_pos)
            self.is_bg_playing = True
            self.bg_start_time = time.time() - start_pos
            try:
                sound = pygame.mixer.Sound(track)
                self.bg_duration = sound.get_length()
            except:
                self.bg_duration = 180
            pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)
        except Exception as e:
            print(f"[DEBUG] Error playing music: {e}")

    def seek_bg_music(self, percent_val):
        if not self.bg_playlist or not self.is_bg_playing: return
        new_pos = percent_val * self.bg_duration
        self.play_bg_music(self.current_bg_index, start_pos=new_pos)

    def toggle_bg_pause(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.is_bg_playing = False
        else:
            pygame.mixer.music.unpause()
            if not pygame.mixer.music.get_busy(): self.play_bg_music()
            self.is_bg_playing = True

    def next_bg_track(self):
        self.current_bg_index += 1
        self.play_bg_music()

    def update_settings(self, new_settings):
        self.settings = new_settings
        try:
            pygame.mixer.music.set_volume(float(new_settings['volume']))
        except:
            pass

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

    def start(self, is_startup=False):
        if self.running: return
        self.running = True
        self.events_pending_reschedule.clear()
        delay_loops = 0

        # --- FIX: Trigger Force Short even if manual start ---
        if self.settings.get('force_startle_on_launch'):
            self.busy = True
            self.root.after(5000, self._startup_startle_trigger)
            delay_loops = 20000

        self.root.after(delay_loops, self._start_loops)
        if self.settings.get('bg_audio_enabled') and self.bg_playlist:
            if not self.is_bg_playing: self.play_bg_music(0)

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
        pygame.mixer.music.stop()
        self.is_bg_playing = False
        self.ducker.unduck()

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
            pygame.mixer.music.stop();
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
        if os.path.exists(TEMP_AUDIO_FILE):
            try:
                os.remove(TEMP_AUDIO_FILE)
            except:
                pass

        self.strict_active = False
        try:
            self.root.deiconify()
            self.root.lift()
        except:
            pass

    def schedule_next(self, event_type):
        if not self.running: return
        seconds = 10
        if event_type == "startle":
            freq = max(1, self.settings.get('startle_freq', 10))
            seconds = int((60 / freq) * 60) + random.randint(-30, 30);
            seconds = max(5, seconds)
        elif event_type == "flash":
            seconds = random.randint(int(self.settings['min_interval']), int(self.settings['max_interval']))
        elif event_type == "subliminal":
            freq = max(1, self.settings.get('subliminal_freq', 10))
            base = 60 / freq
            seconds = base + random.uniform(-base * 0.2, base * 0.2);
            seconds = max(1, seconds)
        self.root.after(int(seconds * 1000), lambda: self.trigger_event(event_type))

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

    def trigger_event(self, event_type, strict_override=False):
        if not self.running: return
        if event_type == "subliminal":
            self._flash_subliminal()
            self.schedule_next("subliminal")
            return
        if event_type == "startle":
            if self.video_running:
                self.events_pending_reschedule.add(event_type)
                return
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
        scale = self.settings.get('image_scale', 1.0)
        threading.Thread(target=self._background_loader,
                         args=(selected_images, sound_path, False, False, monitors, scale), daemon=True).start()

    def _flash_subliminal(self):
        pool = self.settings.get('subliminal_pool', {})
        active_subs = [text for text, active in pool.items() if active]
        if not active_subs: return
        text_content = random.choice(active_subs)
        duration_ms = int(self.settings.get('subliminal_duration', 1) * 16.6)
        monitors = self._get_monitors_safe()
        for m in monitors:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True);
            win.config(bg='black')
            win.geometry(f"{m['width']}x{m['height']}+{m['x']}+{m['y']}")
            win.attributes('-topmost', True)
            lbl = tk.Label(win, text=text_content, bg='black', fg='#FF00FF', font=("Arial", 120, "bold"))
            lbl.place(relx=0.5, rely=0.5, anchor="center")
            self.root.after(duration_ms, win.destroy)

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
        return monitors

    def _apply_window_lock(self, win, is_strict):
        try:
            win.attributes("-toolwindow", 1)
        except:
            pass
        # Panic handling is now in _handle_esc_press
        if is_strict:
            win.protocol("WM_DELETE_WINDOW", lambda: None)
            win.bind('<Alt-F4>', lambda e: "break")
            win.bind("<Tab>", lambda e: "break")
            win.bind("<Alt-Tab>", lambda e: "break")
            win.lift();
            win.focus_force()

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
        self.active_windows.clear()
        self.active_rects.clear()

        if is_strict:
            self.strict_active = True
            try:
                self.root.withdraw()
                self.root.update()
            except:
                pass
        else:
            self.strict_active = False

        self.video_running = True
        self.ducker.duck()
        if pygame.mixer.music.get_busy(): pygame.mixer.music.pause()
        self.attention_spawns = []
        self.targets_hit = 0
        self.targets_total = 0
        self.retry_video_path = None

        if audio_path and os.path.exists(audio_path):
            try:
                self.vid_sound = pygame.mixer.Sound(audio_path)
                self.vid_channel = pygame.mixer.Channel(1)
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
            count = int((duration_sec / 30.0) * density)
            self.targets_total = count
            if count > 0:
                safe_end = max(2.0, duration_sec - 5.0)
                for _ in range(count):
                    t = random.uniform(2.0, safe_end)
                    self.attention_spawns.append(t)
                self.attention_spawns.sort()
                self.retry_video_path = video_path

        self.video_windows = []
        monitors = self._get_monitors_safe()
        for m in monitors:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True);
            win.config(bg='black')
            win.geometry(f"{m['width']}x{m['height']}+{m['x']}+{m['y']}")
            win.attributes('-topmost', True)
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
        if elapsed > self.current_video_duration + 0.5:
            self._cleanup_video();
            return
        if self.attention_spawns:
            if elapsed >= self.attention_spawns[0]:
                self._spawn_attention_target()
                self.attention_spawns.pop(0)
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
        last_dims = None
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
                    img = Image.fromarray(resized)
                    tk_img = ImageTk.PhotoImage(image=img)
                    last_dims = (nw, nh);
                    last_tk_img = tk_img
                vw['lbl'].configure(image=tk_img)
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
        win_x = target_win_data['win'].winfo_x()
        win_y = target_win_data['win'].winfo_y()
        w = target_win_data['w']
        h = target_win_data['h']
        size = self.settings.get('attention_size', 40)
        min_offset = 20
        safe_max_x = max(min_offset, w - int(size * 10))
        if safe_max_x < min_offset: safe_max_x = min_offset + 10
        safe_max_y = max(min_offset, h - int(size * 3))
        if safe_max_y < min_offset: safe_max_y = min_offset + 10
        rx = win_x + random.randint(min_offset, safe_max_x)
        ry = win_y + random.randint(min_offset, safe_max_y)

        def on_hit():
            self.targets_hit += 1
            print(f"[DEBUG] Target Hit! {self.targets_hit}/{self.targets_total}")
            self.play_gj()

        try:
            t_win = TransparentTextWindow(self.root, text, rx, ry, w, h, win_x, win_y, size, on_hit)
            self.active_floating_texts.append(t_win)
        except Exception as e:
            print(f"[DEBUG] Failed to spawn text: {e}"); return
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
        if self.settings.get('bg_audio_enabled') and self.is_bg_playing: pygame.mixer.music.unpause()
        loop_needed = False
        is_troll_loop = False
        if self.settings.get('attention_enabled', False):
            passed = (self.targets_total == 0) or (self.targets_hit >= self.targets_total)
            if not passed:
                loop_needed = True
            elif random.random() < 0.10:
                loop_needed = True; is_troll_loop = True
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
                self.root.deiconify(); self.root.lift()
            except:
                pass
        if self.settings.get('startle_enabled'): self.schedule_next("startle")
        if self.settings.get('subliminal_enabled'): self.schedule_next("subliminal")
        if self.events_pending_reschedule:
            for ev in list(self.events_pending_reschedule): self.schedule_next(ev)
            self.events_pending_reschedule.clear()

    def trigger_mercy_card(self):
        monitors = self._get_monitors_safe()
        mercy_wins = []
        for m in monitors:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True);
            win.config(bg='black')
            win.geometry(f"{m['width']}x{m['height']}+{m['x']}+{m['y']}")
            win.attributes('-topmost', True)
            win.lift();
            win.focus_force()
            lbl = tk.Label(win, text="BAMBI IS SO DUMB\nBAMBI RESET\n DROP FOR COCK", fg="#FF00FF", bg="black",
                           font=("Impact", 85, "bold"))
            lbl.pack(expand=True)
            mercy_wins.append(win)

        def finish_mercy():
            for w in mercy_wins: w.destroy()
            if self.strict_active:
                self.strict_active = False
                try:
                    self.root.deiconify(); self.root.lift()
                except:
                    pass
            if self.settings.get('startle_enabled'): self.schedule_next("startle")
            if self.settings.get('subliminal_enabled'): self.schedule_next("subliminal")
            if self.events_pending_reschedule:
                for ev in list(self.events_pending_reschedule): self.schedule_next(ev)
                self.events_pending_reschedule.clear()

        self.root.after(2500, finish_mercy)

    def trigger_penalty_loop(self, is_troll=False):
        if self.settings.get('startle_strict', False):
            self.strict_active = True
            try:
                self.root.withdraw(); self.root.update()
            except:
                pass
        monitors = self._get_monitors_safe()
        penalty_wins = []
        if is_troll:
            msg = "SUCH A GOOD SLUT BAMBI \nYOU DID IT...BUT\n SUCH GOOD GIRLS MUST AGAIN 😈"; f_size = 85
        else:
            msg = "WHAT A DUMB BAMBI\n DUMB BIMBOS MUST TRY AGAIN"; f_size = 100
        for m in monitors:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True);
            win.config(bg='black')
            win.geometry(f"{m['width']}x{m['height']}+{m['x']}+{m['y']}")
            win.attributes('-topmost', True)
            lbl = tk.Label(win, text=msg, fg="#FF00FF", bg="black", font=("Impact", f_size, "bold"))
            lbl.pack(expand=True)
            penalty_wins.append(win)

        def restart():
            for w in penalty_wins: w.destroy()
            is_strict = self.settings.get('startle_strict', False)
            threading.Thread(target=self._prep_startle_video, args=(self.retry_video_path, is_strict),
                             daemon=True).start()

        self.root.after(1500, restart)

    def on_image_click(self, win, is_startle, event_type):
        if hasattr(win, 'is_locked_spot') and win.is_locked_spot: return
        if win in self.active_windows:
            self.active_windows.remove(win)
            self.active_rects = [r for r in self.active_rects if r['win'] != win]
        win.destroy()
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
            self.ducker.duck()
            try:
                if data.get('processed_data') and data['processed_data'][0]['is_startle']:
                    threading.Thread(target=self._delayed_audio_start, args=(data['sound_path'],)).start()
                else:
                    effect = pygame.mixer.Sound(data['sound_path'])
                    duration = effect.get_length()
                    effect.play()
                    self.root.after(int(duration * 1000) + 1500, self.ducker.unduck)
            except Exception:
                self.ducker.unduck()
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
                effect = pygame.mixer.Sound(sound_path)
                effect.play()
                duration = effect.get_length()
                self.root.after(int(duration * 1000) + 1500, self.ducker.unduck)
            except:
                self.root.after(0, self.ducker.unduck)

    def _spawn_window_final(self, x, y, w, h, tk_frames, delay, is_startle, is_secondary):
        if not self.running: return
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes('-topmost', True)
        win.config(bg='black')
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.attributes('-alpha', 0.0)
        self._apply_window_lock(win, False)
        lbl = tk.Label(win, bg='black', bd=0);
        lbl.pack(expand=True, fill='both')
        lbl.bind('<Button-1>', lambda e: self.on_image_click(win, False, None))
        win.frames = tk_frames;
        win.frame_delay = delay;
        win.start_time = time.time()
        self.active_windows.append(win);
        self.active_rects.append({'win': win, 'x': x, 'y': y, 'w': w, 'h': h})

    def heartbeat(self):
        if self.settings.get('bg_audio_enabled') and self.is_bg_playing and self.gui_update_callback:
            if pygame.mixer.music.get_busy():
                elapsed = time.time() - self.bg_start_time
                if self.bg_duration > 0:
                    prog = min(1.0, elapsed / self.bg_duration)
                    self.gui_update_callback(prog, elapsed)
            else:
                for event in pygame.event.get():
                    if event.type == pygame.USEREVENT + 1: self.next_bg_track()
        if self.video_running: self.root.after(100, self.heartbeat); return
        show_images = time.time() < self.virtual_end_time
        target_alpha = 1.0 if show_images else 0.0
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
                if target_alpha > cur:
                    win.attributes('-alpha', min(1.0, cur + 0.08))
                elif target_alpha < cur:
                    new_a = max(0.0, cur - 0.08);
                    win.attributes('-alpha', new_a)
                    if new_a == 0.0:
                        win.destroy();
                        self.active_windows.remove(win)
                        self.active_rects = [r for r in self.active_rects if r['win'] != win]
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


# --- The Modern GUI ---
class ControlPanel:
    def __init__(self, root):
        self.root = root
        ctk.set_appearance_mode("Light");
        ctk.set_default_color_theme("blue")
        self.root.title("Conditioning Control Panel");
        self.root.geometry("1050x800")
        self.root.configure(fg_color=THEME["bg"])
        # Bind Close Button (X) to minimize
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.root.after(10, self._apply_title_bar_color)
        self.icon = None
        if TRAY_AVAILABLE: self.create_tray_icon()
        self.settings = self.load_settings()
        self.presets = self.load_presets()
        self.engine = FlasherEngine(self.root, self.restore_gui)
        self.engine.set_gui_callback(self.update_audio_ui)
        self.build_ui()
        self.engine.update_settings(self.settings)
        if self.settings.get('start_minimized', False):
            if TRAY_AVAILABLE:
                self.root.withdraw()
            else:
                self.root.iconify()
        for path in self.engine.paths.values(): os.makedirs(path, exist_ok=True)
        if self.settings.get('force_startle_on_launch'):
            self.root.after(500, lambda: self.btn_toggle.configure(text="STOP", fg_color=THEME["warning"],
                                                                   hover_color="#8B0000"))
            self.engine.start(is_startup=True)
        elif self.settings.get('auto_start_engine'):
            self.root.after(500, lambda: self.btn_toggle.configure(text="STOP", fg_color=THEME["warning"],
                                                                   hover_color="#8B0000"))
            self.engine.start(is_startup=True)

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
            self.btn_toggle.configure(text="STOP", fg_color=THEME["warning"], hover_color="#8B0000")
        else:
            self.btn_toggle.configure(text="DROP", fg_color=THEME["btn_bg"], hover_color=THEME["btn_hover"])

    def quit_app(self, icon=None, item=None):
        self.engine.panic_stop()
        self.engine.esc_listener_active = False  # Stop thread
        if self.icon: self.icon.stop()
        self.root.destroy();
        try:
            os._exit(0)
        except:
            pass

    def load_settings(self):
        settings = DEFAULT_SETTINGS.copy()
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    saved = json.load(f)
                    for key, value in saved.items(): settings[key] = value
            except:
                pass
        if 'subliminal_pool' not in settings or not settings['subliminal_pool']:
            settings['subliminal_pool'] = BAMBI_POOL_DICT.copy()
        if 'attention_enabled' not in settings: settings['attention_enabled'] = False
        if 'attention_pool' not in settings or not settings['attention_pool']:
            settings['attention_pool'] = BAMBI_POOL_DICT.copy()
        return settings

    def load_presets(self):
        # Enforce only DEFAULT preset
        return {"DEFAULT": DEFAULT_SETTINGS.copy()}

    def check_danger_toggle(self, switch_widget, name):
        if switch_widget.get() == 1:
            msg1 = (
                "⚠️ DANGER: SELF-LOCKING RISK ⚠️\n\nThis app allows for 'Self-Locking,' and if you combine settings incorrectly (well or correctly😈), "
                "you will lose control of your computer until you hard-reboot.\n\n(And if you enabled run on startup you might get stuck even if you reboot "
                "until you pass the startle lock!)\n\nThe program includes features designed to simulate a total loss of control. Approach these with extreme caution.")
            confirm1 = messagebox.askyesno(f"Enable {name}?", msg1, icon='warning')
            if not confirm1: switch_widget.deselect(); return
            msg2 = (
                "⛔ FINAL CONFIRMATION ⛔\n\nAre you sure? You will be locked until the startle is passed, or you fail it 3 times in a row!!!\n\n"
                "There may be NO ESCAPE KEY if you proceed.")
            confirm2 = messagebox.askyesno(f"Confirm {name}", msg2, icon='error')
            if not confirm2: switch_widget.deselect(); return

    def get_current_ui_values(self):
        return {
            "flash_enabled": self.sw_flash.get(),
            "min_interval": int(self.entry_min.get()), "max_interval": int(self.entry_max.get()),
            "startle_enabled": self.sw_startle.get(), "startle_freq": int(self.slider_s_freq.get()),
            "startle_strict": self.sw_s_strict.get(),
            "subliminal_enabled": self.sw_sub.get(), "subliminal_freq": int(self.slider_sub_freq.get()),
            "subliminal_duration": int(self.slider_sub_dur.get()), "subliminal_pool": self.settings['subliminal_pool'],
            "bg_audio_enabled": self.sw_bg_audio.get(), "bg_audio_max": int(self.slider_bg_vol.get()),
            "fade_duration": float(self.entry_fade.get()), "volume": float(self.slider_vol.get()) / 100.0,
            "dual_monitor": self.sw_dual.get(), "sim_min": int(self.slider_sim_min.get()),
            "sim_max": int(self.slider_sim_max.get()), "image_scale": float(self.slider_scale.get()) / 100.0,

            # Removed system strict lock setting here, default to False
            "strict_lock": False,
            "stealth_mode": False,
            "test_startle_start": False,

            "run_on_startup": self.sw_startup.get(),
            "force_startle_on_launch": self.sw_force.get(), "start_minimized": self.sw_min_start.get(),
            "auto_start_engine": self.sw_auto_start.get(), "last_preset": self.preset_menu.get(),
            "disable_panic_esc": self.sw_no_panic.get(),
            "attention_enabled": self.sw_attention.get(),
            "attention_pool": self.settings['attention_pool'],
            "attention_density": int(self.slider_attn_dens.get()),
            "attention_lifespan": int(self.slider_attn_life.get()),
            "attention_size": int(self.slider_attn_size.get())
        }

    def apply_settings_to_ui(self, s):
        if s.get('flash_enabled', True):
            self.sw_flash.select()
        else:
            self.sw_flash.deselect()
        self.entry_min.delete(0, 'end');
        self.entry_min.insert(0, s.get('min_interval', 3))
        self.entry_max.delete(0, 'end');
        self.entry_max.insert(0, s.get('max_interval', 10))
        if s.get('startle_enabled'):
            self.sw_startle.select()
        else:
            self.sw_startle.deselect()
        self.slider_s_freq.set(s.get('startle_freq', 10))
        if s.get('startle_strict'):
            self.sw_s_strict.select()
        else:
            self.sw_s_strict.deselect()
        if s.get('subliminal_enabled'):
            self.sw_sub.select()
        else:
            self.sw_sub.deselect()
        self.slider_sub_freq.set(s.get('subliminal_freq', 10))
        self.slider_sub_dur.set(s.get('subliminal_duration', 1))
        if 'subliminal_pool' not in s or not s['subliminal_pool']:
            self.settings['subliminal_pool'] = BAMBI_POOL_DICT.copy()
        else:
            self.settings['subliminal_pool'] = s.get('subliminal_pool')
        self.update_subliminal_menu()
        if s.get('bg_audio_enabled'):
            self.sw_bg_audio.select()
        else:
            self.sw_bg_audio.deselect()
        self.slider_bg_vol.set(s.get('bg_audio_max', 30))
        self.entry_fade.delete(0, 'end');
        self.entry_fade.insert(0, s.get('fade_duration', 0.5))
        self.slider_vol.set(s.get('volume', 1.0) * 100)
        self.lbl_vol_val.configure(text=f"{int(s.get('volume', 1.0) * 100)}%")
        if s.get('dual_monitor'):
            self.sw_dual.select()
        else:
            self.sw_dual.deselect()
        self.slider_sim_min.set(s.get('sim_min', 1))
        self.slider_sim_max.set(s.get('sim_max', 3))
        self.slider_scale.set(s.get('image_scale', 1.0) * 100)

        # System UI - Removed sw_strict, sw_stealth, sw_test
        if s.get('run_on_startup'):
            self.sw_startup.select()
        else:
            self.sw_startup.deselect()
        if s.get('force_startle_on_launch'):
            self.sw_force.select()
        else:
            self.sw_force.deselect()
        if s.get('auto_start_engine'):
            self.sw_auto_start.select()
        else:
            self.sw_auto_start.deselect()
        if s.get('start_minimized'):
            self.sw_min_start.select()
        else:
            self.sw_min_start.deselect()
        if s.get('disable_panic_esc'):
            self.sw_no_panic.select()
        else:
            self.sw_no_panic.deselect()
        if s.get('attention_enabled'):
            self.sw_attention.select()
        else:
            self.sw_attention.deselect()
        self.slider_attn_dens.set(s.get('attention_density', 2))
        self.slider_attn_life.set(s.get('attention_lifespan', 4))
        self.slider_attn_size.set(s.get('attention_size', 40))
        if 'attention_pool' not in s or not s['attention_pool']:
            self.settings['attention_pool'] = BAMBI_POOL_DICT.copy()
        else:
            self.settings['attention_pool'] = s.get('attention_pool')
        self.update_attention_menu()

    def save_settings(self):
        try:
            s = self.get_current_ui_values()
            self.settings = s
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(s, f)
            self.toggle_windows_startup(s['run_on_startup'])
            self.engine.update_settings(s)
            messagebox.showinfo("Saved", "Settings saved successfully!")
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers.")

    def reset_defaults(self):
        if messagebox.askyesno("Reset", "Reset all settings to default?"):
            self.apply_settings_to_ui(DEFAULT_SETTINGS)
            self.save_settings()

    def add_preset(self, choice):
        # Only allow selecting DEFAULT
        if choice == "DEFAULT":
            self.apply_settings_to_ui(DEFAULT_SETTINGS)
            self.save_settings()
        self.preset_menu.set("DEFAULT")

    def update_preset_menu(self):
        values = ["DEFAULT"]
        self.preset_menu.configure(values=values)

    def handle_sub_selection(self, choice):
        if choice == "Add Subliminal +":
            dialog = CustomInputDialog(self.root, title="New Subliminal", text="Enter Word/Phrase:")
            text = dialog.get_input()
            if text:
                self.settings['subliminal_pool'][text] = True
                self.update_subliminal_menu()
        elif choice == "Manage Subliminals":
            pass
        else:
            clean_text = choice[2:]
            current_state = self.settings['subliminal_pool'].get(clean_text, False)
            self.settings['subliminal_pool'][clean_text] = not current_state
            self.update_subliminal_menu()
        self.sub_menu.set("Manage Subliminals")

    def update_subliminal_menu(self):
        pool = self.settings.get('subliminal_pool', {})
        values = []
        for text, active in pool.items():
            prefix = "✅ " if active else "❌ "
            values.append(prefix + text)
        values.sort()
        values.append("Add Subliminal +")
        self.sub_menu.configure(values=values)

    def handle_attn_selection(self, choice):
        if choice == "Add Text +":
            dialog = CustomInputDialog(self.root, title="New Attention Text", text="Enter Text:")
            text = dialog.get_input()
            if text:
                self.settings['attention_pool'][text] = True
                self.update_attention_menu()
        elif choice == "Manage Targets":
            pass
        else:
            clean_text = choice[2:]
            current_state = self.settings['attention_pool'].get(clean_text, False)
            self.settings['attention_pool'][clean_text] = not current_state
            self.update_attention_menu()
        self.attn_menu.set("Manage Targets")

    def update_attention_menu(self):
        pool = self.settings.get('attention_pool', {})
        values = []
        for text, active in pool.items():
            prefix = "✅ " if active else "❌ "
            values.append(prefix + text)
        values.sort()
        values.append("Add Text +")
        self.attn_menu.configure(values=values)

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
            self.engine.stop()
            self.restore_gui()
        else:
            self.engine.start(is_startup=not manual)
            self.btn_toggle.configure(text="STOP", fg_color=THEME["warning"], hover_color="#8B0000")

    def update_audio_ui(self, progress, elapsed):
        self.progress_slider.set(progress)
        self.update_playlist_visuals()
        if pygame.mixer.music.get_busy():
            self.btn_play_bg.configure(text="⏸")
        else:
            self.btn_play_bg.configure(text="▶")

    def btn_play_click(self):
        self.engine.toggle_bg_pause()

    def btn_next_click(self):
        self.engine.next_bg_track()

    def on_slider_drag(self, value):
        self.engine.seek_bg_music(value)

    def on_playlist_item_click(self, index):
        if not self.sw_bg_audio.get():
            self.sw_bg_audio.select()
            self.settings['bg_audio_enabled'] = True
            self.engine.settings['bg_audio_enabled'] = True
        self.engine.play_bg_music(index)
        self.update_playlist_visuals()

    def update_playlist_visuals(self):
        current_idx = self.engine.current_bg_index
        for i, btn in enumerate(self.playlist_buttons):
            if i == current_idx:
                btn.configure(fg_color=THEME["accent"], text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color="black")

    def build_ui(self):
        main_font = (THEME["font_family"], 18, "bold")
        sub_font = (THEME["font_family"], 12, "bold")
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        left_side = ctk.CTkFrame(main_container, fg_color="transparent");
        left_side.pack(side="left", fill="both", expand=True)
        right_side = ctk.CTkFrame(main_container, fg_color="transparent");
        right_side.pack(side="right", fill="y", padx=(10, 0))
        header = ctk.CTkFrame(left_side, fg_color=THEME["header_bg"], corner_radius=20);
        header.pack(fill="x", pady=(0, 10))
        self.preset_menu = ctk.CTkOptionMenu(header, values=[], command=self.add_preset, fg_color="white",
                                             text_color=THEME["fg"], button_color=THEME["btn_bg"], font=sub_font,
                                             height=24)
        self.update_preset_menu();
        self.preset_menu.pack(side="right", padx=10, pady=5);
        self.preset_menu.set("DEFAULT")
        ctk.CTkLabel(header, text="💖 Conditioning Dashboard 💖", font=(THEME["font_family"], 24, "bold"),
                     text_color="white").pack(side="left", padx=10, pady=10)
        ctk.CTkLabel(header, text="ESC = PANIC", font=(THEME["font_family"], 12, "bold"), text_color="white").pack(
            side="left", padx=10)
        grid_frame = ctk.CTkFrame(left_side, fg_color="transparent");
        grid_frame.pack(fill="both", expand=True)
        grid_frame.columnconfigure(0, weight=1);
        grid_frame.columnconfigure(1, weight=1);
        grid_frame.columnconfigure(2, weight=1)

        def create_card(parent, title, bg_color, r, c, cs=1):
            frame = ctk.CTkFrame(parent, corner_radius=20, fg_color=bg_color)
            frame.grid(row=r, column=c, columnspan=cs, sticky="nsew", padx=5, pady=5)
            ctk.CTkLabel(frame, text=title, font=main_font, text_color=THEME["fg"]).pack(pady=5)
            return frame

        def add_slider(parent, default, from_, to_, steps, format_str="%d"):
            frame = ctk.CTkFrame(parent, fg_color="transparent");
            frame.pack(fill="x", padx=5, pady=1)
            lbl = ctk.CTkLabel(frame, text=format_str % default, font=sub_font, text_color=THEME["fg"], width=30);
            lbl.pack(side="right")

            def update_lbl(val): lbl.configure(text=format_str % int(val))

            slider = ctk.CTkSlider(frame, from_=from_, to=to_, number_of_steps=steps, button_color=THEME["btn_bg"],
                                   progress_color=THEME["accent"], command=update_lbl, height=14)
            slider.pack(side="left", fill="x", expand=True);
            slider.set(default)
            return slider

        c_flash = create_card(grid_frame, "✨ Flash", THEME["card_bg"], 0, 0)
        self.sw_flash = ctk.CTkSwitch(c_flash, text="Enable TRIGGER \n GIF OVERLAY", font=sub_font, text_color=THEME["fg"],
                                      progress_color=THEME["accent"]);
        self.sw_flash.pack(pady=2)
        if self.settings.get('flash_enabled', True): self.sw_flash.select()
        ctk.CTkLabel(c_flash, text="Min Interval (sec):", font=sub_font, text_color=THEME["fg"]).pack()
        self.entry_min = ctk.CTkEntry(c_flash, width=60, font=sub_font, fg_color="white", text_color=THEME["fg"]);
        self.entry_min.pack(pady=2);
        self.entry_min.insert(0, self.settings['min_interval'])
        ctk.CTkLabel(c_flash, text="Max Interval (sec):", font=sub_font, text_color=THEME["fg"]).pack()
        self.entry_max = ctk.CTkEntry(c_flash, width=60, font=sub_font, fg_color="white", text_color=THEME["fg"]);
        self.entry_max.pack(pady=2);
        self.entry_max.insert(0, self.settings['max_interval'])

        c_startle = create_card(grid_frame, "👻 Mandatory short", THEME["card_bg"], 0, 1)
        self.sw_startle = ctk.CTkSwitch(c_startle, text="Enable", font=sub_font, text_color=THEME["fg"],
                                        progress_color=THEME["accent"]);
        self.sw_startle.pack(pady=2)
        if self.settings['startle_enabled']: self.sw_startle.select()
        btn_now = ctk.CTkButton(c_startle, text="⚡ TRIGGER SHORT", fg_color="red", hover_color="#8B0000", height=24,
                                font=sub_font,
                                command=lambda: self.engine.trigger_event("startle", strict_override=False))
        btn_now.pack(pady=5)
        ctk.CTkLabel(c_startle, text="Freq/Hour:", font=sub_font, text_color=THEME["fg"]).pack()
        self.slider_s_freq = add_slider(c_startle, self.settings['startle_freq'], 1, 60, 59)
        self.sw_s_strict = ctk.CTkSwitch(c_startle, text="Strict Lock", font=sub_font, text_color=THEME["fg"],
                                         progress_color=THEME["warning"],
                                         command=lambda: self.check_danger_toggle(self.sw_s_strict,
                                                                                  "Startle Strict Lock"));
        self.sw_s_strict.pack(pady=2)
        if self.settings['startle_strict']: self.sw_s_strict.select()
        ctk.CTkFrame(c_startle, height=2, fg_color="white").pack(fill="x", padx=10, pady=5)
        self.sw_attention = ctk.CTkSwitch(c_startle, text="Attention Check", font=sub_font, text_color=THEME["fg"],
                                          progress_color="#FF00FF");
        self.sw_attention.pack(pady=2)
        if self.settings.get('attention_enabled'): self.sw_attention.select()
        ctk.CTkLabel(c_startle, text="Targets per 30s:", font=(THEME["font_family"], 10), text_color=THEME["fg"]).pack()
        self.slider_attn_dens = add_slider(c_startle, self.settings.get('attention_density', 2), 1, 60, 59)
        ctk.CTkLabel(c_startle, text="Lifespan (sec):", font=(THEME["font_family"], 10), text_color=THEME["fg"]).pack()
        self.slider_attn_life = add_slider(c_startle, self.settings.get('attention_lifespan', 4), 2, 10, 8)
        ctk.CTkLabel(c_startle, text="Target Size:", font=(THEME["font_family"], 10), text_color=THEME["fg"]).pack()
        self.slider_attn_size = add_slider(c_startle, self.settings.get('attention_size', 40), 10, 180, 60)
        self.attn_menu = ctk.CTkOptionMenu(c_startle, values=[], command=self.handle_attn_selection, fg_color="white",
                                           text_color=THEME["fg"], button_color=THEME["btn_bg"], font=sub_font,
                                           height=20)
        self.attn_menu.pack(pady=5);
        self.update_attention_menu();
        self.attn_menu.set("Manage Targets")

        c_vis = create_card(grid_frame, "🎨 Visuals", THEME["card_bg"], 0, 2)
        vis_inner = ctk.CTkFrame(c_vis, fg_color="transparent");
        vis_inner.pack(fill="x", padx=5)
        ctk.CTkLabel(vis_inner, text="Simultaneous Images:", font=sub_font, text_color=THEME["fg"]).pack(anchor="w")
        ctk.CTkLabel(vis_inner, text="Minimum:", font=(THEME["font_family"], 10), text_color=THEME["fg"]).pack(
            anchor="w")
        self.slider_sim_min = add_slider(vis_inner, self.settings['sim_min'], 1, 20, 19)
        ctk.CTkLabel(vis_inner, text="Maximum:", font=(THEME["font_family"], 10), text_color=THEME["fg"]).pack(
            anchor="w")
        self.slider_sim_max = add_slider(vis_inner, self.settings['sim_max'], 1, 20, 19)
        ctk.CTkLabel(vis_inner, text="Image Scale:", font=sub_font, text_color=THEME["fg"]).pack(anchor="w",
                                                                                                 pady=(5, 0))
        self.slider_scale = add_slider(vis_inner, self.settings['image_scale'] * 100, 50, 250, 20, "%d%%")
        vol_frame = ctk.CTkFrame(c_vis, fg_color="transparent");
        vol_frame.pack(fill="x", pady=5)
        center_cont = ctk.CTkFrame(vol_frame, fg_color="transparent");
        center_cont.pack(anchor="center")
        ctk.CTkLabel(center_cont, text="Fade(s):", font=sub_font, text_color=THEME["fg"]).pack(side="left")
        # WIDENED ENTRY BOX TO 40
        self.entry_fade = ctk.CTkEntry(center_cont, width=40, font=sub_font, fg_color="white", text_color=THEME["fg"]);
        self.entry_fade.pack(side="left", padx=2);
        self.entry_fade.insert(0, self.settings['fade_duration'])
        ctk.CTkLabel(center_cont, text="Vol:", font=sub_font, text_color=THEME["fg"]).pack(side="left", padx=(10, 0))
        self.lbl_vol_val = ctk.CTkLabel(center_cont, text=f"{int(self.settings['volume'] * 100)}%", font=sub_font,
                                        text_color=THEME["fg"], width=35);
        self.lbl_vol_val.pack(side="right")
        self.slider_vol = ctk.CTkSlider(center_cont, from_=0, to=100, width=80, button_color=THEME["btn_bg"],
                                        command=lambda v: self.lbl_vol_val.configure(text=f"{int(v)}%"));
        self.slider_vol.pack(side="left", padx=2);
        self.slider_vol.set(self.settings['volume'] * 100)

        c_sub = create_card(grid_frame, "🧠 Subliminal", THEME["card_bg"], 1, 0, 2)
        self.sw_sub = ctk.CTkSwitch(c_sub, text="Enable", font=sub_font, text_color=THEME["fg"],
                                    progress_color=THEME["accent"]);
        self.sw_sub.pack(pady=2)
        if self.settings['subliminal_enabled']: self.sw_sub.select()
        ctk.CTkLabel(c_sub, text="Freq/Min:", font=sub_font, text_color=THEME["fg"]).pack()
        self.slider_sub_freq = add_slider(c_sub, self.settings['subliminal_freq'], 1, 30, 29)
        ctk.CTkLabel(c_sub, text="Duration (Frames):", font=sub_font, text_color=THEME["fg"]).pack()
        self.slider_sub_dur = add_slider(c_sub, self.settings['subliminal_duration'], 1, 30, 29)
        ctk.CTkLabel(c_sub, text="Manage Text Pool:", font=sub_font, text_color=THEME["fg"]).pack(pady=(5, 0))
        self.sub_menu = ctk.CTkOptionMenu(c_sub, values=[], command=self.handle_sub_selection, fg_color="white",
                                          text_color=THEME["fg"], button_color=THEME["btn_bg"], font=sub_font,
                                          height=20)
        self.sub_menu.pack(pady=5);
        self.update_subliminal_menu();
        self.sub_menu.set("Manage Subliminals")

        c_sys = create_card(grid_frame, "⚙️ System", THEME["card_bg"], 1, 2)
        sys_inner = ctk.CTkFrame(c_sys, fg_color="transparent");
        sys_inner.pack(fill="both", padx=5)
        sys_inner.columnconfigure(0, weight=1);
        sys_inner.columnconfigure(1, weight=1)

        self.sw_dual = ctk.CTkSwitch(sys_inner, text="Dual Mon", font=sub_font, text_color=THEME["fg"],
                                     progress_color=THEME["accent"]);
        self.sw_dual.grid(row=0, column=0, sticky="w", pady=2)
        if self.settings['dual_monitor']: self.sw_dual.select()
        if not SCREENINFO_AVAILABLE: self.sw_dual.configure(state="disabled")

        self.sw_startup = ctk.CTkSwitch(sys_inner, text="Startup Run", font=sub_font, text_color=THEME["fg"],
                                        progress_color=THEME["warning"],
                                        command=lambda: self.check_danger_toggle(self.sw_startup, "Run on Startup"));
        self.sw_startup.grid(row=0, column=1, sticky="w", pady=2)
        if self.settings['run_on_startup']: self.sw_startup.select()

        # Rename to "Force Short on Start"
        self.sw_force = ctk.CTkSwitch(sys_inner, text="Force Short on Start", font=sub_font, text_color=THEME["fg"],
                                      progress_color=THEME["accent"]);
        self.sw_force.grid(row=1, column=0, sticky="w", pady=2)
        if self.settings['force_startle_on_launch']: self.sw_force.select()

        # Removed: sw_test, sw_stealth, sw_strict (system)

        self.sw_auto_start = ctk.CTkSwitch(sys_inner, text="Auto-Start", font=sub_font, text_color=THEME["fg"],
                                           progress_color=THEME["accent"]);
        self.sw_auto_start.grid(row=1, column=1, sticky="w", pady=2)
        if self.settings['auto_start_engine']: self.sw_auto_start.select()

        self.sw_min_start = ctk.CTkSwitch(sys_inner, text="Minimize at Start", font=sub_font, text_color=THEME["fg"],
                                          progress_color=THEME["accent"]);
        self.sw_min_start.grid(row=2, column=0, sticky="w", pady=2)
        if self.settings.get('start_minimized', False): self.sw_min_start.select()

        self.sw_no_panic = ctk.CTkSwitch(sys_inner, text="Disable ESC", font=sub_font, text_color=THEME["warning"],
                                         progress_color=THEME["warning"],
                                         command=lambda: self.check_danger_toggle(self.sw_no_panic,
                                                                                  "Disable Panic Key"));
        self.sw_no_panic.grid(row=2, column=1, sticky="w", pady=2)
        if self.settings.get('disable_panic_esc'): self.sw_no_panic.select()

        ctk.CTkButton(sys_inner, text="Reset Default", fg_color="transparent", border_width=2,
                      border_color=THEME["warning"], text_color=THEME["warning"], height=20, width=100,
                      command=self.reset_defaults).grid(row=3, column=0, columnspan=2, pady=5)

        # --- REORDERED: BG AUDIO PLAYER FIRST ---
        c_bg = ctk.CTkFrame(right_side, corner_radius=20, fg_color=THEME["card_bg"]);
        c_bg.pack(fill="x", pady=5)
        ctk.CTkLabel(c_bg, text="🎵 background tone", font=("Comic Sans MS", 12, "bold"), text_color=THEME["fg"]).pack(
            pady=(5, 2))
        self.sw_bg_audio = ctk.CTkSwitch(c_bg, text="Enable", font=sub_font, text_color=THEME["fg"],
                                         progress_color=THEME["accent"]);
        self.sw_bg_audio.pack(pady=2)
        if self.settings['bg_audio_enabled']: self.sw_bg_audio.select()
        player_frame = ctk.CTkFrame(c_bg, fg_color="transparent")
        player_frame.pack(fill="x", padx=5, pady=2)
        self.btn_play_bg = ctk.CTkButton(player_frame, text="▶", width=30, fg_color=THEME["btn_bg"],
                                         command=self.btn_play_click)
        self.btn_play_bg.pack(side="left", padx=2)
        self.btn_next_bg = ctk.CTkButton(player_frame, text="⏭", width=30, fg_color=THEME["btn_bg"],
                                         command=self.btn_next_click)
        self.btn_next_bg.pack(side="left", padx=2)
        self.progress_slider = ctk.CTkSlider(player_frame, from_=0, to=1, height=10, button_color=THEME["accent"],
                                             progress_color=THEME["accent"], command=self.on_slider_drag)
        self.progress_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.progress_slider.set(0)
        ctk.CTkLabel(c_bg, text="Max Vol:", font=sub_font, text_color=THEME["fg"]).pack()
        self.slider_bg_vol = add_slider(c_bg, self.settings['bg_audio_max'], 1, 100, 99)
        playlist_frame = ctk.CTkScrollableFrame(c_bg, height=80, label_text="Themes", label_fg_color=THEME["header_bg"])
        playlist_frame.pack(fill="x", padx=5, pady=5)
        self.playlist_buttons = []
        if self.engine.bg_playlist:
            for i, f_path in enumerate(self.engine.bg_playlist):
                f_name = os.path.basename(f_path)
                btn = ctk.CTkButton(playlist_frame, text=f_name, height=20, fg_color="transparent", text_color="black",
                                    hover_color=THEME["entry_bg"], anchor="w",
                                    command=lambda idx=i: self.on_playlist_item_click(idx))
                btn.pack(fill="x")
                self.playlist_buttons.append(btn)
        else:
            ctk.CTkLabel(playlist_frame, text="No files in assets/backgrounds", text_color="gray").pack()

        # --- THEN THE START BUTTON (MOVED DOWN) ---
        self.btn_toggle = ctk.CTkButton(right_side, text="DROP", fg_color=THEME["btn_bg"],
                                        hover_color=THEME["btn_hover"], corner_radius=30, width=180, height=120,
                                        font=("Comic Sans MS", 30, "bold"),
                                        command=lambda: self.toggle_engine(manual=True))
        self.btn_toggle.pack(side="top", pady=(10, 10))

        # Exit button above Save
        ctk.CTkButton(right_side, text="EXIT", fg_color="transparent", border_width=2, border_color="red",
                      text_color="red", hover_color=THEME["entry_bg"], corner_radius=30, width=180, height=40,
                      font=("Comic Sans MS", 16, "bold"), command=self.quit_app).pack(side="bottom", pady=(5, 5))

        ctk.CTkButton(right_side, text="SAVE", fg_color="transparent", border_width=4, border_color=THEME["btn_bg"],
                      text_color=THEME["btn_bg"], hover_color=THEME["entry_bg"], corner_radius=30, width=180, height=60,
                      font=("Comic Sans MS", 20, "bold"), command=self.save_settings).pack(side="bottom", pady=(5, 5))


if __name__ == "__main__":
    root = ctk.CTk()
    app = ControlPanel(root)
    root.mainloop()