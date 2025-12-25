import tkinter as tk
from tkinter import simpledialog, messagebox
import customtkinter as ctk
import math
import random
from ctypes import windll
from config import THEME


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

        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        ctk.CTkLabel(header_frame, text=f"{title} Manager", font=(THEME["font_family"], 16, "bold"),
                     text_color=THEME["fg"]).pack(side="left")
        ctk.CTkButton(header_frame, text="Sort A-Z", width=80, height=24, fg_color=THEME["accent"],
                      command=self.sort_list).pack(side="right")

        # Scrollable List
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=THEME["card_bg"])
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)

        # Controls
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
        new_dict = {k: self.data[k] for k in sorted_keys}
        # Clear original and update (to keep reference if needed, though dict order is insertion based in modern python)
        self.data.clear()
        self.data.update(new_dict)
        self.refresh_list()

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

        # Bouncing Physics
        speed = 2.0
        angle = random.uniform(0, 2 * math.pi)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.min_x = offset_x
        self.max_x = offset_x + bounds_w
        self.min_y = offset_y
        self.max_y = offset_y + bounds_h

        # Transparency setup
        TRANS_KEY = "#000001"
        self.config(bg=TRANS_KEY)
        self.wm_attributes("-transparentcolor", TRANS_KEY)
        self.attributes("-alpha", 1.0)

        self.canvas = tk.Canvas(self, bg=TRANS_KEY, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Measure text size
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

        # Make clicks pass through transparent areas (Windows specific)
        try:
            hwnd = windll.user32.GetParent(self.winfo_id())
            # WS_EX_LAYERED | WS_EX_TRANSPARENT
            windll.user32.SetWindowLongW(hwnd, -20, 0x08000000 | 0x00000008)
        except:
            pass

        # Draw Outline (Stroke)
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

        # Draw Main Text
        self.text_id = self.canvas.create_text(center_x, center_y, text=text, font=font_spec,
                                               width=wrap_w, fill="#FF00FF", justify="center")
        self.canvas.tag_bind(self.text_id, "<Button-1>", self.handle_click)
        self.canvas.bind("<Button-1>", self.handle_click)

        self.animate_move()

    def animate_move(self):
        if not self.winfo_exists() or self.clicked: return
        self.pos_x += self.vx
        self.pos_y += self.vy

        # Bounce checks
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