import os
import sys
import json
import threading
import ctypes
import tkinter as tk
from tkinter import messagebox, simpledialog, colorchooser, filedialog
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw

try:
    import pystray
    from pystray import MenuItem as item

    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

try:
    from screeninfo import get_monitors

    SCREENINFO_AVAILABLE = True
except ImportError:
    SCREENINFO_AVAILABLE = False

from config import (
    THEME, DEFAULT_SETTINGS, BAMBI_POOL_DICT, ASSETS_DIR, BASE_DIR,
    SETTINGS_FILE, PRESETS_FILE, STARTUP_FILE_PATH
)
from utils import SingleInstanceChecker
from engine import FlasherEngine
from ui_components import TextManagerDialog

# --- HOT PINK ACCENTS + PURPLE BACKGROUNDS ---
M = {
    "bg": "#1A0A1F",  # Dark purple background
    "header": "#2D1B3D",  # Purple header
    "card": "#251830",  # Dark purple card
    "card_hover": "#2F1E3A",
    "border": "#6B3A6B",  # Purple-pink border
    "fg": "#FFE6F6",  # Light pink text
    "fg_dim": "#B088B0",  # Dimmed purple-pink text
    "accent": "#FF69B4",  # HOT PINK - primary accent
    "accent_dim": "#DB7093",  # Pale violet red
    "btn": "#FF1493",  # Deep pink - buttons
    "btn_hover": "#C71585",  # Medium violet red
    "danger": "#FF4757",  # Red
    "danger_hover": "#C0392B",
    "success": "#00E676",  # Green
    "success_hover": "#00C853",
    "switch_on": "#FF69B4",  # Hot pink
    "switch_off": "#3D2847",  # Purple off state
    "slider": "#FF69B4",  # Hot pink
    "slider_bg": "#1A0A20",  # Dark purple
    "input_bg": "#1A0A20",  # Dark purple
    "tooltip_bg": "#3D2050",  # Purple tooltip
    "xp_bar": "#FF69B4",  # Hot pink XP bar
}


