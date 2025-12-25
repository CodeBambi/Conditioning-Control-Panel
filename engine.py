"""
Flash Engine Module for Conditioning Control Panel
===================================================
Core engine that handles:
- Flash images display
- Video playback
- Subliminal messages
- Audio control
- Event scheduling
"""

import os
import time
import random
import threading
import glob
import subprocess
import datetime
import math
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Dict, List, Any, Callable

from PIL import Image, ImageTk
import cv2
import pygame
import imageio.v3 as iio
import imageio_ffmpeg
from ctypes import windll

# Initialize logging
try:
    from security import logger, sanitize_path, validate_file_extension
except ImportError:
    import logging
    logger = logging.getLogger("ConditioningPanel")
    def sanitize_path(p, d=""): return p
    def validate_file_extension(p, c): return True

try:
    from screeninfo import get_monitors
    SCREENINFO_AVAILABLE = True
except ImportError:
    SCREENINFO_AVAILABLE = False
    logger.info("screeninfo not available - multi-monitor support disabled")

# Import from our modules
from config import (
    ASSETS_DIR, IMG_DIR, SND_DIR, SUB_AUDIO_DIR, STARTLE_VID_DIR,
    TEMP_AUDIO_FILE, DEFAULT_SETTINGS
)

# Try new config imports, fall back gracefully
try:
    from config import LIMITS, validate_limits
except ImportError:
    LIMITS = {"max_images_on_screen": 20, "max_videos_per_hour": 20}
    def validate_limits(s): return s

# Try new utils imports, fall back to old
try:
    from utils import AudioDucker, safe_load_json, safe_save_json
except ImportError:
    try:
        from utils import SystemAudioDucker as AudioDucker
    except ImportError:
        # Create dummy ducker
        class AudioDucker:
            def __init__(self): pass
            def duck(self, strength=80): pass
            def unduck(self): pass
    
    import json
    def safe_load_json(fp, default=None):
        try:
            with open(fp, 'r') as f: return json.load(f)
        except (IOError, OSError, json.JSONDecodeError): return default or {}
    def safe_save_json(fp, data):
        try:
            with open(fp, 'w') as f: json.dump(data, f, indent=2)
            return True
        except (IOError, OSError, TypeError): return False

