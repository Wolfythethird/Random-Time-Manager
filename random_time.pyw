"""
Random Work/Fun Timer - Liquid Glass CustomTkinter GUI (Spacing Fix + Sound Alerts)
"""

import time
import threading
import random
import queue
import os
import ctypes
import tkinter as tk
from tkinter import filedialog, messagebox
from ctypes import wintypes

import customtkinter as ctk
from PIL import Image, ImageTk, ImageFilter, ImageDraw

try:
    from plyer import notification as plyer_notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False


UNIT_TO_SECONDS = {
    "Seconds": 1,
    "Minutes": 60,
    "Hours": 3600,
}

WORK_COLOR = "#e74c3c"
FUN_COLOR = "#3498db"
IDLE_COLOR = "#9e9e9e"
CARD_BG_COLOR = "#1c1c1f"


class RandoTimer:
    """Background worker that fires random Work/Fun switches."""
    def __init__(self, event_queue: queue.Queue):
        self.event_queue = event_queue
        self.work_bounds = (1.0, 1.0)
        self.fun_bounds = (1.0, 1.0)
        self.work = False
        self._stop_event = threading.Event()
        self._thread = None

    def configure(self, work_min, work_max, fun_min, fun_max, start_mode_working):
        self.work_bounds = (work_min, work_max)
        self.fun_bounds = (fun_min, fun_max)
        self.work = start_mode_working

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def is_running(self):
        return self._thread is not None and self._thread.is_alive() and not self._stop_event.is_set()

    def _run(self):
        while not self._stop_event.is_set():
            if self.work:
                random_time = random.uniform(self.work_bounds[0], self.work_bounds[1])
            else:
                random_time = random.uniform(self.fun_bounds[0], self.fun_bounds[1])

            waited = 0.0
            step = 0.1
            while waited < random_time:
                if self._stop_event.is_set():
                    return
                sleep_for = min(step, random_time - waited)
                time.sleep(sleep_for)
                waited += sleep_for

            if self._stop_event.is_set():
                return

            if not self.work:
                message = f"Start Working Now! (Waited {random_time:.2f}s)"
                self.work = True
                mode = "WORK"
            else:
                message = f"Stop Working! Time for FUN! (Waited {random_time:.2f}s)"
                self.work = False
                mode = "FUN"

            self.event_queue.put(("switch", (mode, message)))


class RandoTimerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Random Work / Fun Timer")
        self.geometry("600x880")
        self.minsize(550, 750)

        icon_path = os.path.join(os.path.dirname(__file__), "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.event_queue = queue.Queue()
        self.timer = RandoTimer(self.event_queue)

        self.bg_original_image = None
        self.bg_photo = None
        self._resize_timer = None
        self._last_w = 0
        self._last_h = 0

        self._enable_rounded_window_corners()
        self._build_layout()
        self._poll_queue()

    def _enable_rounded_window_corners(self):
        if os.name != "nt":
            return
        try:
            hwnd = self.winfo_id()
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                ctypes.c_int(DWMWA_WINDOW_CORNER_PREFERENCE),
                ctypes.byref(ctypes.c_uint(DWMWCP_ROUND)),
                ctypes.sizeof(ctypes.c_uint),
            )
        except Exception:
            pass

    def _build_layout(self):
        # Master Canvas
        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#0d0d0f")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.scrollbar = ctk.CTkScrollbar(self, command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        
        self.bg_image_id = self.canvas.create_image(0, 0, anchor="nw")
        
        # --- TITLE ---
        self.txt_title = self.canvas.create_text(0, 0, text="Random Work/Fun Timer", font=("Segoe UI", 24, "bold"), fill="white", anchor="n")

        # --- CARD 1: SETTINGS ---
        self.txt_c1_title = self.canvas.create_text(0, 0, text="Time Settings", font=("Segoe UI", 16, "bold"), fill="white", anchor="nw")
        
        self.txt_work_range = self.canvas.create_text(0, 0, text="Work Range:", fill=WORK_COLOR, font=("Segoe UI", 13, "bold"), anchor="nw")
        self.work_min_var = ctk.StringVar(value="30")
        self.win_work_min = self.canvas.create_window(0, 0, window=ctk.CTkEntry(self.canvas, textvariable=self.work_min_var, width=60, justify="center", bg_color=CARD_BG_COLOR, fg_color=CARD_BG_COLOR), anchor="nw")
        self.txt_work_to = self.canvas.create_text(0, 0, text="to", fill="#cccccc", font=("Segoe UI", 13), anchor="nw")
        self.work_max_var = ctk.StringVar(value="60")
        self.win_work_max = self.canvas.create_window(0, 0, window=ctk.CTkEntry(self.canvas, textvariable=self.work_max_var, width=60, justify="center", bg_color=CARD_BG_COLOR, fg_color=CARD_BG_COLOR), anchor="nw")

        self.txt_fun_range = self.canvas.create_text(0, 0, text="Fun Range:", fill=FUN_COLOR, font=("Segoe UI", 13, "bold"), anchor="nw")
        self.fun_min_var = ctk.StringVar(value="5")
        self.win_fun_min = self.canvas.create_window(0, 0, window=ctk.CTkEntry(self.canvas, textvariable=self.fun_min_var, width=60, justify="center", bg_color=CARD_BG_COLOR, fg_color=CARD_BG_COLOR), anchor="nw")
        self.txt_fun_to = self.canvas.create_text(0, 0, text="to", fill="#cccccc", font=("Segoe UI", 13), anchor="nw")
        self.fun_max_var = ctk.StringVar(value="15")
        self.win_fun_max = self.canvas.create_window(0, 0, window=ctk.CTkEntry(self.canvas, textvariable=self.fun_max_var, width=60, justify="center", bg_color=CARD_BG_COLOR, fg_color=CARD_BG_COLOR), anchor="nw")

        self.txt_time_unit = self.canvas.create_text(0, 0, text="Time Unit:", fill="#cccccc", font=("Segoe UI", 13), anchor="nw")
        self.unit_var = ctk.StringVar(value="Minutes")
        self.win_time_unit = self.canvas.create_window(0, 0, window=ctk.CTkComboBox(self.canvas, values=list(UNIT_TO_SECONDS.keys()), variable=self.unit_var, state="readonly", width=140, bg_color=CARD_BG_COLOR, fg_color=CARD_BG_COLOR), anchor="nw")

        # Native Radio Buttons
        self.txt_start_mode = self.canvas.create_text(0, 0, text="Start Mode:", fill="#cccccc", font=("Segoe UI", 13), anchor="nw")
        self.start_mode_var = ctk.StringVar(value="Fun")
        
        self.win_start_work = self.canvas.create_window(0, 0, window=ctk.CTkRadioButton(self.canvas, text="Working", variable=self.start_mode_var, value="Work", text_color=WORK_COLOR, font=("Segoe UI", 13), bg_color=CARD_BG_COLOR), anchor="nw")
        self.win_start_fun = self.canvas.create_window(0, 0, window=ctk.CTkRadioButton(self.canvas, text="Fun", variable=self.start_mode_var, value="Fun", text_color=FUN_COLOR, font=("Segoe UI", 13), bg_color=CARD_BG_COLOR), anchor="nw")

        # --- CARD 2: APPEARANCE ---
        self.txt_c2_title = self.canvas.create_text(0, 0, text="Appearance & Alerts", font=("Segoe UI", 16, "bold"), fill="white", anchor="nw")
        self.win_btn_bg = self.canvas.create_window(0, 0, window=ctk.CTkButton(self.canvas, text="Choose Background", command=self._choose_background, width=150, bg_color=CARD_BG_COLOR), anchor="nw")
        self.win_btn_clear = self.canvas.create_window(0, 0, window=ctk.CTkButton(self.canvas, text="Clear", command=self._clear_background, width=60, fg_color="transparent", border_width=1, bg_color=CARD_BG_COLOR), anchor="nw")
        self.txt_filename = self.canvas.create_text(0, 0, text="No background selected", fill="#888888", font=("Segoe UI", 12), anchor="nw")
        
        self.txt_blur = self.canvas.create_text(0, 0, text="Background Blur:", fill="#cccccc", font=("Segoe UI", 13), anchor="nw")
        self.bg_blur_var = ctk.DoubleVar(value=0.0)
        self.slider_blur = ctk.CTkSlider(self.canvas, from_=0.0, to=20.0, variable=self.bg_blur_var, command=self._on_blur_change, bg_color=CARD_BG_COLOR)
        self.win_blur_slider = self.canvas.create_window(0, 0, window=self.slider_blur, anchor="nw")

        # Native Checkbox
        self.notify_var = ctk.BooleanVar(value=True)
        notif_text = "Desktop notifications on mode switch" if PLYER_AVAILABLE else "Desktop notifications (install 'plyer')"
        self.win_notify = self.canvas.create_window(0, 0, window=ctk.CTkCheckBox(self.canvas, text=notif_text, variable=self.notify_var, state="normal" if PLYER_AVAILABLE else "disabled", text_color="#cccccc", font=("Segoe UI", 13), bg_color=CARD_BG_COLOR), anchor="nw")

        # --- CARD 3: STATUS ---
        self.txt_status = self.canvas.create_text(0, 0, text="IDLE", font=("Segoe UI", 38, "bold"), fill=IDLE_COLOR, anchor="center")
        self.txt_substatus = self.canvas.create_text(0, 0, text="Not running", font=("Segoe UI", 13), fill="#888888", anchor="center")
        
        self.btn_start = ctk.CTkButton(self.canvas, text="START TIMER", font=("Segoe UI", 13, "bold"), command=self._on_start, fg_color="#27ae60", hover_color="#1e8449", height=40, width=140, bg_color=CARD_BG_COLOR)
        self.win_btn_start = self.canvas.create_window(0, 0, window=self.btn_start, anchor="n")
        self.btn_stop = ctk.CTkButton(self.canvas, text="STOP TIMER", font=("Segoe UI", 13, "bold"), command=self._on_stop, state="disabled", fg_color="#c0392b", hover_color="#922b21", height=40, width=140, bg_color=CARD_BG_COLOR)
        self.win_btn_stop = self.canvas.create_window(0, 0, window=self.btn_stop, anchor="n")

        # --- CARD 4: LOG ---
        self.txt_c4_title = self.canvas.create_text(0, 0, text="Activity Log", font=("Segoe UI", 16, "bold"), fill="white", anchor="nw")
        self.log_text_widget = ctk.CTkTextbox(self.canvas, height=130, state="disabled", fg_color="#151518", bg_color=CARD_BG_COLOR)
        self.win_log = self.canvas.create_window(0, 0, window=self.log_text_widget, anchor="nw")

        self.canvas.bind("<Configure>", self._on_canvas_configure)

    # --- Layout Engine & Glass Rendering ---
    def _on_canvas_configure(self, event):
        w = max(event.width, 300)
        self._reposition_elements(w)
        self._queue_bg_resize(w, max(event.height, 1050))
        self.canvas.configure(scrollregion=(0, 0, w, 1030))

    def _reposition_elements(self, w):
        c_x = 40  
        pad_x = 20

        # Title
        self.canvas.coords(self.txt_title, w/2, 20)

        # Card 1: Time Settings (y: 70 -> 310)
        c1_y = 70
        self.canvas.coords(self.txt_c1_title, c_x, c1_y + 15)
        self.canvas.coords(self.txt_work_range, c_x, c1_y + 55)
        self.canvas.coords(self.win_work_min, c_x + 110, c1_y + 47)
        self.canvas.coords(self.txt_work_to, c_x + 185, c1_y + 55)
        self.canvas.coords(self.win_work_max, c_x + 215, c1_y + 47)

        self.canvas.coords(self.txt_fun_range, c_x, c1_y + 95)
        self.canvas.coords(self.win_fun_min, c_x + 110, c1_y + 87)
        self.canvas.coords(self.txt_fun_to, c_x + 185, c1_y + 95)
        self.canvas.coords(self.win_fun_max, c_x + 215, c1_y + 87)

        self.canvas.coords(self.txt_time_unit, c_x, c1_y + 135)
        self.canvas.coords(self.win_time_unit, c_x + 110, c1_y + 127)

        self.canvas.coords(self.txt_start_mode, c_x, c1_y + 175)
        self.canvas.coords(self.win_start_work, c_x + 110, c1_y + 173)
        self.canvas.coords(self.win_start_fun, c_x + 210, c1_y + 173)

        # Card 2: Appearance & Alerts (y: 330 -> 540)
        c2_y = 330
        self.canvas.coords(self.txt_c2_title, c_x, c2_y + 15)
        self.canvas.coords(self.win_btn_bg, c_x, c2_y + 55)
        self.canvas.coords(self.win_btn_clear, c_x + 180, c2_y + 55)
        self.canvas.coords(self.txt_filename, c_x, c2_y + 110)

        self.canvas.coords(self.txt_blur, c_x, c2_y + 145)
        self.canvas.itemconfigure(self.win_blur_slider, width=max(220, w - (pad_x * 2) - 40))
        self.canvas.coords(self.win_blur_slider, c_x, c2_y + 170)

        self.canvas.coords(self.win_notify, c_x, c2_y + 205)

        # Card 3: Status & Controls (y: 560 -> 770)
        c3_y = 560
        self.canvas.coords(self.txt_status, w/2, c3_y + 45)
        self.canvas.coords(self.txt_substatus, w/2, c3_y + 95)

        # Keep buttons centered and spread apart cleanly.
        btn_y = c3_y + 130
        self.canvas.coords(self.win_btn_start, w/2 - 140, btn_y)
        self.canvas.coords(self.win_btn_stop, w/2 + 140, btn_y)

        # Card 4: Activity Log (y: 790 -> 1010)
        c4_y = 790
        self.canvas.coords(self.txt_c4_title, c_x, c4_y + 15)
        self.canvas.itemconfigure(self.win_log, width=w - (pad_x*2) - 40)
        self.canvas.coords(self.win_log, c_x, c4_y + 50)

    def _queue_bg_resize(self, w, h):
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
        self._last_w = w
        self._last_h = h
        self._resize_timer = self.after(100, self._apply_bg_image)

    def _apply_bg_image(self):
        w = max(self._last_w, 10)
        h = max(self._last_h, 1050)

        if self.bg_original_image:
            img = self.bg_original_image
            src_ratio = img.width / img.height
            dst_ratio = w / h
            if src_ratio > dst_ratio:
                new_h = h
                new_w = int(new_h * src_ratio)
            else:
                new_w = w
                new_h = int(new_w / src_ratio)
            
            resized = img.resize((new_w, new_h), Image.LANCZOS)
            left = (resized.width - w) // 2
            top = (resized.height - h) // 2
            base_img = resized.crop((left, top, left + w, top + h))

            blur_radius = self.bg_blur_var.get()
            if blur_radius > 0:
                base_img = base_img.filter(ImageFilter.GaussianBlur(blur_radius))
        else:
            base_img = Image.new("RGB", (w, h), "#0d0d0f")

        glass_img = base_img.filter(ImageFilter.GaussianBlur(35))
        tint = Image.new("RGBA", (w, h), (28, 28, 31, 190)) 
        glass_img = Image.alpha_composite(glass_img.convert("RGBA"), tint)

        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        pad_x = 20
        cards_bounds = [
            (pad_x, 70, w - pad_x, 310),    # Card 1
            (pad_x, 330, w - pad_x, 540),   # Card 2
            (pad_x, 560, w - pad_x, 770),   # Card 3
            (pad_x, 790, w - pad_x, 1010)   # Card 4
        ]
        
        for box in cards_bounds:
            draw.rounded_rectangle(box, radius=12, fill=255)

        final_img = Image.composite(glass_img, base_img.convert("RGBA"), mask)

        self.bg_photo = ImageTk.PhotoImage(final_img)
        self.canvas.itemconfigure(self.bg_image_id, image=self.bg_photo)

    # --- Actions ---
    def _choose_background(self):
        path = filedialog.askopenfilename(
            title="Choose a background photo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self.bg_original_image = Image.open(path).convert("RGB")
            self.canvas.itemconfigure(self.txt_filename, text=os.path.basename(path))
            self._apply_bg_image()
        except Exception as exc:
            messagebox.showerror("Couldn't open image", f"Error:\n{exc}")

    def _clear_background(self):
        self.bg_original_image = None
        self.bg_blur_var.set(0.0)
        self.canvas.itemconfigure(self.txt_filename, text="No background selected")
        self._apply_bg_image()

    def _on_blur_change(self, _value=None):
        self._queue_bg_resize(self._last_w, self._last_h)

    def _on_start(self):
        try:
            w_min, w_max = float(self.work_min_var.get()), float(self.work_max_var.get())
            f_min, f_max = float(self.fun_min_var.get()), float(self.fun_max_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "All time ranges must be numbers.")
            return

        if any(v <= 0 for v in (w_min, w_max, f_min, f_max)):
            messagebox.showerror("Invalid input", "Times must be greater than 0.")
            return

        if w_min > w_max or f_min > f_max:
            messagebox.showerror("Invalid input", "Min time cannot be greater than Max time.")
            return

        multiplier = UNIT_TO_SECONDS[self.unit_var.get()]
        start_working = self.start_mode_var.get() == "Work"
        
        self.timer.configure(
            work_min=w_min * multiplier, work_max=w_max * multiplier,
            fun_min=f_min * multiplier, fun_max=f_max * multiplier,
            start_mode_working=start_working
        )
        self.timer.start()

        self._set_status(start_working)
        self.canvas.itemconfigure(self.txt_substatus, text="Running...")
        unit = self.unit_var.get().lower()
        self._log(f"Started. Work [{w_min}-{w_max} {unit}] | Fun [{f_min}-{f_max} {unit}].")

        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")

    def _on_stop(self):
        self.timer.stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.canvas.itemconfigure(self.txt_status, text="IDLE", fill=IDLE_COLOR)
        self.canvas.itemconfigure(self.txt_substatus, text="Not running")
        self._log("Timer stopped.")

    def _set_status(self, working: bool):
        if working:
            self.canvas.itemconfigure(self.txt_status, text="WORK", fill=WORK_COLOR)
        else:
            self.canvas.itemconfigure(self.txt_status, text="FUN", fill=FUN_COLOR)

    def _log(self, message: str):
        self.log_text_widget.configure(state="normal")
        timestamp = time.strftime("%H:%M:%S")
        self.log_text_widget.insert("end", f"[{timestamp}] {message}\n")
        self.log_text_widget.see("end")
        self.log_text_widget.configure(state="disabled")

    def _send_notification(self, mode: str, message: str):
        # ---------------------------------------------------------
        # NEW: Play a sound without freezing the GUI
        # ---------------------------------------------------------
        if self.notify_var.get():
            try:
                if os.name == "nt":
                    import winsound
                    # Play different sounds based on the mode
                    # SND_ASYNC makes sure the GUI doesn't freeze while playing
                    # Note: You can replace "SystemHand" or "SystemAsterisk" with "your_sound.wav"
                    if mode == "WORK":
                        winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
                    else:
                        winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                else:
                    # Fallback non-Windows (plays a simple terminal bell)
                    print('\a', end='', flush=True)
            except Exception as e:
                self._log(f"(Sound failed: {e})")

        # ---------------------------------------------------------
        # EXISTING: Trigger visual notification
        # ---------------------------------------------------------
        if not (self.notify_var.get() and PLYER_AVAILABLE):
            return
        
        title = "Time to Work!" if mode == "WORK" else "Time for Fun!"
        try:
            plyer_notification.notify(title=title, message=message, app_name="Random Timer", timeout=8)
        except Exception as exc:
            self._log(f"(Notification failed: {exc})")

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.event_queue.get_nowait()
                if kind == "switch":
                    mode, message = payload
                    self._set_status(mode == "WORK")
                    self.canvas.itemconfigure(self.txt_substatus, text="Running...")
                    self._log(message)
                    self._send_notification(mode, message)
        except queue.Empty:
            pass
        finally:
            self.after(150, self._poll_queue)

def main():
    app = RandoTimerApp()
    app.mainloop()

if __name__ == "__main__":
    main()