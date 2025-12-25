"""
Optimized Bubble Game
- Pre-loaded images to prevent white flash
- Reduced MAX_BUBBLES
- Better cleanup
- Registers with ResourceManager for flash coordination
"""

import os
import math
import time
import random
import threading
import tkinter as tk
from ctypes import windll, byref, c_int

try:
    import pygame
    pygame.mixer.init()
    AUDIO_AVAILABLE = True
except:
    AUDIO_AVAILABLE = False

from PIL import Image, ImageDraw

# Import resource manager for coordination
try:
    from progression_system import resource_mgr
    RESOURCE_MGR_AVAILABLE = True
except:
    RESOURCE_MGR_AVAILABLE = False

# Win32 constants
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
LWA_COLORKEY = 0x1
LWA_ALPHA = 0x2
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

ULW_ALPHA = 0x02
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01

from ctypes import Structure, sizeof, c_byte, wintypes

class BLENDFUNCTION(Structure):
    _fields_ = [("BlendOp", c_byte), ("BlendFlags", c_byte),
                ("SourceConstantAlpha", c_byte), ("AlphaFormat", c_byte)]

class Point(Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

class Size(Structure):
    _fields_ = [("cx", wintypes.LONG), ("cy", wintypes.LONG)]

class BITMAPINFOHEADER(Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]

import ctypes

def make_transparent_window(hwnd, pil_image, x, y, alpha_val=255):
    """Paint a PIL image onto a HWND using UpdateLayeredWindow."""
    try:
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')

        if alpha_val < 255:
            alpha_layer = pil_image.split()[3]
            alpha_layer = alpha_layer.point(lambda p: int(p * alpha_val / 255))
            r, g, b, _ = pil_image.split()
            pil_image = Image.merge('RGBA', (r, g, b, alpha_layer))

        try:
            pil_image = pil_image.convert('RGBa')
        except:
            pil_image = pil_image.convert('RGBA').convert('RGBa')

        w, h = pil_image.size
        r, g, b, a = pil_image.split()
        bgra_img = Image.merge("RGBA", (b, g, r, a))
        img_data = bgra_img.tobytes()

        hdcScreen = windll.user32.GetDC(0)
        hdcMem = windll.gdi32.CreateCompatibleDC(hdcScreen)

        bmi = BITMAPINFOHEADER()
        bmi.biSize = sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        pvBits = ctypes.c_void_p()
        hBitmap = windll.gdi32.CreateDIBSection(hdcMem, byref(bmi), 0, byref(pvBits), 0, 0)
        if hBitmap == 0:
            windll.gdi32.DeleteDC(hdcMem)
            windll.user32.ReleaseDC(0, hdcScreen)
            return

        ctypes.memmove(pvBits, img_data, len(img_data))
        oldBitmap = windll.gdi32.SelectObject(hdcMem, hBitmap)

        blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
        windll.user32.UpdateLayeredWindow(hwnd, hdcScreen, byref(Point(x, y)), byref(Size(w, h)),
                                          hdcMem, byref(Point(0, 0)), 0, byref(blend), ULW_ALPHA)

        windll.gdi32.SelectObject(hdcMem, oldBitmap)
        windll.gdi32.DeleteObject(hBitmap)
        windll.gdi32.DeleteDC(hdcMem)
        windll.user32.ReleaseDC(0, hdcScreen)
    except:
        pass


class Bubble:
    count = 0
    MAX_BUBBLES = 8  # Reduced for performance
    instances = []  # Track all active bubble instances

    def __init__(self, root, monitor, speed, on_pop, on_miss, asset_path, volume=0.5, preloaded_image=None):
        if Bubble.count >= Bubble.MAX_BUBBLES:
            self.alive = False
            if on_miss:
                try:
                    on_miss()
                except:
                    pass
            return

        Bubble.count += 1
        Bubble.instances.append(self)  # Track this instance
        
        # Register with resource manager
        if RESOURCE_MGR_AVAILABLE:
            try:
                resource_mgr.register_effect('bubble', True)
            except:
                pass
        
        self.root = root
        self.on_pop = on_pop
        self.on_miss = on_miss
        self.base_speed = speed
        self.alive = True
        self.is_popping = False
        self.fade_alpha = 255.0
        self.volume = volume
        self.hwnd = None
        self.win = None
        self.hitbox_win = None  # Separate clickable window

        self.anim_type = random.choice([0, 1, 2, 3])
        self.angle = random.randint(0, 360)
        self.time_alive = 0.0
        self.wobble_offset = random.uniform(0, 100)
        self.scale_base = 1.0

        self.start_x = monitor['x'] + random.randint(50, max(100, monitor['width'] - 350))
        self.pos_x = self.start_x
        self.pos_y = monitor['y'] + monitor['height']

        self.target_size = random.randint(200, 280)  # Slightly smaller for performance
        self.original_pil = None

        # Use pre-loaded image if available
        if preloaded_image is not None:
            try:
                self.original_pil = preloaded_image.copy()
                w, h = self.original_pil.size
                aspect = w / h if h > 0 else 1
                if w > self.target_size or h > self.target_size:
                    new_w = self.target_size
                    new_h = int(new_w / aspect)
                    self.original_pil = self.original_pil.resize((new_w, new_h), Image.Resampling.BILINEAR)
            except:
                self.original_pil = None

        # Fallback to loading from file
        if self.original_pil is None and os.path.exists(asset_path):
            try:
                self.original_pil = Image.open(asset_path).convert("RGBA")
                w, h = self.original_pil.size
                aspect = w / h if h > 0 else 1
                if w > self.target_size or h > self.target_size:
                    new_w = self.target_size
                    new_h = int(new_w / aspect)
                    self.original_pil = self.original_pil.resize((new_w, new_h), Image.Resampling.BILINEAR)
            except:
                self.original_pil = None

        # Create fallback bubble if no image
        if self.original_pil is None:
            self.original_pil = Image.new('RGBA', (self.target_size, self.target_size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(self.original_pil)
            draw.ellipse([5, 5, self.target_size - 5, self.target_size - 5], 
                        fill=(200, 200, 255, 128), outline="white", width=2)

        self.base_w, self.base_h = self.original_pil.size
        self.canvas_size = int(math.sqrt(self.base_w ** 2 + self.base_h ** 2)) + 20
        
        # Calculate hitbox size (circular area)
        self.hitbox_size = min(self.base_w, self.base_h)

        # Pre-render the first frame BEFORE creating window
        self._first_frame = self._render_frame()

        # Create window hidden, render first frame, then show
        self._create_window()

    def _render_frame(self):
        """Pre-render a frame"""
        try:
            scale = self.scale_base + 0.05 * math.sin(self.wobble_offset)
            new_w = int(self.base_w * scale)
            new_h = int(self.base_h * scale)
            
            if new_w < 10 or new_h < 10:
                return None
                
            resized = self.original_pil.resize((new_w, new_h), Image.Resampling.NEAREST)
            canvas = Image.new('RGBA', (self.canvas_size, self.canvas_size), (0, 0, 0, 0))
            offset_x = (self.canvas_size - new_w) // 2
            offset_y = (self.canvas_size - new_h) // 2
            canvas.paste(resized, (offset_x, offset_y), resized)
            return canvas
        except:
            return None

    def _create_window(self):
        """Create visual window and separate clickable hitbox window"""
        try:
            # --- VISUAL WINDOW (transparent, click-through) ---
            self.win = tk.Toplevel(self.root)
            self.win.overrideredirect(True)
            self.win.withdraw()  # Start hidden
            self.win.geometry(f"{self.canvas_size}x{self.canvas_size}+{int(self.pos_x)}+{int(self.pos_y)}")
            self.win.update_idletasks()

            self.hwnd = windll.user32.GetParent(self.win.winfo_id())
            if self.hwnd == 0:
                self.hwnd = self.win.winfo_id()

            # Visual window is layered and click-through
            ex_style = windll.user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
            ex_style = ex_style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
            windll.user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, ex_style)

            # Render first frame to window BEFORE showing
            if self._first_frame:
                make_transparent_window(self.hwnd, self._first_frame, 
                                       int(self.pos_x), int(self.pos_y), int(self.fade_alpha))

            # --- HITBOX WINDOW (invisible but clickable) ---
            hitbox_offset = (self.canvas_size - self.hitbox_size) // 2
            hitbox_x = int(self.pos_x) + hitbox_offset
            hitbox_y = int(self.pos_y) + hitbox_offset
            
            self.hitbox_win = tk.Toplevel(self.root)
            self.hitbox_win.overrideredirect(True)
            self.hitbox_win.geometry(f"{self.hitbox_size}x{self.hitbox_size}+{hitbox_x}+{hitbox_y}")
            self.hitbox_win.configure(bg='black')
            self.hitbox_win.attributes('-alpha', 0.01)  # Almost invisible but catches clicks
            self.hitbox_win.attributes('-topmost', True)
            self.hitbox_win.update_idletasks()
            
            # Hitbox catches clicks
            self.hitbox_win.bind("<Button-1>", self.pop)
            
            # Make hitbox topmost but NOT click-through
            hitbox_hwnd = windll.user32.GetParent(self.hitbox_win.winfo_id())
            if hitbox_hwnd == 0:
                hitbox_hwnd = self.hitbox_win.winfo_id()
            
            hb_style = windll.user32.GetWindowLongW(hitbox_hwnd, GWL_EXSTYLE)
            hb_style = hb_style | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
            windll.user32.SetWindowLongW(hitbox_hwnd, GWL_EXSTYLE, hb_style)
            
            windll.user32.SetWindowPos(hitbox_hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                       SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)

            # Now show visual window (already has rendered content via UpdateLayeredWindow)
            self.win.deiconify()
            self.win.attributes('-topmost', True)
            
            windll.user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                       SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)

            # Start animation
            self.root.after(50, self.animate)
            
        except Exception as e:
            print(f"[DEBUG] Bubble window creation error: {e}")
            import traceback
            traceback.print_exc()
            self.destroy()

    def get_wobbly_image(self):
        """Get current frame with wobble effect - optimized"""
        t = self.time_alive
        # Simplified wobble - less math
        wobble = 0.06 * math.sin(t * 2.5 + self.wobble_offset)
        scale = self.scale_base + wobble
        new_w = max(10, int(self.base_w * scale))
        new_h = max(10, int(self.base_h * scale))

        # Use NEAREST for speed, skip rotation when not popping
        resized = self.original_pil.resize((new_w, new_h), Image.Resampling.NEAREST)
        
        # Only rotate when popping (saves CPU during normal animation)
        if self.is_popping or abs(self.angle) > 5:
            rotated = resized.rotate(self.angle, expand=True, resample=Image.Resampling.NEAREST)
        else:
            rotated = resized

        canvas = Image.new('RGBA', (self.canvas_size, self.canvas_size), (0, 0, 0, 0))
        rot_w, rot_h = rotated.size
        offset_x = (self.canvas_size - rot_w) // 2
        offset_y = (self.canvas_size - rot_h) // 2
        canvas.paste(rotated, (offset_x, offset_y), rotated)
        return canvas

    def update_physics(self):
        """Update position and animation"""
        self.time_alive += 0.03  # Slower time progression
        self.pos_y -= self.base_speed

        t = self.time_alive
        if self.anim_type == 0:
            offset = math.sin(t * 2) * 25
            self.pos_x = self.start_x + offset
            self.angle = (self.angle + 0.5) % 360
        elif self.anim_type == 1:
            offset = math.sin(t * 2.5) * 30
            self.pos_x = self.start_x + offset
            self.angle = (self.angle + 0.2) % 360
        elif self.anim_type == 2:
            offset = math.cos(t * 1.8) * 25
            self.pos_x = self.start_x + offset
            self.angle = (self.angle - 1.0) % 360
        elif self.anim_type == 3:
            offset = (math.sin(t) * 30) + (math.cos(t * 2) * 15)
            self.pos_x = self.start_x + offset
            self.angle = (self.angle + 0.8) % 360

    def animate(self):
        if not self.alive:
            return
        
        # Check if video is pending - if so, destroy immediately
        if RESOURCE_MGR_AVAILABLE:
            try:
                if resource_mgr.is_video_active():
                    self.pop()
                    return
            except:
                pass

        if self.is_popping:
            self.scale_base += 0.06
            self.fade_alpha -= 25  # Faster fade for quicker cleanup
            self.angle += 3
            if self.fade_alpha <= 0:
                self.destroy()
                return
        else:
            self.update_physics()
            if self.pos_y < -self.canvas_size:
                self.miss()
                return

        try:
            current_pil = self.get_wobbly_image()
            draw_x = int(self.pos_x)
            draw_y = int(self.pos_y)
            make_transparent_window(self.hwnd, current_pil, draw_x, draw_y, int(self.fade_alpha))
            
            # Move hitbox window to follow bubble center
            if self.hitbox_win and self.hitbox_win.winfo_exists():
                hitbox_offset = (self.canvas_size - self.hitbox_size) // 2
                hitbox_x = draw_x + hitbox_offset
                hitbox_y = draw_y + hitbox_offset
                self.hitbox_win.geometry(f"{self.hitbox_size}x{self.hitbox_size}+{hitbox_x}+{hitbox_y}")
                # Update hitbox alpha during pop
                if self.is_popping:
                    self.hitbox_win.attributes('-alpha', max(0.01, self.fade_alpha / 255 * 0.01))
        except:
            self.destroy()
            return

        self.root.after(50, self.animate)  # ~20 FPS (reduced from 28 for performance)

    def play_sound(self):
        if not AUDIO_AVAILABLE:
            return

        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            sounds_dir = os.path.join(script_dir, "assets", "sounds")
            vol = max(0.05, min(1.0, max(0.0, self.volume)) ** 1.5)  # Gentler curve, minimum 5%

            pop_files = ["Pop.mp3", "Pop2.mp3", "Pop3.mp3"]
            chosen_pop = random.choice(pop_files)
            pop_path = os.path.join(sounds_dir, chosen_pop)

            if os.path.exists(pop_path):
                sound = pygame.mixer.Sound(pop_path)
                sound.set_volume(vol)
                sound.play()

            chance = random.random()
            if chance < 0.03:
                burst_path = os.path.join(sounds_dir, "burst.mp3")
                if os.path.exists(burst_path):
                    sound = pygame.mixer.Sound(burst_path)
                    sound.set_volume(vol)
                    sound.play()
            elif chance < 0.08:
                gg_path = os.path.join(sounds_dir, "GG.mp3")
                if os.path.exists(gg_path):
                    sound = pygame.mixer.Sound(gg_path)
                    sound.set_volume(vol)
                    sound.play()
        except:
            pass

    def pop(self, event=None):
        if not self.alive or self.is_popping:
            return
        self.is_popping = True
        self.play_sound()
        if self.on_pop:
            try:
                self.on_pop()
            except:
                pass

    def miss(self):
        if self.on_miss:
            try:
                self.on_miss()
            except:
                pass
        self.destroy()

    def destroy(self):
        if not self.alive:
            return
        self.alive = False
        Bubble.count = max(0, Bubble.count - 1)

        # Remove from instances list
        if self in Bubble.instances:
            Bubble.instances.remove(self)

        # Unregister from resource manager
        if RESOURCE_MGR_AVAILABLE:
            try:
                resource_mgr.register_effect('bubble', False)
            except:
                pass

        # Destroy hitbox window
        if self.hitbox_win:
            try:
                self.hitbox_win.destroy()
            except:
                pass
            self.hitbox_win = None

        # Destroy visual window
        if self.win:
            try:
                self.win.destroy()
            except:
                pass
            self.win = None
        self.hwnd = None
        self.original_pil = None
        self._first_frame = None

    @classmethod
    def pop_all(cls):
        """Pop all active bubbles (plays sounds and triggers callbacks) - fast cleanup"""
        # Pop all bubbles without waiting
        for bubble in cls.instances[:]:  # Copy list to avoid modification during iteration
            if bubble.alive:
                if not bubble.is_popping:
                    bubble.play_sound()  # Play sound
                    if bubble.on_pop:
                        try:
                            bubble.on_pop()
                        except:
                            pass
                # Force immediate destroy
                bubble.alive = False
                try:
                    if bubble.hitbox_win:
                        bubble.hitbox_win.destroy()
                    if bubble.win:
                        bubble.win.destroy()
                except:
                    pass

        # Clear tracking
        cls.instances.clear()
        cls.count = 0

        # Reset resource manager
        if RESOURCE_MGR_AVAILABLE:
            try:
                resource_mgr.active_effects['bubbles'] = 0
            except:
                pass