from browser import BrowserManager
from ui_components import TransparentTextWindow
from progression_system import ProgressionSystem


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

        # Sub-systems
        self.ducker = AudioDucker()
        self.browser = BrowserManager()
        self.progression = ProgressionSystem(self)

        self.penalty_loop_count = 0

        # Callbacks
        self.gui_update_callback = None
        self.scheduler_update_callback = None
        self.xp_update_callback = None

        # Game Stats
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
            logger.info("Pygame audio initialized")
        except pygame.error as e:
            logger.error(f"Failed to initialize pygame audio: {e}")

        self.load_gj_sound()

        # Watchers
        self.esc_listener_active = True
        self.esc_thread = threading.Thread(target=self._monitor_global_esc, daemon=True)
        self.esc_thread.start()
        self.clock_monitor_thread = threading.Thread(target=self._monitor_time_schedule, daemon=True)
        self.clock_monitor_thread.start()

        self.heartbeat()

    def _monitor_global_esc(self):
        import ctypes
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
                logger.debug(f"Loaded GJ sound: {found[0]}")
            except pygame.error as e:
                logger.warning(f"Could not load GJ sound: {e}")

    def play_gj(self):
        if self.gj_sound:
            try:
                self.gj_sound.play()
            except pygame.error as e:
                logger.debug(f"Could not play GJ sound: {e}")

    def update_settings(self, new_settings):
        needs_reschedule = False
        check_keys = ['min_interval', 'max_interval', 'flash_enabled', 'subliminal_enabled', 'subliminal_freq',
                      'startle_enabled', 'startle_freq', 'sub_audio_enabled']
        for k in check_keys:
            if new_settings.get(k) != self.settings.get(k): needs_reschedule = True; break
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

        # Check Unlocks Immediately
        lvl = self.settings.get('player_level', 1)
        self.progression.check_unlocks(lvl)

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

        if key == 'flash_freq':
            # Increase frequency with intensity (more flashes as ramp progresses)
            target = min(10, val * multiplier)
            return val + ((target - val) * progress)
        elif key == 'startle_freq':
            target = min(35, val * multiplier)
            return int(val + ((target - val) * progress))
        elif key == 'subliminal_freq':
            target = min(30, val * multiplier)
            return int(val + ((target - val) * progress))
        elif key == 'volume':
            bonus = (multiplier - 1.0) * 0.15
            target = val + bonus
            current_vol = val + ((target - val) * progress)
            return min(0.8, current_vol)  # Cap at 80% to avoid being too loud
        return val

    def _update_scheduler_progress(self):
        if not self.running or not self.settings.get('scheduler_enabled', False):
            self.current_intensity_progress = 0.0
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
        self.running = False
        self.busy = False
        self.video_running = False
        try:
            pygame.mixer.stop()
        except pygame.error as e:
            logger.debug(f"Could not stop pygame mixer: {e}")
        self.ducker.unduck()

        # Pop all active bubbles (plays sounds)
        try:
            from bubble_game import Bubble
            Bubble.pop_all()
        except ImportError:
            pass  # Module not available
        except Exception as e:
            logger.debug(f"Could not pop bubbles: {e}")

        for win in self.active_windows:
            try:
                win.destroy()
            except tk.TclError:
                pass  # Window already destroyed
        self.active_windows.clear()
        self.active_rects.clear()

        for t in self.active_floating_texts:
            try:
                t.destroy()
            except tk.TclError:
                pass  # Window already destroyed
        self.active_floating_texts.clear()

        # Shutdown progression visuals
        self.progression.shutdown()

        # Reset resource manager
        try:
            from progression_system import resource_mgr
            resource_mgr.active_effects['flashes'] = 0
            resource_mgr.active_effects['bubbles'] = 0
            resource_mgr.flash_waiting = False
        except ImportError:
            pass  # Module not available
        except (KeyError, AttributeError) as e:
            logger.debug(f"Could not reset resource manager: {e}")

        if hasattr(self, 'cap') and self.cap: self.cap.release()
        self.events_pending_reschedule.clear()
        self.strict_active = False
        try:
            self.root.deiconify()
            self.root.lift()
        except tk.TclError as e:
            logger.debug(f"Could not restore window: {e}")

    def schedule_next(self, event_type):
        if not self.running: return
        seconds = 10
        if event_type == "startle":
            base_freq = max(1, self.settings.get('startle_freq', 10))
            eff_freq = self.get_effective_value('startle_freq', base_freq)
            seconds = int((60 / max(1, eff_freq)) * 60) + random.randint(-30, 30)
            seconds = max(5, seconds)
        elif event_type == "flash":
            # Use flash_freq (flashes per minute)
            base_freq = max(0.5, self.settings.get('flash_freq', 2))
            eff_freq = self.get_effective_value('flash_freq', base_freq)
            base = 60 / max(0.5, eff_freq)  # Seconds between flashes
            seconds = base + random.uniform(-base * 0.3, base * 0.3)  # ±30% variance
            seconds = max(3, seconds)  # Minimum 3 seconds
        elif event_type == "subliminal":
            base_freq = max(1, self.settings.get('subliminal_freq', 10))
            eff_freq = self.get_effective_value('subliminal_freq', base_freq)
            base = 60 / max(1, eff_freq)
            seconds = base + random.uniform(-base * 0.2, base * 0.2)
            seconds = max(1, seconds)
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
        except FileNotFoundError as e:
            logger.warning(f"FFmpeg not found: {e}")
        except subprocess.SubprocessError as e:
            logger.warning(f"Audio extraction failed: {e}")
        return None

    def _do_duck(self):
        if self.settings.get('audio_ducking_enabled', True):
            strength = self.settings.get('audio_ducking_strength', 100)
            self.ducker.duck(strength)

    def _duck_subliminal_channel(self, should_duck):
        try:
            sub_vol = self.settings.get('sub_audio_volume', 0.5)
            curved_vol = max(0.05, sub_vol ** 1.5)  # Gentler curve, minimum 5%
            if should_duck:
                pygame.mixer.Channel(2).set_volume(curved_vol * 0.3)  # 30% during duck
            else:
                pygame.mixer.Channel(2).set_volume(curved_vol)
        except pygame.error as e:
            logger.debug(f"Could not adjust subliminal channel: {e}")

    def trigger_event(self, event_type, strict_override=False):
        if not self.running: return

        if event_type == "subliminal":
            self._flash_subliminal()
            self.schedule_next("subliminal")
            return

        if event_type == "startle":
            if self.video_running: self.events_pending_reschedule.add(event_type); return
            self.busy = True
            
            # Signal to progression system that video is coming - this will:
            # - Pop all bubbles (with sounds)
            # - Hide/stop spiral
            # - Hide pink filter
            try:
                self.progression.prepare_for_video()
            except AttributeError:
                pass  # Progression not initialized
            except Exception as e:
                logger.debug(f"Could not prepare for video: {e}")
            
            # Stop any currently playing flash sounds
            try:
                pygame.mixer.stop()
            except pygame.error as e:
                logger.debug(f"Could not stop mixer: {e}")
            
            # Clear any active flash windows immediately
            for win in self.active_windows[:]:
                try:
                    win.destroy()
                except tk.TclError:
                    pass  # Already destroyed
            self.active_windows.clear()
            self.active_rects.clear()
            
            # Reset resource manager flash count
            try:
                from progression_system import resource_mgr
                resource_mgr.active_effects['flashes'] = 0
                resource_mgr.active_effects['bubbles'] = 0
            except ImportError:
                pass  # Module not available
            except (KeyError, AttributeError) as e:
                logger.debug(f"Could not reset resource manager: {e}")
            
            # Wait 4 seconds to let resources free up
            video_path = self.get_next_media('startle', self.paths['startle_videos'])
            if not video_path: self.busy = False; return
            is_strict = self.settings.get('startle_strict', False) or strict_override
            self.penalty_loop_count = 0
            
            # Schedule the actual video prep after delay
            self.root.after(4000, lambda: self._delayed_startle_prep(video_path, is_strict))
            return
        else:
            if not self.settings.get('flash_enabled', True): return
            self.events_pending_reschedule.add(event_type)
            if len(self.active_windows) > 0 or self.busy or self.video_running: return
            self.busy = True

        if event_type == "flash":
            self._flash_images()
    
    def _delayed_startle_prep(self, video_path, is_strict):
        """Called after 4 second delay to start video"""
        if not self.running:
            self.busy = False
            return
        threading.Thread(target=self._prep_startle_video, args=(video_path, is_strict), daemon=True).start()

    def _flash_images(self):
        # Check if video is pending - if so, skip flash entirely
        try:
            from progression_system import resource_mgr
            if resource_mgr.is_video_active():
                self.busy = False
                return
            
            if not resource_mgr.request_flash():
                # Bubbles active, retry in 500ms
                self.busy = False
                self.root.after(500, self._retry_flash)
                return
        except ImportError:
            pass  # Module not available
        except Exception as e:
            logger.debug(f"Resource manager check failed: {e}")
        
        media_pool = self.get_files(self.paths['images'])
        sound_pool = self.get_files(self.paths['sounds'])
        if not media_pool: self.busy = False; return
        sound_path = random.choice(sound_pool) if sound_pool else None
        monitors = self._get_monitors_safe()
        
        # Use single sim_images value with small variance
        base_images = max(1, self.settings.get('sim_images', 5))
        max_allowed = min(self.settings.get('flash_hydra_limit', 20), 20)  # Hard cap at 20
        
        # Reduce image count when spiral is active to prevent overload
        try:
            from progression_system import resource_mgr
            if resource_mgr.active_effects.get('spiral', False):
                base_images = min(base_images, 3)  # Max 3 images when spiral active
                max_allowed = min(max_allowed, 8)
        except ImportError:
            pass  # Module not available
        except (KeyError, AttributeError) as e:
            logger.debug(f"Resource manager check failed: {e}")
        
        # Clamp base_images to max allowed
        base_images = min(base_images, max_allowed)
        num_images = max(1, base_images + random.randint(-1, 1))  # ±1 variance
        num_images = min(num_images, max_allowed)  # Cap at max allowed
        selected_images = []
        for _ in range(num_images):
            img = self.get_next_media('flash', self.paths['images'])
            if img: selected_images.append(img)
        if not selected_images: self.busy = False; return
        base_scale = self.settings.get('image_scale', 1.0)
        threading.Thread(target=self._background_loader,
                         args=(selected_images, sound_path, False, False, monitors, base_scale), daemon=True).start()

    def _retry_flash(self):
        """Retry flash after waiting for bubbles"""
        if not self.running:
            return
        try:
            from progression_system import resource_mgr
            if resource_mgr.has_active_bubbles():
                # Still bubbles, wait more
                self.root.after(300, self._retry_flash)
                return
            resource_mgr.flash_done_waiting()
        except ImportError:
            pass  # Module not available
        except (AttributeError, KeyError) as e:
            logger.debug(f"Resource manager retry check failed: {e}")
        self.busy = True
        self._flash_images()

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
            if os.path.exists(path): linked_audio_path = path; break
            path_lower = os.path.join(self.paths['sub_audio'], clean_text.lower() + ext)
            if os.path.exists(path_lower): linked_audio_path = path_lower; break

        if linked_audio_path and self.settings.get('sub_audio_enabled', False):
            self._do_duck()
            try:
                snd = pygame.mixer.Sound(linked_audio_path)
                vol = self.settings.get('sub_audio_volume', 0.5)
                curved_vol = max(0.05, vol ** 1.5)  # Gentler curve, minimum 5%
                chan = pygame.mixer.Channel(2)
                chan.set_volume(curved_vol)
                chan.play(snd)
                length = snd.get_length()
                self._add_xp(1)
                self.root.after(int(length * 1000) + 500, self.ducker.unduck)
            except pygame.error as e:
                logger.debug(f"Could not play subliminal audio: {e}")
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
            except (OSError, AttributeError) as e:
                logger.debug(f"Could not set window style: {e}")
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
                raw = get_monitors()
                monitors = [{'x': m.x, 'y': m.y, 'width': m.width, 'height': m.height, 'is_primary': m.is_primary} for m
                            in raw]
            except Exception as e:
                logger.debug(f"Could not get monitors: {e}")
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
        try:
            win.attributes("-toolwindow", 1)
        except tk.TclError as e:
            logger.debug(f"Could not set toolwindow: {e}")
        if is_strict:
            win.protocol("WM_DELETE_WINDOW", lambda: None)
            win.bind('<Alt-F4>', lambda e: "break")
            win.bind("<Tab>", lambda e: "break")
            win.bind("<Alt-Tab>", lambda e: "break")
            win.lift()
            win.focus_force()
        else:
            try:
                hwnd = windll.user32.GetParent(win.winfo_id())
                windll.user32.SetWindowLongW(hwnd, -20, 0x08000000 | 0x00000008)
            except (OSError, AttributeError) as e:
                logger.debug(f"Could not set window style: {e}")

    def _prep_startle_video(self, video_path, is_strict):
        audio_path = self.extract_audio_from_video(video_path)
        self.root.after(0, lambda: self._start_startle_player(video_path, audio_path, is_strict))

    def _start_startle_player(self, video_path, audio_path, is_strict):
        if not self.running: self.busy = False; return
        pygame.mixer.stop()
        for win in list(self.active_windows):
            try:
                win.destroy()
            except tk.TclError:
                pass  # Window already destroyed
        self.active_windows.clear()
        self.active_rects.clear()
        if is_strict:
            self.strict_active = True
            try:
                self.root.withdraw()
                self.root.update()
            except tk.TclError as e:
                logger.debug(f"Could not withdraw window: {e}")
        else:
            self.strict_active = False

        self.video_running = True
        
        # Notify progression system that video started
        try:
            self.progression.video_started()
        except AttributeError:
            pass  # Progression not initialized
        except Exception as e:
            logger.debug(f"Could not notify video start: {e}")
        
        self._do_duck()
        self._duck_subliminal_channel(True)
        self.attention_spawns = []
        self.targets_hit = 0
        self.targets_total = 0
        self.session_targets_clicked = 0
        self.retry_video_path = None
        self._add_xp(50, is_video_context=True)

        if audio_path and os.path.exists(audio_path):
            try:
                self.vid_sound = pygame.mixer.Sound(audio_path)
                self.vid_channel = pygame.mixer.Channel(1)
                vol = self.settings.get('volume', 1.0)
                curved_vol = max(0.05, vol ** 1.5)  # Gentler curve, minimum 5%
                self.vid_channel.set_volume(curved_vol)
                self.vid_channel.play(self.vid_sound)
            except pygame.error as e:
                logger.warning(f"Could not play video audio: {e}")

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
                for _ in range(count): t = random.uniform(2.0, safe_end); self.attention_spawns.append(t)
                self.attention_spawns.sort()
                self.retry_video_path = video_path

        self.video_windows = []
        monitors = self._get_monitors_safe()
        for m in monitors:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True)
            win.config(bg='black')
            win.geometry(f"{m['width']}x{m['height']}+{m['x']}+{m['y']}")
            win.attributes('-topmost', True)
            win.is_locked_spot = True
            self._apply_window_lock(win, is_strict)
            lbl = tk.Label(win, bg='black', bd=0)
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
            except tk.TclError:
                pass  # Window may be destroyed

        if self.active_floating_texts:
            for t in self.active_floating_texts:
                try:
                    t.lift()
                except tk.TclError:
                    pass  # Window may be destroyed

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
                    last_dims = (nw, nh)
                    last_tk_img = tk_img
                vw['lbl'].configure(image=tk_img)
                vw['lbl'].image = tk_img
            except (tk.TclError, cv2.error) as e:
                logger.debug(f"Video frame error: {e}")
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
        safe_max_y = max(min_offset, h - int(size * 3))
        rx = win_x + random.randint(min_offset, safe_max_x)
        ry = win_y + random.randint(min_offset, safe_max_y)

        def on_hit():
            self.targets_hit += 1
            self.session_targets_clicked += 1
            self.play_gj()
            self._add_xp(5, is_video_context=True)

        try:
            t_win = TransparentTextWindow(self.root, text, rx, ry, w, h, win_x, win_y, size, on_hit)
            self.active_floating_texts.append(t_win)
        except Exception as e:
            logger.debug(f"Could not create attention window: {e}")
            return

        lifespan_sec = self.settings.get('attention_lifespan', 4)

        def expire():
            if t_win in self.active_floating_texts:
                self.active_floating_texts.remove(t_win)
                try:
                    t_win.destroy()
                except tk.TclError:
                    pass  # Already destroyed

        self.root.after(int(lifespan_sec * 1000), expire)

    def _cleanup_video(self):
        self.video_running = False
        self.busy = False
        
        # Notify progression system that video ended
        try:
            self.progression.video_ended()
        except AttributeError:
            pass  # Progression not initialized
        except Exception as e:
            logger.debug(f"Could not notify video end: {e}")
        
        if hasattr(self, 'cap') and self.cap: self.cap.release()
        for vw in self.video_windows:
            try:
                vw['win'].destroy()
            except tk.TclError:
                pass  # Already destroyed
        self.video_windows = []
        for t in self.active_floating_texts:
            try:
                t.destroy()
            except tk.TclError:
                pass  # Already destroyed
        self.active_floating_texts.clear()

        if os.path.exists(TEMP_AUDIO_FILE):
            try:
                os.remove(TEMP_AUDIO_FILE)
            except OSError as e:
                logger.debug(f"Could not remove temp audio: {e}")

        self.ducker.unduck()
        self._duck_subliminal_channel(False)

        loop_needed = False
        is_troll_loop = False
        if self.settings.get('attention_enabled', False):
            passed = (self.targets_total == 0) or (self.targets_hit >= self.targets_total)
            if not passed:
                loop_needed = True
            elif random.random() < 0.10:
                loop_needed = True
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
                self.root.deiconify()
                self.root.lift()
            except tk.TclError as e:
                logger.debug(f"Could not restore window: {e}")

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
            win.overrideredirect(True)
            win.config(bg='black')
            win.geometry(f"{m['width']}x{m['height']}+{m['x']}+{m['y']}")
            win.attributes('-topmost', True)
            win.lift()
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
                    self.root.deiconify()
                    self.root.lift()
                except tk.TclError as e:
                    logger.debug(f"Could not restore window: {e}")
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
                self.root.withdraw()
                self.root.update()
            except tk.TclError as e:
                logger.debug(f"Could not withdraw window: {e}")
        monitors = self._get_monitors_safe()
        penalty_wins = []
        if is_troll:
            msg = "SUCH A GOOD SLUT BAMBI \nYOU DID IT...BUT\n SUCH GOOD GIRLS MUST AGAIN 😈"
            f_size = 85
        else:
            msg = "WHAT A DUMB BAMBI\n DUMB BIMBOS MUST TRY AGAIN"
            f_size = 100
        for m in monitors:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True)
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
        if not self.settings.get('flash_clickable', True): return
        if win in self.active_windows:
            self.active_windows.remove(win)
            self.active_rects = [r for r in self.active_rects if r['win'] != win]
        win.destroy()
        
        # Only spawn more if corruption mode is enabled AND not in cleanup phase
        if self.settings.get('flash_corruption', False) and not getattr(self, '_cleanup_in_progress', False):
            max_hydra = self.settings.get('flash_hydra_limit', 30)
            current_count = len(self.active_windows)
            # Only spawn more if we have room for at least 1 more (spawns 2, but closed 1)
            # Net change is +1, so check if current_count < max_hydra
            if current_count + 1 < max_hydra:
                self.trigger_multiplication(is_startle, event_type, max_hydra, current_count)

    def trigger_multiplication(self, is_startle, event_type, max_hydra=20, current_count=0):
        if not self.running: return
        media_pool = self.get_files(self.paths['images'])
        if not media_pool: return
        
        # Cap max_hydra to 20 to prevent excessive images
        max_hydra = min(max_hydra, 20)
        
        # Calculate how many we can actually spawn (max 2, but respect limit)
        space_available = max_hydra - current_count
        num_to_spawn = min(2, space_available)
        
        if num_to_spawn <= 0:
            return
        
        selected = [random.choice(media_pool) for _ in range(num_to_spawn)]
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
        except Exception as e:
            logger.warning(f"Background loader error: {e}")
            if not is_multiplication: self.root.after(0, lambda: self.busy.__setattr__('busy', False))

    def _load_raw_frames(self, path):
        pil_images = []
        delay = 0.033
        try:
            frames_iter = iio.imiter(path)
            try:
                meta = iio.immeta(path)
                duration = meta.get('duration', 0)
                if duration > 0: delay = duration / 1000.0; delay = max(delay, 0.04)
            except (KeyError, TypeError):
                pass  # No duration metadata
            raw_frames = []
            for i, frame in enumerate(frames_iter):
                if i > 60: break
                raw_frames.append(frame)
            step = 1
            if len(raw_frames) > 60: step = len(raw_frames) // 60; delay *= step
            for i in range(0, len(raw_frames), step): pil_images.append(Image.fromarray(raw_frames[i]))
        except Exception as e:
            logger.debug(f"Could not load animated frames: {e}")
            try:
                pil_images.append(Image.open(path))
            except (IOError, OSError) as e:
                logger.debug(f"Could not load image: {e}")
        return pil_images, delay

    def _finalize_show_images(self, data):
        if not self.running:
            if not data['is_multiplication']: self.busy = False
            return
        duration = 5.0
        
        # Always duck audio when showing flash images
        self._do_duck()
        self._duck_subliminal_channel(True)
        
        if data['sound_path']:
            try:
                if data.get('processed_data') and data['processed_data'][0]['is_startle']:
                    threading.Thread(target=self._delayed_audio_start, args=(data['sound_path'],)).start()
                else:
                    effect = pygame.mixer.Sound(data['sound_path'])
                    vol = self.settings.get('volume', 1.0)
                    curved_vol = max(0.05, vol ** 1.5)  # Gentler curve, minimum 5%
                    effect.set_volume(curved_vol)
                    duration = effect.get_length()
                    effect.play()
                    self._add_xp(2)
            except Exception:
                pass
        
        # Schedule unduck after duration (sound length or default 5s)
        unduck_delay = int(duration * 1000) + 1500
        self.root.after(unduck_delay, self.ducker.unduck)
        self.root.after(unduck_delay - 1000, lambda: self._duck_subliminal_channel(False))
        
        # Force cleanup all flash windows 1 second after audio ends
        # This prevents hydra mode from spawning forever
        cleanup_delay = int(duration * 1000) + 1000
        self.root.after(cleanup_delay, self._force_flash_cleanup)
        
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
    
    def _force_flash_cleanup(self):
        """Force cleanup all flash windows after audio ends"""
        if not self.running:
            return
        # Set virtual_end_time to now to trigger fade out
        self.virtual_end_time = time.time()
        # Disable hydra spawning temporarily by marking cleanup in progress
        self._cleanup_in_progress = True
        
        # Schedule re-enabling after windows fade out
        def re_enable():
            self._cleanup_in_progress = False
        self.root.after(2000, re_enable)

    def _delayed_audio_start(self, sound_path):
        time.sleep(2.0)
        if self.running:
            try:
                effect = pygame.mixer.Sound(sound_path)
                vol = self.settings.get('volume', 1.0)
                curved_vol = max(0.05, vol ** 1.5)  # Gentler curve, minimum 5%
                effect.set_volume(curved_vol)
                effect.play()
                duration = effect.get_length()
                self.root.after(int(duration * 1000) + 1500, self.ducker.unduck)
            except pygame.error as e:
                logger.debug(f"Could not play delayed audio: {e}")
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
        if self.settings.get('flash_clickable', True):
            win.config(cursor="hand2")
        else:
            win.config(cursor="X_cursor")
        self._add_xp(1)
        lbl = tk.Label(win, bg='black', bd=0)
        lbl.pack(expand=True, fill='both')
        lbl.bind('<Button-1>', lambda e: self.on_image_click(win, False, None))
        win.frames = tk_frames
        win.frame_delay = delay
        win.start_time = time.time()
        self.active_windows.append(win)
        self.active_rects.append({'win': win, 'x': x, 'y': y, 'w': w, 'h': h})

    def _add_xp(self, base_points, is_video_context=False):
        multiplier = 1.0
        if self.settings.get('disable_panic_esc', False): multiplier *= 1.5
        if is_video_context and self.settings.get('startle_strict', False): multiplier *= 1.5

        points_to_add = float(base_points) * multiplier
        self.settings['player_xp'] += points_to_add
        self._check_level_up()
        self._update_ui_xp()

    def _check_level_up(self):
        current_xp = self.settings.get('player_xp', 0.0)
        current_level = self.settings.get('player_level', 1)
        # New formula: 50 + (level * 20) - much faster progression
        xp_needed = 50.0 + (current_level * 20.0)

        leveled_up = False
        while current_xp >= xp_needed:
            current_xp -= xp_needed
            current_level += 1
            xp_needed = 50.0 + (current_level * 20.0)
            leveled_up = True

        self.settings['player_xp'] = current_xp
        self.settings['player_level'] = current_level

        if leveled_up:
            self.progression.check_unlocks(current_level)
            self._play_levelup_sound()
    
    def _play_levelup_sound(self):
        """Play level up celebration sound"""
        try:
            lvlup_path = os.path.join(self.paths['sounds'], "lvup.mp3")
            if os.path.exists(lvlup_path):
                vol = self.settings.get('volume', 0.5)
                sound = pygame.mixer.Sound(lvlup_path)
                sound.set_volume(min(1.0, vol * 1.5))  # Slightly louder for celebration
                sound.play()
        except Exception as e:
            print(f"[DEBUG] Level up sound error: {e}")

    def _update_ui_xp(self):
        if self.xp_update_callback:
            lvl = self.settings.get('player_level', 1)
            xp = self.settings.get('player_xp', 0.0)
            # New formula: 50 + (level * 20)
            req = 50.0 + (lvl * 20.0)
            progress = xp / req
            self.xp_update_callback(lvl, progress, xp, req)

    def heartbeat(self):
        now = time.time()
        dt = now - self.last_heartbeat_time
        self.last_heartbeat_time = now

        # --- Base XP Accumulation: 5 XP/min when running ---
        if self.running:
            self.bg_audio_accumulator += dt
            # 5 XP per minute = 1 XP every 12 seconds
            if self.bg_audio_accumulator >= 12.0:
                self.bg_audio_accumulator -= 12.0
                self._add_xp(1)

        # --- Spiral XP Bonus: 5 XP/min if opacity > 3% ---
        if self.running and self.settings.get("spiral_enabled"):
            op = self.settings.get("spiral_opacity", 0.1)
            if self.settings.get("spiral_link_ramp"):
                op += (self.current_intensity_progress * 0.4)
            if op >= 0.03:
                self._add_xp(0.083 * dt)  # 5/60 = 0.083 XP per second

        # --- Pink Filter XP Bonus: 5 XP/min if opacity > 5% ---
        if self.running and self.settings.get("pink_filter_enabled"):
            pf_op = self.settings.get("pink_filter_opacity", 0.1)
            if self.settings.get("pink_filter_link_ramp"):
                pf_op += (self.current_intensity_progress * 0.4)
            if pf_op >= 0.05:
                self._add_xp(0.083 * dt)  # 5/60 = 0.083 XP per second

        # --- Progression Visuals (Spiral, Pink Filter & Bubbles) ---
        if self.running:
            try:
                # Calculate pink opacity
                pink_op = 0.0
                if self.settings.get("pink_filter_enabled"):
                    pink_op = self.settings.get("pink_filter_opacity", 0.1)
                    if self.settings.get("pink_filter_link_ramp"):
                        pink_op += (self.current_intensity_progress * 0.4)
                        pink_op = min(0.5, pink_op)  # Cap at 50%

                # Update all progression visuals
                self.progression.update_visuals(pink_opacity=pink_op)
            except Exception as e:
                logger.debug(f"Could not update progression visuals: {e}")
        else:
            try:
                self.progression.shutdown()
            except AttributeError:
                pass  # Progression not initialized

        try:
            self._update_scheduler_progress()
        except Exception as e:
            logger.debug(f"Could not update scheduler: {e}")

        if self.video_running:
            self.root.after(100, self.heartbeat)
            return

        # --- Standard Image Flashing Logic ---
        max_alpha = self.get_effective_value('image_alpha', self.settings.get('image_alpha', 1.0))
        max_alpha = min(1.0, max(0.0, max_alpha))
        show_images = time.time() < self.virtual_end_time
        target_alpha_val = max_alpha if show_images else 0.0

        # Sync flash count with resource manager
        try:
            from progression_system import resource_mgr
            current_flash_count = len([w for w in self.active_windows if not getattr(w, 'is_locked_spot', False)])
            resource_mgr.active_effects['flashes'] = current_flash_count
        except ImportError:
            pass  # Module not available
        except (KeyError, AttributeError) as e:
            logger.debug(f"Could not sync flash count: {e}")

        if not show_images and not self.active_windows:
            self.active_rects.clear()
            if self.events_pending_reschedule:
                for ev in list(self.events_pending_reschedule):
                    self.schedule_next(ev)
                self.events_pending_reschedule.clear()

        for win in self.active_windows[:]:
            if not win.winfo_exists():
                self.active_windows.remove(win)
                continue
            if hasattr(win, 'is_locked_spot'):
                continue
            try:
                cur = win.attributes('-alpha')
                if target_alpha_val > cur:
                    win.attributes('-alpha', min(target_alpha_val, cur + 0.08))
                elif target_alpha_val < cur:
                    new_a = max(0.0, cur - 0.08)
                    win.attributes('-alpha', new_a)
                    if new_a == 0.0:
                        win.destroy()
                        self.active_windows.remove(win)
                        self.active_rects = [r for r in self.active_rects if r['win'] != win]
            except tk.TclError:
                pass  # Window may be destroyed
            if hasattr(win, 'frames') and len(win.frames) > 1:
                now = time.time()
                idx = int((now - win.start_time) / win.frame_delay) % len(win.frames)
                try:
                    win.winfo_children()[0].configure(image=win.frames[idx])
                except (tk.TclError, IndexError):
                    pass  # Window or frame may be gone
        self.root.after(33, self.heartbeat)