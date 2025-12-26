"""
Optimized Progression System with Resource Management
- Global resource limiter prevents CPU overload
- Pre-loaded bubble assets
- Pauses during video playback
- Rate-limited everything
"""

import tkinter as tk
import os
import time
import random
import ctypes
from ctypes import windll
from PIL import Image, ImageSequence, ImageTk

# Initialize logging
try:
    from security import logger
except ImportError:
    import logging
    logger = logging.getLogger("ConditioningPanel")

# --- WIN32 API CONSTANTS ---
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TOPMOST = 0x00008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040


class ResourceManager:
    """
    Global resource manager to prevent CPU overload.
    Tracks active effects and prevents too many simultaneous operations.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self.active_effects = {
            'spiral': False,
            'bubbles': 0,
            'flashes': 0,
            'video': False,
            'pink_filter': False
        }
        self.max_bubbles = 4  # Reasonable limit
        self.max_flashes = 15
        self.last_effect_time = {}
        self.min_effect_interval = 0.5  # Back to 0.5s
        self.video_pending = False
        self.video_pending_time = 0
        self.flash_waiting = False  # Flash is waiting for bubbles to clear
    
    def can_start_effect(self, effect_type):
        """Check if we can start a new effect"""
        if self.active_effects['video'] or self.video_pending:
            return False
        
        now = time.time()
        last = self.last_effect_time.get(effect_type, 0)
        
        if now - last < self.min_effect_interval:
            return False
        
        if effect_type == 'bubble':
            if self.active_effects['bubbles'] >= self.max_bubbles:
                return False
            # Don't spawn bubbles if flash is waiting or flashes are active
            if self.flash_waiting or self.active_effects['flashes'] > 0:
                return False
        elif effect_type == 'flash':
            if self.active_effects['flashes'] >= self.max_flashes:
                return False
            # Don't spawn flashes if bubbles are active
            if self.active_effects['bubbles'] > 0:
                return False
        
        self.last_effect_time[effect_type] = now
        return True
    
    def has_active_bubbles(self):
        """Check if there are bubbles currently active"""
        return self.active_effects['bubbles'] > 0
    
    def has_active_flashes(self):
        """Check if there are flashes currently active"""
        return self.active_effects['flashes'] > 0
    
    def request_flash(self):
        """Request to do a flash - returns True if can proceed, False if must wait"""
        if self.active_effects['video'] or self.video_pending:
            return False
        if self.has_active_bubbles():
            self.flash_waiting = True
            return False
        self.flash_waiting = False
        return True
    
    def flash_done_waiting(self):
        """Called when flash can finally proceed"""
        self.flash_waiting = False
    
    def register_effect(self, effect_type, active=True):
        """Register an effect starting or ending"""
        if effect_type == 'bubble':
            if active:
                self.active_effects['bubbles'] += 1
            else:
                self.active_effects['bubbles'] = max(0, self.active_effects['bubbles'] - 1)
        elif effect_type == 'flash':
            if active:
                self.active_effects['flashes'] += 1
            else:
                self.active_effects['flashes'] = max(0, self.active_effects['flashes'] - 1)
        elif effect_type in self.active_effects:
            self.active_effects[effect_type] = active
    
    def prepare_for_video(self):
        """Signal that video is about to start - pause everything"""
        self.video_pending = True
        self.video_pending_time = time.time()
    
    def start_video(self):
        """Video has started"""
        self.video_pending = False
        self.active_effects['video'] = True
    
    def end_video(self):
        """Video has ended"""
        self.active_effects['video'] = False
        self.video_pending = False
    
    def is_video_active(self):
        return self.active_effects['video'] or self.video_pending
    
    def get_load_factor(self):
        """Get current system load factor (0.0 to 1.0)"""
        load = 0.0
        if self.active_effects['spiral']:
            load += 0.4
        load += self.active_effects['bubbles'] * 0.1
        load += self.active_effects['flashes'] * 0.05
        if self.active_effects['pink_filter']:
            load += 0.1
        return min(1.0, load)


# Global resource manager
resource_mgr = ResourceManager()


class SpiralOverlay:
    """
    Lightweight GIF overlay using tkinter's native alpha.
    Optimized for minimal CPU usage.
    """
    
    # Class-level frame cache
    _frame_cache = {}

    def __init__(self, root, gif_path, initial_alpha=0.3, dual_monitor=False):
        self.root = root
        self.gif_path = gif_path
        self.alpha = initial_alpha
        self.dual_monitor = dual_monitor
        self.destroyed = False
        self.windows = []
        self.labels = []
        self.frame_delays = []
        self.current_frame = 0
        self.monitors = []
        self.animating = False
        self._last_frame_time = 0
        self._min_frame_interval = 80  # ~12 FPS max for performance
        self._photo_frames = []
        self._raw_frames = []
        self._paused = False

        # Register with resource manager
        resource_mgr.register_effect('spiral', True)

        # Get monitor information
        self.monitors = self._get_monitors()

        # Load and prepare frames
        if self._load_gif():
            self._create_windows()
            if self.windows:
                self.animating = True
                self._animate()

    def _get_monitors(self):
        """Get list of monitors to display on"""
        monitors = []
        try:
            from screeninfo import get_monitors
            all_monitors = list(get_monitors())
            if self.dual_monitor:
                for m in all_monitors:
                    monitors.append({'x': m.x, 'y': m.y, 'width': m.width, 'height': m.height})
            else:
                primary = None
                for m in all_monitors:
                    if m.x == 0 and m.y == 0:
                        primary = m
                        break
                if primary is None and all_monitors:
                    primary = all_monitors[0]
                if primary:
                    monitors.append({'x': primary.x, 'y': primary.y, 'width': primary.width, 'height': primary.height})
        except Exception as e:
            logger.debug(f"Could not get monitors: {e}")
            monitors.append({
                'x': 0, 'y': 0,
                'width': self.root.winfo_screenwidth(),
                'height': self.root.winfo_screenheight()
            })
        return monitors

    def _load_gif(self):
        """Load GIF at reduced resolution for performance"""
        if not self.gif_path or not os.path.exists(self.gif_path):
            return False
        
        try:
            cache_key = self.gif_path
            if cache_key in SpiralOverlay._frame_cache:
                cached = SpiralOverlay._frame_cache[cache_key]
                self.frame_delays = cached['delays'].copy()
                self._raw_frames = cached['frames']
                return True

            img = Image.open(self.gif_path)
            
            # Cap resolution at 1280x720 for better performance
            max_w = min(1280, max(m['width'] for m in self.monitors))
            max_h = min(720, max(m['height'] for m in self.monitors))
            
            raw_frames = []
            frame_count = 0
            for frame in ImageSequence.Iterator(img):
                if frame_count >= 24:  # Limit to 24 frames
                    break
                    
                frame_rgba = frame.convert('RGBA')
                img_w, img_h = frame_rgba.size
                scale = min(max_w / img_w, max_h / img_h)
                
                if scale < 1.0:
                    new_w = int(img_w * scale)
                    new_h = int(img_h * scale)
                    frame_rgba = frame_rgba.resize((new_w, new_h), Image.Resampling.NEAREST)
                
                raw_frames.append(frame_rgba)
                delay = max(frame.info.get('duration', 100), self._min_frame_interval)
                self.frame_delays.append(delay)
                frame_count += 1
            
            if not raw_frames:
                return False
            
            self._raw_frames = raw_frames
            SpiralOverlay._frame_cache[cache_key] = {
                'frames': raw_frames,
                'delays': self.frame_delays.copy()
            }
            
            return True
            
        except Exception as e:
            print(f"[DEBUG] Error loading spiral GIF: {e}")
            return False

    def _create_windows(self):
        """Create overlay windows"""
        if not self._raw_frames:
            return
        
        for mon in self.monitors:
            if self.destroyed:
                return
            try:
                win = tk.Toplevel(self.root)
                win.overrideredirect(True)
                win.attributes('-topmost', True)
                win.attributes('-alpha', self.alpha)
                win.configure(bg='black')
                win.geometry(f"{mon['width']}x{mon['height']}+{mon['x']}+{mon['y']}")
                
                label = tk.Label(win, bg='black', bd=0, highlightthickness=0)
                label.pack(fill='both', expand=True)
                
                win.update_idletasks()
                self._make_click_through(win)
                
                self.windows.append(win)
                self.labels.append(label)
                win.mon_w = mon['width']
                win.mon_h = mon['height']
                
            except Exception as e:
                print(f"[DEBUG] Error creating spiral window: {e}")

        # Pre-convert frames to PhotoImages
        self._photo_frames = []
        
        for i, raw in enumerate(self._raw_frames):
            try:
                if self.windows:
                    win = self.windows[0]
                    img_w, img_h = raw.size
                    scale = max(win.mon_w / img_w, win.mon_h / img_h)
                    
                    if abs(scale - 1.0) > 0.01:
                        new_w = int(img_w * scale)
                        new_h = int(img_h * scale)
                        scaled = raw.resize((new_w, new_h), Image.Resampling.NEAREST)
                    else:
                        scaled = raw
                    
                    photo = ImageTk.PhotoImage(scaled)
                    self._photo_frames.append(photo)
            except Exception as e:
                break

    def _make_click_through(self, window):
        """Make window click-through"""
        try:
            hwnd = windll.user32.GetParent(window.winfo_id())
            if hwnd == 0:
                hwnd = window.winfo_id()
            
            ex_style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style = ex_style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
            windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            
            windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                       SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
        except (OSError, AttributeError) as e:
            logger.debug(f"Could not make window click-through: {e}")

    def _animate(self):
        """Animate frames with rate limiting"""
        if self.destroyed or not self.animating or not self.windows:
            return
        
        # Pause during video
        if resource_mgr.is_video_active():
            self.root.after(200, self._animate)
            return
        
        try:
            now = time.time() * 1000
            
            if now - self._last_frame_time < self._min_frame_interval:
                self.root.after(20, self._animate)
                return
            
            self._last_frame_time = now
            
            if self._photo_frames:
                frame_idx = self.current_frame % len(self._photo_frames)
                photo = self._photo_frames[frame_idx]
                
                for label in self.labels:
                    try:
                        label.configure(image=photo)
                        label.image = photo
                    except tk.TclError:
                        pass  # Label may be destroyed
                
                self.current_frame += 1
            
            delay = 100
            if self.frame_delays:
                delay = max(self._min_frame_interval, self.frame_delays[self.current_frame % len(self.frame_delays)])
            
            self.root.after(delay, self._animate)
            
        except tk.TclError as e:
            logger.debug(f"Animation error: {e}")

    def set_alpha(self, alpha_val):
        """Update overlay transparency (0-255 -> 0.0-1.0)"""
        self.alpha = max(0.0, min(1.0, alpha_val / 255.0))
        for win in self.windows:
            try:
                win.attributes('-alpha', self.alpha)
            except tk.TclError:
                pass  # Window may be destroyed

    def pause(self):
        """Pause animation"""
        self._paused = True

    def resume(self):
        """Resume animation"""
        self._paused = False

    def destroy(self):
        """Clean up"""
        if self.destroyed:
            return
        self.destroyed = True
        self.animating = False
        resource_mgr.register_effect('spiral', False)
        
        for win in self.windows:
            try:
                win.destroy()
            except tk.TclError:
                pass  # Already destroyed
        self.windows.clear()
        self.labels.clear()
        self._photo_frames = []


class PinkFilterOverlay:
    """Simple pink filter overlay - very lightweight."""

    def __init__(self, root):
        self.root = root
        self.windows = []
        self.active = False
        self.current_alpha = 0.0

    def set_overlay(self, alpha):
        """Set pink filter opacity (0.0 to 0.5)"""
        # Don't show during video
        if resource_mgr.is_video_active():
            self._destroy_windows()
            return
            
        safe_alpha = min(0.5, max(0.0, alpha))
        
        if safe_alpha <= 0.01:
            self._destroy_windows()
            return
            
        if self.active and abs(self.current_alpha - safe_alpha) < 0.02:
            return
            
        self.current_alpha = safe_alpha
        
        if not self.active:
            self._create_windows()
            
        for win in self.windows:
            try:
                win.attributes('-alpha', self.current_alpha)
            except tk.TclError:
                pass  # Window may be destroyed

    def _create_windows(self):
        """Create overlay windows"""
        self.active = True
        resource_mgr.register_effect('pink_filter', True)
        monitors = self._get_monitors()
        
        for m in monitors:
            try:
                win = tk.Toplevel(self.root)
                win.overrideredirect(True)
                win.geometry(f"{m['width']}x{m['height']}+{m['x']}+{m['y']}")
                win.configure(bg="#FF69B4")
                win.attributes('-alpha', self.current_alpha)
                win.attributes('-topmost', True)
                
                win.update_idletasks()
                self._make_click_through(win)
                self.windows.append(win)
            except tk.TclError as e:
                logger.debug(f"Could not create pink filter window: {e}")

    def _destroy_windows(self):
        """Destroy all windows"""
        for win in self.windows:
            try:
                win.destroy()
            except tk.TclError:
                pass  # Already destroyed
        self.windows.clear()
        self.active = False
        self.current_alpha = 0.0
        resource_mgr.register_effect('pink_filter', False)

    def _make_click_through(self, window):
        """Make click-through"""
        try:
            hwnd = windll.user32.GetParent(window.winfo_id())
            if hwnd == 0:
                hwnd = window.winfo_id()
            
            ex_style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style = ex_style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_NOACTIVATE
            windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            
            windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                       SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
        except (OSError, AttributeError) as e:
            logger.debug(f"Could not make click-through: {e}")

    def _get_monitors(self):
        """Get monitors"""
        try:
            from screeninfo import get_monitors
            return [{'x': m.x, 'y': m.y, 'width': m.width, 'height': m.height} for m in get_monitors()]
        except ImportError:
            return [{'x': 0, 'y': 0, 'width': self.root.winfo_screenwidth(), 'height': self.root.winfo_screenheight()}]
        except Exception as e:
            logger.debug(f"Could not get monitors: {e}")
            return [{'x': 0, 'y': 0, 'width': self.root.winfo_screenwidth(), 'height': self.root.winfo_screenheight()}]


class BubbleManager:
    """Manages bubble spawning with strict rate limiting and pre-loading."""
    
    def __init__(self, engine_ref):
        self.engine = engine_ref
        self.last_spawn_time = 0
        self._bubble_image = None
        self._image_loaded = False
        
        # Pre-load bubble image
        self._preload_image()

    def _preload_image(self):
        """Pre-load bubble image to prevent white flash"""
        try:
            path = os.path.join("assets", "images", "bubble.png")
            if not os.path.exists(path):
                path = "bubble.png"
            if os.path.exists(path):
                self._bubble_image = Image.open(path).convert('RGBA')
                self._image_loaded = True
        except (IOError, OSError) as e:
            logger.debug(f"Could not preload bubble image: {e}")

    def update(self):
        if not self.engine.settings.get("bubbles_enabled", False):
            return
        
        # Don't spawn during video
        if resource_mgr.is_video_active():
            return
        
        # Check bubble count limit
        current_bubbles = resource_mgr.active_effects.get('bubbles', 0)
        if current_bubbles >= resource_mgr.max_bubbles:
            return
        
        # Don't spawn if flashes are on screen
        current_flashes = resource_mgr.active_effects.get('flashes', 0)
        if current_flashes > 0:
            return
        
        # Don't spawn if flash is waiting
        if resource_mgr.flash_waiting:
            return
            
        freq = self.engine.settings.get("bubbles_freq", 5)
        if self.engine.settings.get("bubbles_link_ramp", False):
            freq += (self.engine.current_intensity_progress * 10)
        
        # Reduce frequency when spiral is active
        if resource_mgr.active_effects.get('spiral', False):
            freq = min(freq, 4)
        
        freq = min(freq, 12)
        spawn_interval = 60.0 / max(1, freq)
        
        time_since_last = time.time() - self.last_spawn_time
        if time_since_last > spawn_interval:
            self._spawn()
            self.last_spawn_time = time.time()

    def _spawn(self):
        try:
            from bubble_game import Bubble
            path = os.path.join("assets", "images", "bubble.png")
            if not os.path.exists(path):
                path = "bubble.png"
            
            if not os.path.exists(path):
                return
            
            # Get monitors from engine (supports multi-monitor)
            monitors = self.engine._get_monitors_safe() if hasattr(self.engine, '_get_monitors_safe') else None
            
            if monitors and len(monitors) > 0:
                # Choose random monitor
                mon = random.choice(monitors)
            else:
                # Fallback to primary screen
                mon = {
                    'x': 0, 
                    'y': 0, 
                    'width': self.engine.root.winfo_screenwidth(),
                    'height': self.engine.root.winfo_screenheight()
                }
            
            volume = self.engine.settings.get('volume', 0.5)
            
            def on_pop():
                self.engine._add_xp(10)
            
            Bubble(
                self.engine.root, 
                mon, 
                speed=random.uniform(2, 4),
                on_pop=on_pop,
                on_miss=None,
                asset_path=path,
                volume=volume,
                preloaded_image=self._bubble_image  # Pass pre-loaded image
            )
        except Exception as e:
            print(f"[DEBUG] Bubble spawn error: {e}")
            import traceback
            traceback.print_exc()


class ProgressionSystem:
    """Main progression system with resource management."""
    
    def __init__(self, engine_ref):
        self.engine = engine_ref
        self.pink_filter = PinkFilterOverlay(engine_ref.root)
        self.spiral = None
        self.bubbles = BubbleManager(engine_ref)
        self.unlocks = {"pink_filter": False, "spiral": False, "bubbles": False}
        self.current_spiral_path = None
        self.current_spiral_dual = None
        self._is_shutdown = False
        self._last_visual_update = 0
        self._visual_update_interval = 0.1  # 100ms between updates (was 150ms)

    def check_unlocks(self, level):
        """Check what features are unlocked at current level"""
        self.unlocks["pink_filter"] = (level >= 10)
        self.unlocks["spiral"] = (level >= 10)
        self.unlocks["bubbles"] = (level >= 20)

    def prepare_for_video(self):
        """Called before video starts - stop/hide ALL effects to free resources"""
        resource_mgr.prepare_for_video()
        
        # Pop all bubbles immediately (plays sounds, frees resources)
        try:
            from bubble_game import Bubble
            Bubble.pop_all()
        except ImportError:
            pass  # Module not available
        except Exception as e:
            logger.debug(f"Could not pop bubbles: {e}")
        
        # Hide pink filter
        self.pink_filter._destroy_windows()
        
        # STOP spiral completely (not just pause - frees significant CPU)
        if self.spiral and not self.spiral.destroyed:
            self.spiral.pause()
            # Hide and minimize spiral windows during video
            for win in self.spiral.windows:
                try:
                    win.withdraw()
                except tk.TclError:
                    pass  # Window may be destroyed
            # Stop the animation loop
            self.spiral.running = False

    def video_started(self):
        """Called when video actually starts"""
        resource_mgr.start_video()

    def video_ended(self):
        """Called when video ends - resume effects"""
        resource_mgr.end_video()
        
        # Resume spiral only if enabled
        if self.spiral and not self.spiral.destroyed:
            if self.engine.settings.get('spiral_enabled', False):
                self.spiral.running = True
                self.spiral.resume()
                for win in self.spiral.windows:
                    try:
                        win.deiconify()
                    except tk.TclError:
                        pass  # Window may be destroyed

    def update_visuals(self, pink_opacity=0.0):
        """Update visual effects with rate limiting"""
        self._is_shutdown = False
        
        # Don't update during video
        if resource_mgr.is_video_active():
            return
        
        now = time.time()
        
        if now - self._last_visual_update < self._visual_update_interval:
            return
        self._last_visual_update = now
        
        # 1. Pink Filter
        if self.unlocks["pink_filter"] and self.engine.settings.get("pink_filter_enabled"):
            self.pink_filter.set_overlay(pink_opacity)
        else:
            self.pink_filter.set_overlay(0.0)

        # 2. Spiral Overlay
        self._update_spiral()

        # 3. Bubbles
        if self.unlocks["bubbles"]:
            self.bubbles.update()

    def _update_spiral(self):
        """Handle spiral overlay"""
        spiral_enabled = self.unlocks["spiral"] and self.engine.settings.get("spiral_enabled")
        path = self.engine.settings.get("spiral_path", "")
        dual_monitor = self.engine.settings.get("dual_monitor", False)
        
        if spiral_enabled and path:
            base_op = self.engine.settings.get("spiral_opacity", 0.1)
            if self.engine.settings.get("spiral_link_ramp"):
                base_op += (self.engine.current_intensity_progress * 0.4)
                base_op = min(1.0, base_op)
            alpha_255 = int(base_op * 255)

            need_new = (
                self.spiral is None or 
                self.spiral.destroyed or
                self.current_spiral_path != path or
                self.current_spiral_dual != dual_monitor
            )
            
            if need_new:
                if self.spiral:
                    self.spiral.destroy()
                    self.spiral = None
                
                self.spiral = SpiralOverlay(self.engine.root, path, base_op, dual_monitor)
                self.current_spiral_path = path
                self.current_spiral_dual = dual_monitor

            elif self.spiral and not self.spiral.destroyed:
                self.spiral.set_alpha(alpha_255)
                
        else:
            if self.spiral:
                self.spiral.destroy()
                self.spiral = None
                self.current_spiral_path = None
                self.current_spiral_dual = None

    def shutdown(self):
        """Clean up"""
        if self._is_shutdown:
            return
        self._is_shutdown = True
        
        self.pink_filter._destroy_windows()
        if self.spiral:
            self.spiral.destroy()
            self.spiral = None
            self.current_spiral_path = None
            self.current_spiral_dual = None