class ModernToolTip:
    """Modern tooltip with wrap and styling"""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, e=None):
        if self.tip:
            return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_attributes("-topmost", True)
        frame = tk.Frame(tw, bg=M["tooltip_bg"], padx=10, pady=6)
        frame.pack()
        frame.configure(highlightbackground=M["accent"], highlightthickness=1)
        tk.Label(frame, text=self.text, bg=M["tooltip_bg"], fg=M["fg"],
                 font=("Segoe UI", 9), justify="left", wraplength=280).pack()
        tw.wm_geometry(f"+{x}+{y}")

    def hide(self, e=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class ControlPanel:
    def __init__(self, root):
        self.root = root
        ctk.set_appearance_mode("Dark")
        self.root.title("💗 Conditioning Dashboard")
        self.root.geometry("1100x820")  # Taller window
        self.root.configure(fg_color=M["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        # Icon
        self.icon_path = None
        for folder in [ASSETS_DIR, BASE_DIR]:
            for name in ["Conditioning Control Panel.png", "icon.png"]:
                p = os.path.join(folder, name)
                if os.path.exists(p):
                    self.icon_path = p
                    break
            if self.icon_path:
                break

        if self.icon_path:
            try:
                img = Image.open(self.icon_path)
                self.icon_photo = ImageTk.PhotoImage(img)
                self.root.wm_iconphoto(True, self.icon_photo)
            except:
                pass

        self.root.after(10, self._style_titlebar)
        self.icon = None
        if TRAY_AVAILABLE:
            self._create_tray()

        self.presets = self._load_presets()
        self.settings = self._load_settings()
        saved_xp = self.settings.get('player_xp', 0.0)
        saved_lvl = self.settings.get('player_level', 1)

        self._build_ui()
        self._apply_settings(self.settings)

        self.engine = FlasherEngine(self.root, self._restore)
        self.engine.xp_update_callback = self._update_xp
        self.engine.scheduler_update_callback = self._update_scheduler
        self.engine.update_settings(self.settings)
        self.engine.settings['player_xp'] = saved_xp
        self.engine.settings['player_level'] = saved_lvl
        self.engine._update_ui_xp()
        self._check_unlocks(saved_lvl)

        # Initialize browser after GUI is ready
        self.root.after(1000, self._init_browser)

        # Show welcome message on first launch (after browser loads)
        self.root.after(1500, self._check_first_launch)

        if self.settings.get('start_minimized'):
            self.root.withdraw()
        if self.settings.get('auto_start_engine'):
            self.root.after(2000, lambda: self._toggle(manual=False))
        if self.settings.get('force_startle_on_launch'):
            self.root.after(3000, lambda: self.engine.trigger_event("startle"))

    def _check_first_launch(self):
        """Show welcome message on first launch"""
        if not self.settings.get('welcomed', False):
            self._show_welcome_dialog()
            # Mark as welcomed
            self.settings['welcomed'] = True
            self._save_settings()

    def _show_welcome_dialog(self):
        """Show a welcome dialog for new users"""
        welcome_win = ctk.CTkToplevel(self.root)
        welcome_win.title("🎀 Welcome to Conditioning Control Panel!")
        welcome_win.geometry("500x420")
        welcome_win.resizable(False, False)
        welcome_win.transient(self.root)
        welcome_win.grab_set()
        welcome_win.configure(fg_color=M["bg"])

        # Force on top of everything including browser
        welcome_win.attributes('-topmost', True)
        welcome_win.lift()
        welcome_win.focus_force()

        # Center on screen
        welcome_win.update_idletasks()
        x = (welcome_win.winfo_screenwidth() - 500) // 2
        y = (welcome_win.winfo_screenheight() - 420) // 2
        welcome_win.geometry(f"500x420+{x}+{y}")

        # Keep on top after geometry change
        welcome_win.after(100, lambda: welcome_win.attributes('-topmost', True))
        welcome_win.after(100, lambda: welcome_win.lift())

        # Header
        ctk.CTkLabel(welcome_win, text="🎀 Welcome, Bambi! 🎀",
                     font=("Segoe UI", 24, "bold"), text_color=M["accent"]).pack(pady=(20, 10))

        # Message
        msg = """This is your Conditioning Control Panel!

Before you begin, please read the README file for:
• How each feature works
• Safety warnings (especially for Strict Lock mode)
• Tips for the best experience

Choose a preset to get started, or customize 
your own settings in the Settings tab.

Remember: ESC is your panic button (unless disabled)!

Enjoy the pink fog... 💕"""

        ctk.CTkLabel(welcome_win, text=msg, font=("Segoe UI", 12),
                     text_color=M["fg"], justify="center").pack(pady=10, padx=20)

        # Preset selection
        ctk.CTkLabel(welcome_win, text="Choose a starting preset:",
                     font=("Segoe UI", 12, "bold"), text_color=M["fg_dim"]).pack(pady=(15, 5))

        preset_frame = ctk.CTkFrame(welcome_win, fg_color="transparent")
        preset_frame.pack(pady=5)

        def apply_preset(name):
            self._apply_builtin_preset(name)
            welcome_win.destroy()

        presets = [
            ("🌸 Beginner Bimbo", "beginner", "Low intensity, perfect for starting"),
            ("💄 Bimbo in Training", "training", "Medium-low, gentle conditioning"),
            ("💋 Advanced Bimbo", "advanced", "Medium-high, more intense"),
            ("👑 Ultimate Bimbodoll", "ultimate", "High intensity experience"),
        ]

        for label, key, tip in presets:
            btn = ctk.CTkButton(preset_frame, text=label, font=("Segoe UI", 11),
                                fg_color=M["card"], hover_color=M["btn"],
                                text_color=M["fg"], width=200, height=30,
                                command=lambda k=key: apply_preset(k))
            btn.pack(pady=3)
            ModernToolTip(btn, tip)

        # Skip button
        ctk.CTkButton(welcome_win, text="Skip (Keep Current Settings)",
                      fg_color="transparent", hover_color=M["card"],
                      text_color=M["fg_dim"], font=("Segoe UI", 10),
                      command=welcome_win.destroy).pack(pady=15)

    def _apply_builtin_preset(self, preset_key):
        """Apply a built-in preset"""
        presets = {
            "beginner": {
                "flash_enabled": True, "flash_freq": 1, "sim_images": 2,
                "flash_clickable": True, "flash_corruption": False, "flash_hydra_limit": 10,
                "startle_enabled": False, "startle_freq": 2, "startle_strict": False,
                "subliminal_enabled": False, "subliminal_freq": 2, "subliminal_duration": 3,
                "image_scale": 0.7, "image_alpha": 0.8, "fade_duration": 0.5,
                "volume": 0.25, "audio_ducking_enabled": True, "audio_ducking_strength": 50,
                "dual_monitor": False, "disable_panic_esc": False,
                "attention_enabled": False,
                "scheduler_enabled": False,
                "pink_filter_enabled": False, "spiral_enabled": False, "bubbles_enabled": False,
            },
            "training": {
                "flash_enabled": True, "flash_freq": 2, "sim_images": 3,
                "flash_clickable": True, "flash_corruption": False, "flash_hydra_limit": 12,
                "startle_enabled": True, "startle_freq": 4, "startle_strict": False,
                "subliminal_enabled": True, "subliminal_freq": 3, "subliminal_duration": 2,
                "image_scale": 0.8, "image_alpha": 0.9, "fade_duration": 0.4,
                "volume": 0.35, "audio_ducking_enabled": True, "audio_ducking_strength": 70,
                "dual_monitor": True, "disable_panic_esc": False,
                "attention_enabled": False,
                "scheduler_enabled": False,
                "pink_filter_enabled": True, "pink_filter_opacity": 0.1,
                "spiral_enabled": False, "bubbles_enabled": True, "bubbles_freq": 3,
            },
            "advanced": {
                "flash_enabled": True, "flash_freq": 4, "sim_images": 5,
                "flash_clickable": True, "flash_corruption": True, "flash_hydra_limit": 15,
                "startle_enabled": True, "startle_freq": 6, "startle_strict": False,
                "subliminal_enabled": True, "subliminal_freq": 5, "subliminal_duration": 2,
                "image_scale": 0.9, "image_alpha": 1.0, "fade_duration": 0.3,
                "volume": 0.45, "audio_ducking_enabled": True, "audio_ducking_strength": 85,
                "dual_monitor": True, "disable_panic_esc": False,
                "attention_enabled": True, "attention_density": 3,
                "scheduler_enabled": True, "scheduler_duration_min": 30,
                "pink_filter_enabled": True, "pink_filter_opacity": 0.15,
                "spiral_enabled": True, "spiral_opacity": 0.15,
                "bubbles_enabled": True, "bubbles_freq": 5,
            },
            "ultimate": {
                "flash_enabled": True, "flash_freq": 6, "sim_images": 7,
                "flash_clickable": True, "flash_corruption": True, "flash_hydra_limit": 18,
                "startle_enabled": True, "startle_freq": 8, "startle_strict": True,
                "subliminal_enabled": True, "subliminal_freq": 7, "subliminal_duration": 1,
                "image_scale": 1.0, "image_alpha": 1.0, "fade_duration": 0.2,
                "volume": 0.55, "audio_ducking_enabled": True, "audio_ducking_strength": 100,
                "dual_monitor": True, "disable_panic_esc": False,
                "attention_enabled": True, "attention_density": 5,
                "scheduler_enabled": True, "scheduler_duration_min": 60, "scheduler_multiplier": 1.5,
                "pink_filter_enabled": True, "pink_filter_opacity": 0.2, "pink_filter_link_ramp": True,
                "spiral_enabled": True, "spiral_opacity": 0.2, "spiral_link_ramp": True,
                "bubbles_enabled": True, "bubbles_freq": 7, "bubbles_link_ramp": True,
            },
        }

        if preset_key in presets:
            preset_settings = presets[preset_key]
            # Preserve player progress
            preset_settings['player_level'] = self.settings.get('player_level', 1)
            preset_settings['player_xp'] = self.settings.get('player_xp', 0.0)
            preset_settings['welcomed'] = True
            # Merge with defaults
            new_settings = DEFAULT_SETTINGS.copy()
            new_settings.update(preset_settings)
            self._apply_settings(new_settings)
            self.settings = new_settings
            self.engine.update_settings(new_settings)
            self._save_settings()

    def _init_browser(self):
        """Initialize the embedded browser"""
        if hasattr(self, 'browser_container') and self.browser_container.winfo_exists():
            try:
                # Update status
                if hasattr(self, 'browser_status'):
                    self.browser_status.configure(text="● Loading...", text_color=M["accent"])

                self.engine.browser.launch_embedded(self.browser_container)
                self.root.after(3000, self._apply_browser_zoom)
                self.root.after(4000, self._browser_ready)
            except Exception as e:
                print(f"[DEBUG] Browser init error: {e}")
                if hasattr(self, 'browser_status'):
                    self.browser_status.configure(text="● Error", text_color=M["danger"])

    def _browser_ready(self):
        """Called when browser is ready"""
        if hasattr(self, 'browser_status'):
            self.browser_status.configure(text="● Connected", text_color=M["success"])

    def _apply_browser_zoom(self):
        """Apply zoom to embedded browser"""
        zoom_script = "document.body.style.zoom='75%'"
        try:
            if hasattr(self.engine.browser, 'driver') and self.engine.browser.driver:
                self.engine.browser.driver.execute_script(zoom_script)
            elif hasattr(self.engine.browser, 'execute_script'):
                self.engine.browser.execute_script(zoom_script)
        except:
            pass

    def _style_titlebar(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            color = 0x001F0A1A  # BGR format - dark purple
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(ctypes.c_int(color)), 4)
        except:
            pass

    def _load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    s = json.load(f)
                m = DEFAULT_SETTINGS.copy()
                m.update(s)
                if 'subliminal_pool' not in m:
                    m['subliminal_pool'] = BAMBI_POOL_DICT.copy()
                if 'attention_pool' not in m:
                    m['attention_pool'] = BAMBI_POOL_DICT.copy()
                return m
            except:
                pass
        return DEFAULT_SETTINGS.copy()

    def _save_settings(self):
        s = self._get_values()
        s['player_level'] = self.engine.settings.get('player_level', 1)
        s['player_xp'] = self.engine.settings.get('player_xp', 0.0)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(s, f, indent=2)
        self.settings = s
        self.engine.update_settings(s)

    def _load_presets(self):
        if os.path.exists(PRESETS_FILE):
            try:
                with open(PRESETS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_presets(self):
        with open(PRESETS_FILE, 'w') as f:
            json.dump(self.presets, f, indent=2)
        self._update_preset_menu()

    def _update_preset_menu(self):
        # Built-in presets + DEFAULT + user presets
        builtin = ["🌸 Beginner Bimbo", "💄 Bimbo in Training", "💋 Advanced Bimbo", "👑 Ultimate Bimbodoll"]
        names = ["DEFAULT"] + builtin + sorted(self.presets.keys())
        self.preset_menu.configure(values=names)

    def _handle_preset(self, name):
        # Built-in preset mapping
        builtin_map = {
            "🌸 Beginner Bimbo": "beginner",
            "💄 Bimbo in Training": "training",
            "💋 Advanced Bimbo": "advanced",
            "👑 Ultimate Bimbodoll": "ultimate",
        }

        if name in builtin_map:
            self._apply_builtin_preset(builtin_map[name])
            return
        elif name == "DEFAULT":
            s = DEFAULT_SETTINGS.copy()
        elif name in self.presets:
            s = self.presets[name].copy()
        else:
            return
        s['player_level'] = self.engine.settings.get('player_level', 1)
        s['player_xp'] = self.engine.settings.get('player_xp', 0.0)
        self.settings = s
        self._apply_settings(s)
        self.engine.update_settings(s)

    def _create_tray(self):
        def setup(icon):
            icon.visible = True

        try:
            if self.icon_path:
                img = Image.open(self.icon_path)
            else:
                img = Image.new('RGB', (64, 64), color=(157, 39, 176))
            menu = pystray.Menu(
                item('Show', self._restore, default=True),
                item('Exit', self._quit)
            )
            self.icon = pystray.Icon("app", img, "Conditioning", menu)
            threading.Thread(target=lambda: self.icon.run(setup), daemon=True).start()
        except:
            pass

    def minimize_to_tray(self):
        self._save_settings()
        self.root.withdraw()

    def _restore(self, icon=None, item=None):
        self.root.deiconify()
        self.root.lift()
        self._sync_btns()
        try:
            self.engine.browser.resize_to_container()
        except:
            pass

    def _quit(self, icon=None, item=None):
        self.engine.panic_stop()
        self.engine.esc_listener_active = False
        try:
            self.engine.browser.close()
        except:
            pass
        self._save_settings()
        if self.icon:
            self.icon.stop()
        self.root.destroy()

    def _danger_check(self, sw, name):
        if sw.get():
            if not messagebox.askyesno("⚠️ Warning", f"Enable '{name}'?\n\nThis is a dangerous setting."):
                sw.deselect()
                return
        self._notify()

    def _check_unlocks(self, level):
        if level >= 10:
            self.lv10_locked.pack_forget()
            self.lv10_unlocked.pack(fill="both", expand=True, padx=5, pady=5)
        else:
            self.lv10_unlocked.pack_forget()
            self.lv10_locked.pack(fill="both", expand=True, padx=5, pady=5)
        if level >= 20:
            self.lv20_locked.pack_forget()
            self.lv20_unlocked.pack(fill="both", expand=True, padx=5, pady=5)
        else:
            self.lv20_unlocked.pack_forget()
            self.lv20_locked.pack(fill="both", expand=True, padx=5, pady=5)

    def _toggle_day(self, btn):
        if btn._fg_color == M["btn"]:
            btn.configure(fg_color="transparent", text_color=M["fg_dim"])
        else:
            btn.configure(fg_color=M["btn"], text_color="white")
        self._notify()

    # --- UI HELPERS ---
    def _card(self, parent, title, row, col, rs=1, cs=1):
        f = ctk.CTkFrame(parent, corner_radius=10, fg_color=M["card"], border_width=1, border_color=M["border"])
        f.grid(row=row, column=col, rowspan=rs, columnspan=cs, sticky="nsew", padx=3, pady=3)
        ctk.CTkLabel(f, text=title, font=("Segoe UI", 12, "bold"), text_color=M["fg"]).pack(pady=(6, 2), padx=8,
                                                                                            anchor="w")
        ctk.CTkFrame(f, height=1, fg_color=M["border"]).pack(fill="x", padx=8, pady=(0, 4))
        return f

    def _tip(self, w, text):
        ModernToolTip(w, text)

    def _slider(self, parent, label, min_v, max_v, fmt="{:.0f}", tip=""):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=1)
        lbl = ctk.CTkLabel(row, text=label, text_color=M["fg_dim"], font=("Segoe UI", 10), width=65, anchor="w")
        lbl.pack(side="left")
        if tip:
            self._tip(lbl, tip)
        val = ctk.CTkLabel(row, text=fmt.format(min_v), text_color=M["accent"], font=("Segoe UI", 10, "bold"), width=35)
        val.pack(side="right")

        def upd(v):
            val.configure(text=fmt.format(v))
            self._notify()

        sl = ctk.CTkSlider(row, from_=min_v, to=max_v, button_color=M["accent"], button_hover_color=M["btn"],
                           progress_color=M["slider"], fg_color=M["slider_bg"], command=upd, height=12)
        sl.pack(side="right", fill="x", expand=True, padx=4)
        return sl, val

    def _switch(self, parent, text, tip="", cmd=None):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=8, pady=1)
        sw = ctk.CTkSwitch(f, text=text, font=("Segoe UI", 10), text_color=M["fg"],
                           progress_color=M["switch_on"], button_color=M["accent"], fg_color=M["switch_off"],
                           command=cmd or self._notify)
        sw.pack(side="left")
        if tip:
            self._tip(sw, tip)
        return sw

    def _sync_btns(self):
        if self.engine.running:
            self.btn_main.configure(text="⏹ STOP", fg_color=M["danger"])
            if hasattr(self, 'btn_extra'):
                self.btn_extra.configure(text="⏹ STOP", fg_color=M["danger"])
        else:
            self.btn_main.configure(text="▶ START", fg_color=M["success"])
            if hasattr(self, 'btn_extra'):
                self.btn_extra.configure(text="▶ START", fg_color=M["success"])

    def _switch_tab(self, val):
        if val == "⚙️ Settings":
            self.tab_extra.pack_forget()
            self.tab_main.pack(fill="both", expand=True, padx=6, pady=3)
        else:
            self.tab_main.pack_forget()
            self.tab_extra.pack(fill="both", expand=True, padx=6, pady=3)

    # --- BUILD UI ---
    def _build_ui(self):
        # Header
        hdr = ctk.CTkFrame(self.root, fg_color=M["header"], corner_radius=0, height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        top = ctk.CTkFrame(hdr, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(top, text="💗 Conditioning Dashboard", font=("Segoe UI", 16, "bold"), text_color="white").pack(
            side="left")
        self.preset_menu = ctk.CTkOptionMenu(top, values=[], command=self._handle_preset, fg_color=M["card"],
                                             button_color=M["btn"], text_color="white", height=26, width=110)
        self._update_preset_menu()
        self.preset_menu.pack(side="right", padx=6)
        self.preset_menu.set("DEFAULT")
        self.tabs = ctk.CTkSegmentedButton(top, values=["⚙️ Settings", "🎮 Progression"], command=self._switch_tab,
                                           selected_color=M["btn"], unselected_color=M["card"], text_color="white",
                                           font=("Segoe UI", 10))
        self.tabs.pack(side="right", padx=12)
        self.tabs.set("⚙️ Settings")

        # XP Bar
        xp = ctk.CTkFrame(hdr, fg_color=M["slider_bg"], height=22, corner_radius=0)
        xp.pack(fill="x", side="bottom")
        self.lbl_lvl = ctk.CTkLabel(xp, text="LVL 1", text_color=M["accent"], font=("Impact", 12))
        self.lbl_lvl.pack(side="left", padx=10)
        self.xp_bar = ctk.CTkProgressBar(xp, progress_color=M["xp_bar"], fg_color=M["card"], height=8, corner_radius=4)
        self.xp_bar.pack(side="left", fill="x", expand=True, padx=6)
        self.xp_bar.set(0)
        self.lbl_xp = ctk.CTkLabel(xp, text="0 / 70 XP", text_color=M["fg_dim"], font=("Segoe UI", 9))
        self.lbl_xp.pack(side="right", padx=10)

        # Content
        content = ctk.CTkFrame(self.root, fg_color="transparent")
        content.pack(fill="both", expand=True)
        self.tab_main = ctk.CTkFrame(content, fg_color="transparent")
        self.tab_extra = ctk.CTkFrame(content, fg_color="transparent")
        self._build_main(self.tab_main)
        self._build_extra(self.tab_extra)
        self._switch_tab("⚙️ Settings")

    def _build_main(self, p):
        p.columnconfigure(0, weight=1)
        p.columnconfigure(1, weight=1)
        p.columnconfigure(2, weight=2)  # Browser column
        p.rowconfigure(0, weight=1)  # Main content row

        # Col 1 - Flash, Visuals, Logo/Buttons
        c1 = ctk.CTkFrame(p, fg_color="transparent")
        c1.grid(row=0, column=0, sticky="nsew")

        # Flash
        cf = self._card(c1, "⚡ Flash Images", 0, 0)
        self.sw_flash = self._switch(cf, "Enable", "Show random images from your 'images' folder at set intervals.")
        self.sw_click = self._switch(cf, "Clickable",
                                     "ON: Click images to close them\nOFF: Ghost mode - images pass through clicks")
        self.sw_corrupt = self._switch(cf, "💀 Corruption",
                                       "ON: Clicking closes 1 but spawns 2 more (hydra effect)\nOFF: Clicking just closes the image")
        self.sl_freq, self.lb_freq = self._slider(cf, "Per Min", 1, 10,
                                                  tip="Flashes per minute. Higher = more frequent.")
        self.sl_img, self.lb_img = self._slider(cf, "Images", 1, 10, tip="Number of images per flash event.")
        self.sl_hydra, self.lb_hydra = self._slider(cf, "Max On Screen", 1, 20,
                                                    tip="Maximum images on screen at once.\nAutomatically stays >= Images count.")

        # Link sliders: Max must be >= Images (with proper label updates)
        def on_img_change(val):
            img_count = int(float(val))
            max_count = int(self.sl_hydra.get())
            self.lb_img.configure(text=str(img_count))
            # If max is less than images, bump it up
            if max_count < img_count:
                self.sl_hydra.set(img_count)
                self.lb_hydra.configure(text=str(img_count))
            self._notify()

        def on_max_change(val):
            max_count = int(float(val))
            img_count = int(self.sl_img.get())
            # Enforce minimum = images count
            if max_count < img_count:
                max_count = img_count
                self.sl_hydra.set(max_count)
            self.lb_hydra.configure(text=str(max_count))
            self._notify()

        self.sl_img.configure(command=on_img_change)
        self.sl_hydra.configure(command=on_max_change)

        # Visual
        cv = self._card(c1, "🎨 Visuals", 1, 0)
        self.sl_scale, self.lb_scale = self._slider(cv, "Size", 50, 250, "{:.0f}%", "Image size percentage.")
        self.sl_alpha, self.lb_alpha = self._slider(cv, "Opacity", 10, 100, "{:.0f}%", "Image transparency.")
        self.sl_fade, self.lb_fade = self._slider(cv, "Fade", 0, 100, "{:.0f}%", "Fade duration (0-1 sec).")

        # Logo + Buttons - BIGGER
        c1.rowconfigure(2, weight=1)
        logo_f = ctk.CTkFrame(c1, fg_color="transparent")
        logo_f.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)
        logo_f.grid_columnconfigure(0, weight=1)
        logo_f.grid_rowconfigure(0, weight=1)
        if self.icon_path:
            try:
                pil = Image.open(self.icon_path)
                w, h = pil.size
                tw = 280  # Logo size
                th = int(tw / (w / h))
                pil = pil.resize((tw, th), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=pil, dark_image=pil, size=(tw, th))
                ctk.CTkLabel(logo_f, text="", image=ctk_img).grid(row=0, column=0, pady=8)
            except:
                pass
        self.btn_main = ctk.CTkButton(logo_f, text="▶ START", fg_color=M["success"], hover_color=M["success_hover"],
                                      font=("Segoe UI", 16, "bold"), height=50, corner_radius=25,
                                      command=lambda: self._toggle(True))
        self.btn_main.grid(row=1, column=0, sticky="ew", padx=8, pady=(8, 5))
        bf = ctk.CTkFrame(logo_f, fg_color="transparent")
        bf.grid(row=2, column=0, sticky="ew", padx=8)
        bf.grid_columnconfigure(0, weight=1)
        bf.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(bf, text="💾 Save", fg_color=M["btn"], hover_color=M["btn_hover"], height=38,
                      font=("Segoe UI", 12, "bold"),
                      command=self._save_settings).grid(row=0, column=0, sticky="ew", padx=3)
        ctk.CTkButton(bf, text="🚪 Exit", fg_color=M["danger"], hover_color=M["danger_hover"], height=38,
                      font=("Segoe UI", 12, "bold"),
                      command=self._quit).grid(row=0, column=1, sticky="ew", padx=3)

        # Col 2 - Video, Subliminals, System (scrollable content)
        c2 = ctk.CTkFrame(p, fg_color="transparent")
        c2.grid(row=0, column=1, sticky="nsew")

        # Video
        cvid = self._card(c2, "🎬 Mandatory Video", 0, 0)
        vr = ctk.CTkFrame(cvid, fg_color="transparent")
        vr.pack(fill="x", padx=8, pady=2)
        self.sw_vid = ctk.CTkSwitch(vr, text="Enable", font=("Segoe UI", 10), text_color=M["fg"],
                                    progress_color=M["switch_on"], command=self._notify)
        self.sw_vid.pack(side="left")
        self._tip(self.sw_vid, "Play full-screen videos from 'startle_videos' folder.\nCannot be minimized or skipped.")
        ctk.CTkButton(vr, text="▶ Test", height=22, width=45, fg_color=M["accent_dim"],
                      command=lambda: self.engine.trigger_event("startle")).pack(side="right")
        self.sl_vfreq, self.lb_vfreq = self._slider(cvid, "Per Hour", 1, 20, tip="Videos per hour.")
        sr = ctk.CTkFrame(cvid, fg_color="transparent")
        sr.pack(fill="x", padx=8, pady=2)
        self.sw_strict = ctk.CTkSwitch(sr, text="⚠️ Strict Lock", text_color=M["danger"], progress_color=M["danger"],
                                       command=lambda: self._danger_check(self.sw_strict, "Strict Lock"))
        self.sw_strict.pack(side="left")
        self._tip(self.sw_strict, "⚠️ DANGER: Video CANNOT be closed!\nMust watch entire video. Use ESC to escape.")

        # Mini-game
        mg = ctk.CTkFrame(cvid, fg_color=M["slider_bg"], corner_radius=6)
        mg.pack(fill="x", padx=6, pady=4)
        ctk.CTkLabel(mg, text="🎯 Mini-Game", font=("Segoe UI", 10, "bold"), text_color=M["accent"]).pack(pady=(4, 2))
        self.sw_attn = self._switch(mg, "Enable", "Targets appear during video.\nMust click all or video replays!")
        self.sl_targ, self.lb_targ = self._slider(mg, "Targets", 1, 20, tip="Number of targets to spawn.")
        self.sl_tlife, self.lb_tlife = self._slider(mg, "Duration", 2, 10, tip="Seconds each target stays.")
        self.sl_tsize, self.lb_tsize = self._slider(mg, "Size", 20, 100, tip="Target text size.")
        ctk.CTkButton(mg, text="📝 Manage", fg_color=M["btn"], height=24, command=self._open_attn).pack(pady=4)

        # Subliminals
        cs = self._card(c2, "💭 Subliminals", 1, 0)
        subr = ctk.CTkFrame(cs, fg_color="transparent")
        subr.pack(fill="x", padx=8, pady=2)
        self.sw_sub = ctk.CTkSwitch(subr, text="Enable", font=("Segoe UI", 10), text_color=M["fg"],
                                    progress_color=M["switch_on"], command=self._notify)
        self.sw_sub.pack(side="left")
        self._tip(self.sw_sub, "Flash text messages briefly on screen.")
        ctk.CTkButton(subr, text="🎨", width=30, height=20, fg_color=M["accent"], command=self._style_editor).pack(
            side="right")
        self.sl_sfreq, self.lb_sfreq = self._slider(cs, "Per Min", 1, 30, tip="Subliminal messages per minute.")
        self.sl_sdur, self.lb_sdur = self._slider(cs, "Frames", 1, 10, tip="Duration in frames (longer = readable).")
        self.sl_sop, self.lb_sop = self._slider(cs, "Opacity", 10, 100, "{:.0f}%", "Text visibility.")
        ctk.CTkButton(cs, text="📝 Messages", fg_color=M["btn"], height=24, command=self._open_sub).pack(pady=3)
        saf = ctk.CTkFrame(cs, fg_color=M["slider_bg"], corner_radius=6)
        saf.pack(fill="x", padx=6, pady=4)
        self.sw_saud = self._switch(saf, "🔊 Audio Whispers", "Play audio from 'sub_audio' folder.")
        self.sl_svol, self.lb_svol = self._slider(saf, "Volume", 0, 100, "{:.0f}%", "Whisper volume.")

        # System - compact 2 columns
        csys = self._card(c2, "⚙️ System", 2, 0)
        sg = ctk.CTkFrame(csys, fg_color="transparent")
        sg.pack(fill="x", padx=6, pady=4)
        sg.grid_columnconfigure(0, weight=1)
        sg.grid_columnconfigure(1, weight=1)
        self.sw_dual = ctk.CTkSwitch(sg, text="Dual Mon", font=("Segoe UI", 9), text_color=M["fg"],
                                     command=self._notify)
        self.sw_dual.grid(row=0, column=0, sticky="w", padx=2, pady=2)
        self._tip(self.sw_dual, "Show effects on all monitors.")
        self.sw_startup = ctk.CTkSwitch(sg, text="Win Start", font=("Segoe UI", 9), text_color=M["fg"],
                                        command=lambda: self._danger_check(self.sw_startup, "Startup"))
        self.sw_startup.grid(row=0, column=1, sticky="w", padx=2, pady=2)
        self._tip(self.sw_startup, "⚠️ Start app with Windows.")
        self.sw_force = ctk.CTkSwitch(sg, text="Vid Launch", font=("Segoe UI", 9), text_color=M["fg"],
                                      command=self._notify)
        self.sw_force.grid(row=1, column=0, sticky="w", padx=2, pady=2)
        self._tip(self.sw_force, "Play video immediately on app start.")
        self.sw_auto = ctk.CTkSwitch(sg, text="Auto Run", font=("Segoe UI", 9), text_color=M["fg"],
                                     command=self._notify)
        self.sw_auto.grid(row=1, column=1, sticky="w", padx=2, pady=2)
        self._tip(self.sw_auto, "Start conditioning automatically.")
        self.sw_min = ctk.CTkSwitch(sg, text="Start Hidden", font=("Segoe UI", 9), text_color=M["fg"],
                                    command=self._notify)
        self.sw_min.grid(row=2, column=0, sticky="w", padx=2, pady=2)
        self._tip(self.sw_min, "Start minimized to tray.")
        self.sw_nopanic = ctk.CTkSwitch(sg, text="⚠️ No Panic", font=("Segoe UI", 9), text_color=M["danger"],
                                        command=lambda: self._danger_check(self.sw_nopanic, "Disable Panic"))
        self.sw_nopanic.grid(row=2, column=1, sticky="w", padx=2, pady=2)
        self._tip(self.sw_nopanic, "⚠️ DANGER: Disables ESC panic key!")

        # Col 3 - Browser + Audio stacked
        c3 = ctk.CTkFrame(p, fg_color="transparent")
        c3.grid(row=0, column=2, sticky="nsew")
        c3.rowconfigure(0, weight=3)  # Browser gets more space
        c3.rowconfigure(1, weight=1)  # Audio gets less
        c3.columnconfigure(0, weight=1)

        # Browser
        cb = self._card(c3, "🌐 Browser", 0, 0)
        cb.configure(height=350)  # Minimum height

        # Browser wrapper to allow overlay
        browser_wrapper = ctk.CTkFrame(cb, fg_color=M["slider_bg"], corner_radius=6)
        browser_wrapper.pack(fill="both", expand=True, padx=6, pady=6)

        # Themed header overlay to cover Chrome toolbar - MUST be tall enough
        self.browser_header = ctk.CTkFrame(browser_wrapper, fg_color=M["header"], height=45, corner_radius=0)
        self.browser_header.pack(fill="x", side="top")
        self.browser_header.pack_propagate(False)

        # Header content - looks like part of the app
        header_content = ctk.CTkFrame(self.browser_header, fg_color="transparent")
        header_content.pack(fill="both", expand=True, padx=10)
        header_content.grid_columnconfigure(0, weight=1)
        header_content.grid_rowconfigure(0, weight=1)

        left_frame = ctk.CTkFrame(header_content, fg_color="transparent")
        left_frame.pack(side="left", fill="y", pady=8)
        ctk.CTkLabel(left_frame, text="☁️ Bambi Cloud",
                     font=("Segoe UI", 12, "bold"), text_color=M["accent"]).pack(side="left")

        # Right side with status
        right_frame = ctk.CTkFrame(header_content, fg_color="transparent")
        right_frame.pack(side="right", fill="y", pady=8)
        self.browser_status = ctk.CTkLabel(right_frame, text="● Online",
                                           font=("Segoe UI", 10), text_color=M["success"])
        self.browser_status.pack(side="right")

        # Actual browser container below the header
        self.browser_container = ctk.CTkFrame(browser_wrapper, fg_color=M["slider_bg"], corner_radius=0)
        self.browser_container.pack(fill="both", expand=True)

        # Loading label (will be covered by browser once loaded)
        ctk.CTkLabel(self.browser_container, text="🌐 Loading...",
                     text_color=M["fg_dim"], font=("Segoe UI", 11)).place(relx=0.5, rely=0.5, anchor="center")

        # Audio
        ca = self._card(c3, "🔊 Audio", 1, 0)
        ar = ctk.CTkFrame(ca, fg_color="transparent")
        ar.pack(fill="x", padx=8, pady=4)
        self.sw_bgaud = ctk.CTkSwitch(ar, text="Background Audio", font=("Segoe UI", 10), text_color=M["fg"],
                                      progress_color=M["switch_on"], command=self._notify)
        self.sw_bgaud.pack(side="left")
        self._tip(self.sw_bgaud, "Enable ambient audio from web player.")
        self.sl_vol, self.lb_vol = self._slider(ca, "Master", 0, 100, "{:.0f}%", "Master volume for all sounds.")
        dr = ctk.CTkFrame(ca, fg_color="transparent")
        dr.pack(fill="x", padx=8, pady=4)
        self.sw_duck = ctk.CTkSwitch(dr, text="Audio Duck", font=("Segoe UI", 10), text_color=M["fg"],
                                     command=self._notify)
        self.sw_duck.pack(side="left")
        self._tip(self.sw_duck, "Lower system volume during effects.")
        self.sl_duck, self.lb_duck = self._slider(ca, "Duck %", 0, 100, "{:.0f}%", "How much to reduce other apps.")

    def _build_extra(self, p):
        p.columnconfigure(0, weight=1)
        p.columnconfigure(1, weight=1)
        for i in range(4):
            p.rowconfigure(i, weight=1 if i < 3 else 0)

        # Scheduler
        csc = self._card(p, "⏱️ Intensity Ramp", 0, 0)
        self.sw_sched = self._switch(csc, "Enable Ramping", "Gradually increase intensity over time.")
        self.sl_schdur, self.lb_schdur = self._slider(csc, "Duration", 10, 180, "{:.0f}m", "Minutes to reach max.")
        self.sl_schmult, self.lb_schmult = self._slider(csc, "Max Mult", 1.0, 5.0, "{:.1f}x",
                                                        "Maximum intensity multiplier.")
        self.sw_linkalpha = self._switch(csc, "Link Opacity", "Also increase image opacity over time.")
        self.sched_bar = ctk.CTkProgressBar(csc, progress_color=M["accent"], fg_color=M["slider_bg"], height=6)
        self.sched_bar.pack(fill="x", padx=8, pady=4)
        self.sched_bar.set(0)
        self.lbl_sched = ctk.CTkLabel(csc, text="Not active", font=("Segoe UI", 9), text_color=M["fg_dim"])
        self.lbl_sched.pack(pady=2)

        # Time Schedule
        ct = self._card(p, "📅 Time Schedule", 0, 1)
        self.sw_time = self._switch(ct, "Enable Schedule", "Only run during specific hours.")
        tr = ctk.CTkFrame(ct, fg_color="transparent")
        tr.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(tr, text="Start:", text_color=M["fg_dim"], font=("Segoe UI", 9)).pack(side="left")
        self.ent_start = ctk.CTkEntry(tr, width=55, fg_color=M["input_bg"], border_color=M["border"])
        self.ent_start.pack(side="left", padx=4)
        self._tip(self.ent_start, "Start time (24h format, e.g. 14:00)")
        ctk.CTkLabel(tr, text="End:", text_color=M["fg_dim"], font=("Segoe UI", 9)).pack(side="left", padx=(10, 0))
        self.ent_end = ctk.CTkEntry(tr, width=55, fg_color=M["input_bg"], border_color=M["border"])
        self.ent_end.pack(side="left", padx=4)
        self._tip(self.ent_end, "End time (24h format, e.g. 18:00)")
        df = ctk.CTkFrame(ct, fg_color="transparent")
        df.pack(fill="x", padx=8, pady=4)
        self.day_btns = []
        for d in ["M", "T", "W", "T", "F", "S", "S"]:
            b = ctk.CTkButton(df, text=d, width=28, height=26, fg_color=M["btn"], hover_color=M["btn_hover"])
            b.pack(side="left", padx=1)
            b.configure(command=lambda btn=b: self._toggle_day(btn))
            self.day_btns.append(b)

        # Level 10
        c10 = self._card(p, "🔮 Level 10 Unlocks", 1, 0)
        self.lv10_locked = ctk.CTkFrame(c10, fg_color="transparent")
        self.lv10_unlocked = ctk.CTkFrame(c10, fg_color="transparent")
        ctk.CTkLabel(self.lv10_locked, text="🔒 Reach Level 10\n\n• Spiral Overlay\n• Pink Filter",
                     font=("Segoe UI", 11), text_color=M["fg_dim"]).pack(expand=True, pady=15)
        self.sw_spiral = self._switch(self.lv10_unlocked, "🌀 Spiral Overlay", "Display animated spiral GIF.")
        spr = ctk.CTkFrame(self.lv10_unlocked, fg_color="transparent")
        spr.pack(fill="x", padx=8, pady=2)
        ctk.CTkButton(spr, text="📁 GIF", fg_color=M["btn"], height=24, command=self._pick_spiral).pack(side="left")
        self.sl_spirop, self.lb_spirop = self._slider(self.lv10_unlocked, "Opacity", 5, 50, "{:.0f}%",
                                                      "Spiral visibility.")
        self.sw_spirlink = self._switch(self.lv10_unlocked, "Link Ramp", "Increase with intensity.")
        ctk.CTkFrame(self.lv10_unlocked, height=1, fg_color=M["border"]).pack(fill="x", padx=8, pady=6)
        self.sw_pink = self._switch(self.lv10_unlocked, "💗 Pink Filter", "Apply pink tint to screen.")
        self.sl_pinkop, self.lb_pinkop = self._slider(self.lv10_unlocked, "Intensity", 5, 50, "{:.0f}%",
                                                      "Pink strength.")
        self.sw_pinklink = self._switch(self.lv10_unlocked, "Link Ramp", "Increase with intensity.")
        self.lv10_locked.pack(fill="both", expand=True, padx=5, pady=5)

        # Level 20
        c20 = self._card(p, "🎈 Level 20 Unlocks", 1, 1)
        self.lv20_locked = ctk.CTkFrame(c20, fg_color="transparent")
        self.lv20_unlocked = ctk.CTkFrame(c20, fg_color="transparent")
        ctk.CTkLabel(self.lv20_locked, text="🔒 Reach Level 20\n\n• Bubble Pop Game",
                     font=("Segoe UI", 11), text_color=M["fg_dim"]).pack(expand=True, pady=15)
        self.sw_bub = self._switch(self.lv20_unlocked, "🫧 Bubbles", "Floating bubbles to pop for XP!")
        self.sl_bubfreq, self.lb_bubfreq = self._slider(self.lv20_unlocked, "Per Min", 1, 15, tip="Bubbles per minute.")
        self.sw_bublink = self._switch(self.lv20_unlocked, "Link Ramp", "Increase with intensity.")
        self.lv20_locked.pack(fill="both", expand=True, padx=5, pady=5)

        # Future
        c50 = self._card(p, "🔥 Level 50", 2, 0)
        ctk.CTkLabel(c50, text="🔒 Coming Soon...", font=("Segoe UI", 11), text_color=M["fg_dim"]).pack(expand=True,
                                                                                                       pady=15)
        c100 = self._card(p, "👑 Level 100", 2, 1)
        ctk.CTkLabel(c100, text="🔒 Coming Soon...", font=("Segoe UI", 11), text_color=M["fg_dim"]).pack(expand=True,
                                                                                                        pady=15)

        # Buttons
        bf = ctk.CTkFrame(p, fg_color="transparent")
        bf.grid(row=3, column=0, columnspan=2, pady=8, sticky="ew")
        bf.grid_columnconfigure(0, weight=1)
        bf.grid_columnconfigure(1, weight=1)
        bf.grid_columnconfigure(2, weight=1)
        self.btn_extra = ctk.CTkButton(bf, text="▶ START", fg_color=M["success"], hover_color=M["success_hover"],
                                       font=("Segoe UI", 13, "bold"), height=38, corner_radius=18,
                                       command=lambda: self._toggle(True))
        self.btn_extra.grid(row=0, column=0, padx=6, sticky="ew")
        ctk.CTkButton(bf, text="💾 Save", fg_color=M["btn"], hover_color=M["btn_hover"], height=38,
                      command=self._save_settings).grid(row=0, column=1, padx=6, sticky="ew")
        ctk.CTkButton(bf, text="🚪 Exit", fg_color=M["danger"], hover_color=M["danger_hover"], height=38,
                      command=self._quit).grid(row=0, column=2, padx=6, sticky="ew")

    def _pick_spiral(self):
        path = filedialog.askopenfilename(title="Select Spiral GIF", filetypes=[("GIF", "*.gif")])
        if path:
            self.settings["spiral_path"] = path
            self._notify()

    def _toggle(self, manual=True):
        if self.engine.running:
            self.engine.stop()
            self._sync_btns()
        else:
            self.engine.start(is_startup=not manual)
            self.btn_main.configure(text="⏹ STOP", fg_color=M["danger"])
            if hasattr(self, 'btn_extra'):
                self.btn_extra.configure(text="⏹ STOP", fg_color=M["danger"])

    def _update_scheduler(self, prog, mult, remain):
        self.sched_bar.set(prog)
        cur = 1.0 + ((mult - 1.0) * prog)
        m, s = divmod(int(remain), 60)
        self.lbl_sched.configure(text=f"{cur:.1f}x | {m}m {s}s left")

    def _update_xp(self, level, prog, cur, need):
        old = self.settings.get('player_level', 1)
        self.lbl_lvl.configure(text=f"LVL {level}")
        self.xp_bar.set(prog)
        self.lbl_xp.configure(text=f"{int(cur)} / {int(need)} XP")
        if level != old:
            self.settings['player_level'] = level
            self._check_unlocks(level)

    def _get_values(self):
        days = [i for i, b in enumerate(self.day_btns) if b._fg_color == M["btn"]]
        lvl = self.engine.settings.get('player_level', 1) if hasattr(self, 'engine') else self.settings.get(
            'player_level', 1)
        xp = self.engine.settings.get('player_xp', 0.0) if hasattr(self, 'engine') else self.settings.get('player_xp',
                                                                                                          0.0)
        return {
            "player_level": lvl, "player_xp": xp,
            "flash_enabled": self.sw_flash.get(), "flash_freq": int(self.sl_freq.get()),
            "flash_clickable": self.sw_click.get(), "flash_corruption": self.sw_corrupt.get(),
            "flash_hydra_limit": min(int(self.sl_hydra.get()), 20),
            "startle_enabled": self.sw_vid.get(), "startle_freq": int(self.sl_vfreq.get()),
            "startle_strict": self.sw_strict.get(),
            "subliminal_enabled": self.sw_sub.get(), "subliminal_freq": int(self.sl_sfreq.get()),
            "subliminal_duration": int(self.sl_sdur.get()), "subliminal_opacity": self.sl_sop.get() / 100.0,
            "subliminal_pool": self.settings['subliminal_pool'],
            "sub_bg_color": self.settings.get("sub_bg_color", "#000000"),
            "sub_bg_transparent": self.settings.get("sub_bg_transparent", False),
            "sub_text_color": self.settings.get("sub_text_color", "#FF00FF"),
            "sub_text_transparent": self.settings.get("sub_text_transparent", False),
            "sub_border_color": self.settings.get("sub_border_color", "#FFFFFF"),
            "sub_audio_enabled": self.sw_saud.get(), "sub_audio_volume": self.sl_svol.get() / 100.0,
            "bg_audio_enabled": self.sw_bgaud.get(), "bg_audio_max": 15,
            "fade_duration": self.sl_fade.get() / 100.0, "volume": self.sl_vol.get() / 100.0,
            "audio_ducking_enabled": self.sw_duck.get(), "audio_ducking_strength": int(self.sl_duck.get()),
            "dual_monitor": self.sw_dual.get(), "sim_images": int(self.sl_img.get()),
            "image_scale": self.sl_scale.get() / 100.0, "image_alpha": self.sl_alpha.get() / 100.0,
            "run_on_startup": self.sw_startup.get(), "force_startle_on_launch": self.sw_force.get(),
            "start_minimized": self.sw_min.get(), "auto_start_engine": self.sw_auto.get(),
            "last_preset": self.preset_menu.get(), "disable_panic_esc": self.sw_nopanic.get(),
            "attention_enabled": self.sw_attn.get(), "attention_pool": self.settings['attention_pool'],
            "attention_density": int(self.sl_targ.get()), "attention_lifespan": int(self.sl_tlife.get()),
            "attention_size": int(self.sl_tsize.get()),
            "scheduler_enabled": self.sw_sched.get(), "scheduler_duration_min": int(self.sl_schdur.get()),
            "scheduler_multiplier": float(self.sl_schmult.get()), "scheduler_link_alpha": self.sw_linkalpha.get(),
            "time_schedule_enabled": self.sw_time.get(), "time_start_str": self.ent_start.get(),
            "time_end_str": self.ent_end.get(), "active_weekdays": days,
            "pink_filter_enabled": self.sw_pink.get(), "pink_filter_opacity": self.sl_pinkop.get() / 100.0,
            "pink_filter_link_ramp": self.sw_pinklink.get(),
            "spiral_enabled": self.sw_spiral.get(), "spiral_path": self.settings.get("spiral_path", ""),
            "spiral_opacity": self.sl_spirop.get() / 100.0, "spiral_link_ramp": self.sw_spirlink.get(),
            "bubbles_enabled": self.sw_bub.get(), "bubbles_freq": int(self.sl_bubfreq.get()),
            "bubbles_link_ramp": self.sw_bublink.get(),
        }

    def _notify(self, e=None):
        s = self._get_values()
        self.settings = s
        self.engine.update_settings(s)

    def _style_editor(self):
        d = ctk.CTkToplevel(self.root)
        d.title("Subliminal Styles")
        d.geometry("300x380")
        d.configure(fg_color=M["bg"])
        d.attributes('-topmost', True)

        def pick(k):
            c = colorchooser.askcolor()[1]
            if c:
                self.settings[k] = c
                self._notify()

        def tog(k, v):
            self.settings[k] = bool(v.get())
            self._notify()

        ctk.CTkLabel(d, text="Background", font=("Segoe UI", 12, "bold"), text_color=M["fg"]).pack(pady=10)
        ctk.CTkButton(d, text="Pick Color", fg_color=M["btn"], command=lambda: pick("sub_bg_color")).pack(pady=4)
        bv = ctk.BooleanVar(value=self.settings.get("sub_bg_transparent", False))
        ctk.CTkCheckBox(d, text="Transparent", variable=bv, text_color=M["fg"],
                        command=lambda: tog("sub_bg_transparent", bv)).pack(pady=4)
        ctk.CTkLabel(d, text="Text", font=("Segoe UI", 12, "bold"), text_color=M["fg"]).pack(pady=10)
        ctk.CTkButton(d, text="Pick Color", fg_color=M["btn"], command=lambda: pick("sub_text_color")).pack(pady=4)
        tv = ctk.BooleanVar(value=self.settings.get("sub_text_transparent", False))
        ctk.CTkCheckBox(d, text="Transparent", variable=tv, text_color=M["fg"],
                        command=lambda: tog("sub_text_transparent", tv)).pack(pady=4)
        ctk.CTkLabel(d, text="Border", font=("Segoe UI", 12, "bold"), text_color=M["fg"]).pack(pady=10)
        ctk.CTkButton(d, text="Pick Color", fg_color=M["btn"], command=lambda: pick("sub_border_color")).pack(pady=4)
        ctk.CTkButton(d, text="Close", fg_color=M["card"], command=d.destroy).pack(pady=15)

    def _open_sub(self):
        TextManagerDialog(self.root, "Subliminals", self.settings['subliminal_pool'], self._notify)

    def _open_attn(self):
        TextManagerDialog(self.root, "Targets", self.settings['attention_pool'], self._notify)

    def _apply_settings(self, s):
        def sw(w, v):
            w.select() if v else w.deselect()

        def sl(w, l, v, f="{:.0f}"):
            w.set(v)
            l.configure(text=f.format(v))

        sw(self.sw_flash, s.get('flash_enabled', True))
        sl(self.sl_freq, self.lb_freq, s.get('flash_freq', 2))
        sw(self.sw_click, s.get('flash_clickable', True))
        sw(self.sw_corrupt, s.get('flash_corruption', False))
        sl(self.sl_img, self.lb_img, s.get('sim_images', 5))
        sl(self.sl_hydra, self.lb_hydra, min(s.get('flash_hydra_limit', 20), 20))
        sw(self.sw_vid, s.get('startle_enabled', True))
        sl(self.sl_vfreq, self.lb_vfreq, s.get('startle_freq', 6))
        sw(self.sw_strict, s.get('startle_strict', False))
        sw(self.sw_sub, s.get('subliminal_enabled', False))
        sl(self.sl_sfreq, self.lb_sfreq, s.get('subliminal_freq', 5))
        sl(self.sl_sdur, self.lb_sdur, s.get('subliminal_duration', 2))
        sl(self.sl_sop, self.lb_sop, s.get('subliminal_opacity', 0.8) * 100, "{:.0f}%")
        sw(self.sw_saud, s.get('sub_audio_enabled', False))
        sl(self.sl_svol, self.lb_svol, s.get('sub_audio_volume', 0.5) * 100, "{:.0f}%")
        sw(self.sw_bgaud, s.get('bg_audio_enabled', True))
        sl(self.sl_fade, self.lb_fade, s.get('fade_duration', 0.4) * 100, "{:.0f}%")
        sl(self.sl_vol, self.lb_vol, s.get('volume', 0.32) * 100, "{:.0f}%")
        sw(self.sw_duck, s.get('audio_ducking_enabled', True))
        sl(self.sl_duck, self.lb_duck, s.get('audio_ducking_strength', 100), "{:.0f}%")
        sw(self.sw_dual, s.get('dual_monitor', True))
        sl(self.sl_scale, self.lb_scale, s.get('image_scale', 0.9) * 100, "{:.0f}%")
        sl(self.sl_alpha, self.lb_alpha, s.get('image_alpha', 1.0) * 100, "{:.0f}%")
        sw(self.sw_startup, s.get('run_on_startup', False))
        sw(self.sw_force, s.get('force_startle_on_launch', False))
        sw(self.sw_auto, s.get('auto_start_engine', False))
        sw(self.sw_min, s.get('start_minimized', False))
        sw(self.sw_nopanic, s.get('disable_panic_esc', False))
        sw(self.sw_attn, s.get('attention_enabled', False))
        sl(self.sl_targ, self.lb_targ, s.get('attention_density', 3))
        sl(self.sl_tlife, self.lb_tlife, s.get('attention_lifespan', 5))
        sl(self.sl_tsize, self.lb_tsize, s.get('attention_size', 70))
        sw(self.sw_sched, s.get('scheduler_enabled', False))
        sl(self.sl_schdur, self.lb_schdur, s.get('scheduler_duration_min', 60), "{:.0f}m")
        sl(self.sl_schmult, self.lb_schmult, s.get('scheduler_multiplier', 1.0), "{:.1f}x")
        sw(self.sw_linkalpha, s.get('scheduler_link_alpha', False))
        sw(self.sw_time, s.get('time_schedule_enabled', False))
        self.ent_start.delete(0, 'end')
        self.ent_start.insert(0, s.get('time_start_str', "16:00"))
        self.ent_end.delete(0, 'end')
        self.ent_end.insert(0, s.get('time_end_str', "18:00"))
        days = s.get('active_weekdays', [0, 1, 2, 3, 4, 5, 6])
        for i, b in enumerate(self.day_btns):
            if i in days:
                b.configure(fg_color=M["btn"], text_color="white")
            else:
                b.configure(fg_color="transparent", text_color=M["fg_dim"])
        sw(self.sw_spiral, s.get('spiral_enabled', False))
        sl(self.sl_spirop, self.lb_spirop, s.get('spiral_opacity', 0.1) * 100, "{:.0f}%")
        sw(self.sw_spirlink, s.get('spiral_link_ramp', False))
        sw(self.sw_pink, s.get('pink_filter_enabled', False))
        sl(self.sl_pinkop, self.lb_pinkop, s.get('pink_filter_opacity', 0.1) * 100, "{:.0f}%")
        sw(self.sw_pinklink, s.get('pink_filter_link_ramp', False))
        sw(self.sw_bub, s.get('bubbles_enabled', False))
        sl(self.sl_bubfreq, self.lb_bubfreq, s.get('bubbles_freq', 5))
        sw(self.sw_bublink, s.get('bubbles_link_ramp', False))