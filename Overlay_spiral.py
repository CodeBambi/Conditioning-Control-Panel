import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageSequence
import ctypes
from ctypes import windll, wintypes, byref, c_int, c_byte, Structure, sizeof
import os
import threading
import time

# --- WIN32 API CONSTANTS ---
GWL_EXSTYLE = -20
GWL_HWNDPARENT = -8
GWL_STYLE = -16
WS_EX_LAYERED = 0x80000
WS_EX_TOPMOST = 0x00008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_POPUP = 0x80000000
ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01

# Z-Order Constants
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SW_SHOWNOACTIVATE = 4


class BITMAPINFOHEADER(Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD)
    ]


class BLENDFUNCTION(Structure):
    _fields_ = [
        ('BlendOp', c_byte),
        ('BlendFlags', c_byte),
        ('SourceConstantAlpha', c_byte),
        ('AlphaFormat', c_byte),
    ]


class Point(Structure):
    _fields_ = [('x', c_int), ('y', c_int)]


class Size(Structure):
    _fields_ = [('cx', c_int), ('cy', c_int)]


def make_transparent_window(hwnd, pil_image, x, y, alpha_val=255):
    """Paint a PIL image onto a HWND using UpdateLayeredWindow."""
    if pil_image.mode != 'RGBA':
        pil_image = pil_image.convert('RGBA')

    # Apply alpha to entire image
    if alpha_val < 255:
        alpha_layer = pil_image.split()[3]
        alpha_layer = alpha_layer.point(lambda p: int(p * alpha_val / 255))
        r, g, b, _ = pil_image.split()
        pil_image = Image.merge('RGBA', (r, g, b, alpha_layer))

    # Convert to RGBa for proper alpha handling
    if pil_image.mode != 'RGBa':
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

    ctypes.memmove(pvBits, img_data, len(img_data))
    oldBitmap = windll.gdi32.SelectObject(hdcMem, hBitmap)

    ptSrc = Point(0, 0)
    ptDst = Point(x, y)
    sz = Size(w, h)

    blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)

    windll.user32.UpdateLayeredWindow(hwnd, hdcScreen, byref(ptDst), byref(sz),
                                      hdcMem, byref(ptSrc), 0, byref(blend), ULW_ALPHA)

    windll.gdi32.SelectObject(hdcMem, oldBitmap)
    windll.gdi32.DeleteObject(hBitmap)
    windll.gdi32.DeleteDC(hdcMem)
    windll.user32.ReleaseDC(0, hdcScreen)


class TopmostManager:
    """Background thread that maintains topmost status"""

    def __init__(self):
        self.windows = set()
        self.running = True
        self.thread = threading.Thread(target=self._maintain_topmost, daemon=True)
        self.thread.start()

    def add_window(self, hwnd):
        self.windows.add(hwnd)

    def remove_window(self, hwnd):
        self.windows.discard(hwnd)

    def _maintain_topmost(self):
        while self.running:
            for hwnd in list(self.windows):
                try:
                    windll.user32.SetWindowPos(
                        hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
                    )
                except:
                    pass
            time.sleep(0.1)

    def stop(self):
        self.running = False


class GIFOverlay:
    def __init__(self, root, gif_path, initial_alpha=77):
        self.root = root
        self.gif_path = gif_path
        self.alpha = initial_alpha
        self.running = True

        # Get screen dimensions first
        self.screen_w = root.winfo_screenwidth()
        self.screen_h = root.winfo_screenheight()

        # Load GIF frames
        self.frames = []
        self.frame_delays = []
        self.load_gif()

        if not self.frames:
            print("Error: Could not load GIF")
            return

        print(f"Creating overlay window {self.screen_w}x{self.screen_h}")

        # Create overlay window
        self.overlay = tk.Toplevel(root)
        self.overlay.overrideredirect(True)
        self.overlay.attributes('-topmost', True)
        self.overlay.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
        self.overlay.configure(bg='black')
        self.overlay.update()

        # Get window handle
        self.hwnd = windll.user32.GetParent(self.overlay.winfo_id())
        if self.hwnd == 0:
            self.hwnd = self.overlay.winfo_id()

        print(f"HWND: {self.hwnd}")

        # Setup window styles for click-through and always on top
        self._setup_window_styles()

        # Start topmost manager
        self.topmost_manager = TopmostManager()
        self.topmost_manager.add_window(self.hwnd)

        # Start animation
        self.current_frame = 0
        self.animate()

    def load_gif(self):
        """Load all frames from the GIF"""
        try:
            print(f"Loading GIF: {self.gif_path}")
            img = Image.open(self.gif_path)

            for frame in ImageSequence.Iterator(img):
                # Convert to RGBA
                frame_rgba = frame.convert('RGBA')

                # Scale to fit screen while maintaining aspect ratio
                img_w, img_h = frame_rgba.size
                screen_ratio = self.screen_w / self.screen_h
                img_ratio = img_w / img_h

                scale = max(
                    self.screen_w / img_w,
                    self.screen_h / img_h
                )

                new_w = int(img_w * scale)
                new_h = int(img_h * scale)

                frame_rgba = frame_rgba.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # Center on screen
                final_frame = Image.new('RGBA', (self.screen_w, self.screen_h), (0, 0, 0, 0))
                x_offset = (self.screen_w - new_w) // 2
                y_offset = (self.screen_h - new_h) // 2
                final_frame.paste(frame_rgba, (x_offset, y_offset), frame_rgba)

                self.frames.append(final_frame)

                # Get frame duration (default 100ms if not specified)
                try:
                    duration = frame.info.get('duration', 100)
                except:
                    duration = 100
                self.frame_delays.append(max(duration, 20))  # Minimum 20ms

            print(f"Loaded {len(self.frames)} frames")
        except Exception as e:
            print(f"Error loading GIF: {e}")
            import traceback
            traceback.print_exc()

    def _setup_window_styles(self):
        """Setup window for click-through and always on top"""
        # Detach from parent
        windll.user32.SetWindowLongW(self.hwnd, GWL_HWNDPARENT, 0)

        # Set as popup
        style = windll.user32.GetWindowLongW(self.hwnd, GWL_STYLE)
        style = style | WS_POPUP
        windll.user32.SetWindowLongW(self.hwnd, GWL_STYLE, style)

        # Extended styles: layered, topmost, transparent (click-through), no activate
        ex_style = windll.user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
        ex_style = ex_style | WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        windll.user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, ex_style)

        # Initial topmost positioning
        windll.user32.SetWindowPos(
            self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
        )

        # Show without activating
        windll.user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)

    def animate(self):
        """Animate the GIF frames"""
        if not self.running or not self.frames:
            return

        try:
            frame = self.frames[self.current_frame]
            make_transparent_window(self.hwnd, frame, 0, 0, self.alpha)

            delay = self.frame_delays[self.current_frame]
            self.current_frame = (self.current_frame + 1) % len(self.frames)

            self.root.after(delay, self.animate)
        except Exception as e:
            print(f"Animation error: {e}")
            import traceback
            traceback.print_exc()

    def set_alpha(self, alpha):
        """Update overlay transparency"""
        self.alpha = int(alpha)

    def stop_overlay(self, event=None):
        """Stop the overlay"""
        print("Stopping overlay")
        self.running = False
        self.topmost_manager.stop()
        try:
            self.overlay.destroy()
        except:
            pass


class ControlPanel:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GIF Overlay Control")
        self.root.geometry("450x180")
        self.root.resizable(False, False)

        self.overlay = None
        self.gif_path = None

        # Find GIF in assets folder
        self._find_gif()

        # Title
        title = tk.Label(self.root, text="GIF Overlay Controller", font=("Arial", 14, "bold"))
        title.pack(pady=10)

        # GIF path display
        path_frame = tk.Frame(self.root)
        path_frame.pack(pady=5, padx=20, fill='x')

        tk.Label(path_frame, text="GIF:", font=("Arial", 10)).pack(side='left')
        self.path_label = tk.Label(path_frame, text="No GIF selected", font=("Arial", 9), fg="gray")
        self.path_label.pack(side='left', padx=5, fill='x', expand=True)

        btn_browse = tk.Button(path_frame, text="Browse", command=self._browse_gif,
                               bg="#4CAF50", fg="white", font=("Arial", 9))
        btn_browse.pack(side='right')

        # Transparency slider
        slider_frame = tk.Frame(self.root)
        slider_frame.pack(pady=10, padx=20, fill='x')

        tk.Label(slider_frame, text="Opacity:", font=("Arial", 10)).pack(side='left')

        self.alpha_var = tk.IntVar(value=30)
        self.slider = ttk.Scale(slider_frame, from_=0, to=40, orient='horizontal',
                                variable=self.alpha_var, command=self._on_alpha_change)
        self.slider.pack(side='left', fill='x', expand=True, padx=10)

        self.alpha_label = tk.Label(slider_frame, text="30%", font=("Arial", 10), width=5)
        self.alpha_label.pack(side='right')

        # Buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=15)

        self.btn_start = tk.Button(btn_frame, text="Start Overlay", command=self._start_overlay,
                                   bg="#2196F3", fg="white", font=("Arial", 11, "bold"),
                                   width=15, height=2)
        self.btn_start.pack(side='left', padx=5)

        self.btn_stop = tk.Button(btn_frame, text="Stop (ESC)", command=self._stop_overlay,
                                  bg="#f44336", fg="white", font=("Arial", 11, "bold"),
                                  width=15, height=2, state='disabled')
        self.btn_stop.pack(side='left', padx=5)

        # Info label
        info = tk.Label(self.root, text="Press ESC anywhere to stop overlay",
                        font=("Arial", 9), fg="gray")
        info.pack(pady=5)

        # Bind ESC globally
        self.root.bind('<Escape>', self._stop_overlay)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if self.gif_path:
            filename = os.path.basename(self.gif_path)
            self.path_label.config(text=filename, fg="black")
            print(f"Found GIF: {filename}")

    def _find_gif(self):
        """Find first GIF in assets folder"""
        # Try multiple possible locations
        search_paths = [
            "assets",
            os.path.join("assets", "images"),
            "."
        ]

        for assets_dir in search_paths:
            if os.path.exists(assets_dir):
                for file in os.listdir(assets_dir):
                    if file.lower().endswith('.gif'):
                        self.gif_path = os.path.join(assets_dir, file)
                        print(f"Found GIF at: {self.gif_path}")
                        return

        print("No GIF found in any search location")

    def _browse_gif(self):
        """Browse for a GIF file"""
        path = filedialog.askopenfilename(
            title="Select a GIF file",
            filetypes=[("GIF files", "*.gif"), ("All files", "*.*")]
        )
        if path:
            self.gif_path = path
            self.path_label.config(text=os.path.basename(path), fg="black")
            print(f"Selected GIF: {path}")

    def _on_alpha_change(self, value):
        """Update alpha label and overlay if running"""
        alpha_percent = int(float(value))
        self.alpha_label.config(text=f"{alpha_percent}%")

        if self.overlay:
            # Convert percentage to 0-255
            alpha_val = int(255 * alpha_percent / 100)
            self.overlay.set_alpha(alpha_val)

    def _start_overlay(self):
        """Start the overlay"""
        if not self.gif_path or not os.path.exists(self.gif_path):
            messagebox.showerror("Error", "Please select a valid GIF file")
            return

        if self.overlay:
            self._stop_overlay()

        # Convert percentage to 0-255
        alpha_val = int(255 * self.alpha_var.get() / 100)

        print(f"Starting overlay with alpha: {alpha_val}")
        self.overlay = GIFOverlay(self.root, self.gif_path, alpha_val)

        self.btn_start.config(state='disabled')
        self.btn_stop.config(state='normal')

    def _stop_overlay(self, event=None):
        """Stop the overlay"""
        if self.overlay:
            self.overlay.stop_overlay()
            self.overlay = None

        self.btn_start.config(state='normal')
        self.btn_stop.config(state='disabled')

    def _on_close(self):
        """Clean up and close"""
        self._stop_overlay()
        self.root.destroy()

    def run(self):
        """Start the application"""
        self.root.mainloop()


if __name__ == "__main__":
    print("Starting GIF Overlay Application...")
    app = ControlPanel()
    app.run()