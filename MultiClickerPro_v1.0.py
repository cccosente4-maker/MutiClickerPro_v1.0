import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pyautogui
import threading
import time
import json
import keyboard
import pygame

# Initialize pygame mixer safely
try:
    pygame.mixer.init()
    SOUND_AVAILABLE = True
except Exception as e:
    print("pygame mixer init failed:", e)
    SOUND_AVAILABLE = False

# Preload sounds (if present)
CLICK_SOUND = None
DOUBLE_CLICK_SOUND = None
if SOUND_AVAILABLE:
    try:
        CLICK_SOUND = pygame.mixer.Sound("click2.wav")
        DOUBLE_CLICK_SOUND = pygame.mixer.Sound("click2.wav")  # reuse or another file
    except Exception as e:
        print("Could not load sound files:", e)
        CLICK_SOUND = None
        DOUBLE_CLICK_SOUND = None


class MultiClickerApp:
    def load_positions(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        with open(file_path, "r") as f:
            data = json.load(f)
        self.clear_positions()
        for pos in data:
            self.tree.insert("", "end", values=pos)
        # update overlays for loaded positions (basic)
        for i, item in enumerate(self.tree.get_children(), start=1):
            vals = self.tree.item(item, "values")
            try:
                _, x, y, _, _ = vals
                self.show_position_number_persistent(int(x), int(y), i)
            except Exception:
                pass
        self.update_double_positions()
        self.log_message("Positions loaded")
    def save_positions(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json")
        if not file_path:
            return
        data = [self.tree.item(item, "values") for item in self.tree.get_children()]
        with open(file_path, "w") as f:
            json.dump(data, f)
        self.log_message("Positions saved")
    def clear_positions(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        # Remove all persistent overlays
        for overlay in self.position_overlays:
            try:
                overlay.destroy()
            except Exception:
                pass
        self.position_overlays.clear()
        self.log_message("Positions cleared")
        self.update_double_positions()
    def __init__(self, root):
        self.root = root
        self.root.title("🎯 Multi Clicker Pro")
        self.root.geometry("520x470")
        self.root.configure(bg="#1e1e2f")
        
        # --- Style (Dark Theme) ---
        style = ttk.Style(self.root)
        style.theme_use("clam")
        
        style.configure("Treeview",
                background="#2b2b40",
                foreground="white",
                rowheight=17,
                fieldbackground="#2b2b40",
                bordercolor="#000000",
                borderwidth=1)
        style.map("Treeview",
              background=[("selected", "#4a90e2")],
              bordercolor=[("selected", "#000000")])
        
        style.configure("TLabel", background="#1e1e2f", foreground="white", font=("Segoe UI", 8))
        style.configure("TButton", padding=2, relief="flat",
                background="#3b3b50", foreground="white", font=("Segoe UI", 8))
        style.map("TButton", background=[("active", "#505070")])
        
        # --- Variables ---
        self.is_running = False
        self.thread = None
        self.delay = tk.DoubleVar(value=0.5)
        self.repeats = tk.IntVar(value=1)
        self.cycles = tk.IntVar(value=1)
        self.cycle_delay = tk.DoubleVar(value=1.0)
        self.click_type = tk.StringVar(value="Left")
        self.click_mode = tk.StringVar(value="Single")
        self.double_mode = tk.StringVar(value="Random")
        self.double_freq = tk.IntVar(value=5)
        self.double_position = tk.StringVar(value="All Positions")
        self.position_overlays = []
        
        # --- Main Layout (2 columns: left positions, right status/settings) ---
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill="both", expand=True, padx=4, pady=4)
        
        # Left: Position List
        self.left_frame = ttk.LabelFrame(self.main_frame, text="Click Positions")
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        
        self.tree = ttk.Treeview(self.left_frame, columns=("Position", "X", "Y", "Click Type", "Mode"),
                     show="headings", height=9, style="Treeview")
        self.tree.heading("Position", text="Pos")
        self.tree.heading("X", text="X")
        self.tree.heading("Y", text="Y")
        self.tree.heading("Click Type", text="Type")
        self.tree.heading("Mode", text="Mode")
        self.tree.column("Position", width=38, anchor="center")
        self.tree.column("X", width=38, anchor="center")
        self.tree.column("Y", width=38, anchor="center")
        self.tree.column("Click Type", width=54, anchor="center")
        self.tree.column("Mode", width=54, anchor="center")
        self.tree.grid(row=0, column=0, columnspan=4, pady=2, sticky="nsew")
        
        # Use two labels: one for 'Msg:' (white), one for message (yellow)
        self.msg_label = tk.Label(self.left_frame, text="Msg:", anchor="w",
            bg="#2b2b40", fg="white",
            font=("Segoe UI", 8, "bold"), height=1, padx=1, pady=2)
        self.msg_label.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        self.message_text_label = tk.Label(self.left_frame, text="Ready", anchor="w",
            bg="#2b2b40", fg="yellow",
            font=("Segoe UI", 8, "bold"), height=1, padx=1, pady=2)
        self.message_text_label.grid(row=1, column=1, columnspan=3, sticky="ew", pady=(2, 0))

        ttk.Button(self.left_frame, text="Add", command=self.add_position).grid(row=2, column=0, pady=2, sticky="ew")
        ttk.Button(self.left_frame, text="Clear", command=self.clear_positions).grid(row=2, column=1, pady=2, sticky="ew")
        ttk.Button(self.left_frame, text="Save", command=self.save_positions).grid(row=2, column=2, pady=2, sticky="ew")
        ttk.Button(self.left_frame, text="Load", command=self.load_positions).grid(row=2, column=3, pady=2, sticky="ew")

        self.left_frame.columnconfigure((0, 1, 2, 3), weight=1)
        self.left_frame.rowconfigure(0, weight=1)

        # Right: Status + Settings
        self.right_frame = ttk.Frame(self.main_frame)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)

        # Status Panel
        status_frame = ttk.LabelFrame(self.right_frame, text="Status")
        status_frame.grid(row=0, column=0, sticky="ew", pady=2)

        self.timer_label = tk.Label(status_frame, text="Timer: 0s", anchor="w", bg="#1e1e2f", fg="#00BFFF", font=("Segoe UI", 8, "bold"))
        self.timer_label.grid(row=0, column=0, sticky="w", padx=2, pady=1)

        self.clicks_left_label = tk.Label(status_frame, text="Clicks Left: 0", anchor="w", bg="#1e1e2f", fg="#FF6347", font=("Segoe UI", 8, "bold"))
        self.clicks_left_label.grid(row=1, column=0, sticky="w", padx=2, pady=1)

        self.cycles_left_label = tk.Label(status_frame, text="Cycles Left: 0", anchor="w", bg="#1e1e2f", fg="#32CD32", font=("Segoe UI", 8, "bold"))
        self.cycles_left_label.grid(row=2, column=0, sticky="w", padx=2, pady=1)

        # Settings Panel
        settings_frame = ttk.LabelFrame(self.right_frame, text="Settings")
        settings_frame.grid(row=1, column=0, sticky="ew", pady=2)

        ttk.Label(settings_frame, text="Delay (s):").grid(row=0, column=0, sticky="w", padx=2, pady=1)
        ttk.Entry(settings_frame, textvariable=self.delay, width=5).grid(row=0, column=1, padx=2, pady=1)

        ttk.Label(settings_frame, text="Repeats:").grid(row=1, column=0, sticky="w", padx=2, pady=1)
        ttk.Entry(settings_frame, textvariable=self.repeats, width=5).grid(row=1, column=1, padx=2, pady=1)

        ttk.Label(settings_frame, text="Cycles:").grid(row=2, column=0, sticky="w", padx=2, pady=1)
        ttk.Entry(settings_frame, textvariable=self.cycles, width=5).grid(row=2, column=1, padx=2, pady=1)

        ttk.Label(settings_frame, text="Cycle Delay (s):").grid(row=3, column=0, sticky="w", padx=2, pady=1)
        ttk.Entry(settings_frame, textvariable=self.cycle_delay, width=5).grid(row=3, column=1, padx=2, pady=1)

        ttk.Label(settings_frame, text="Click Type:").grid(row=4, column=0, sticky="w", padx=2, pady=1)
        ttk.Combobox(settings_frame, textvariable=self.click_type,
                     values=["Left", "Right", "Middle"], state="readonly", width=7).grid(row=4, column=1, padx=2, pady=1)

        ttk.Label(settings_frame, text="Click Mode:").grid(row=5, column=0, sticky="w", padx=2, pady=1)
        ttk.Combobox(settings_frame, textvariable=self.click_mode,
                     values=["Single", "Double"], state="readonly", width=7).grid(row=5, column=1, padx=2, pady=1)

        # Double Click Options
        double_frame = ttk.LabelFrame(settings_frame, text="Double Click Options")
        double_frame.grid(row=6, column=0, columnspan=2, pady=2, sticky="ew")

        ttk.Label(double_frame, text="Mode:").grid(row=0, column=0, sticky="w", padx=2, pady=1)
        ttk.Combobox(double_frame, textvariable=self.double_mode,
                     values=["Random", "Customize"], state="readonly", width=8).grid(row=0, column=1, padx=2, pady=1)

        ttk.Label(double_frame, text="Every X:").grid(row=1, column=0, sticky="w", padx=2, pady=1)
        ttk.Spinbox(double_frame, from_=1, to=100, textvariable=self.double_freq, width=4).grid(row=1, column=1, padx=2, pady=1)

        ttk.Label(double_frame, text="Target:").grid(row=2, column=0, sticky="w", padx=2, pady=1)
        self.double_dropdown = ttk.Combobox(double_frame, textvariable=self.double_position, state="readonly", width=8)
        self.double_dropdown.grid(row=2, column=1, padx=2, pady=1)
        ttk.Button(double_frame, text="Refresh", command=self.update_double_positions).grid(row=3, column=0, columnspan=2, pady=2)

        # Start/Stop
        control_frame = ttk.Frame(self.right_frame)
        control_frame.grid(row=2, column=0, pady=2, sticky="ew")
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)

        self.start_btn = tk.Button(control_frame, text="▶ Start", bg="#2ECC71", fg="white",
                                   font=("Segoe UI", 8, "bold"), command=self.start_clicking, height=1)
        self.start_btn.grid(row=0, column=0, padx=(0,2), pady=2, sticky="ew")

        self.stop_btn = tk.Button(control_frame, text="■ Stop", bg="#7F8C8D", fg="white",
                                  font=("Segoe UI", 8, "bold"), command=self.stop_clicking, height=1)
        self.stop_btn.grid(row=0, column=1, padx=(2,0), pady=2, sticky="ew")

        # Shortcuts
        shortcut_label = ttk.Label(self.right_frame, text="Shortcuts: F6 = Start | F7 = Stop", foreground="lightgray", font=("Segoe UI", 7))
        shortcut_label.grid(row=3, column=0, pady=2)

        # Key bindings
        keyboard.add_hotkey("F6", self.start_clicking)
        keyboard.add_hotkey("F7", self.stop_clicking)

        # Configure resizing
        self.main_frame.columnconfigure(0, weight=2)
        self.main_frame.columnconfigure(1, weight=1)

        # After self.tree.grid(...)
        self.tree_modes = {}
        def add_mode_dropdown(row_id):
            bbox = self.tree.bbox(row_id, column="Mode")
            if bbox:
                x, y, width, height = bbox
                mode_var = tk.StringVar(value=self.tree.set(row_id, "Mode"))
                combo = ttk.Combobox(self.tree, textvariable=mode_var, values=["Single", "Double"], state="readonly", width=7, justify="center")
                combo.place(x=x, y=y, width=width, height=height)
                combo.configure(style="Mode.TCombobox")
                combo.option_add('*TCombobox*Listbox.Justify', 'center')
                combo.option_add('*TCombobox.Justify', 'center')
                def on_select(event):
                    self.tree.set(row_id, "Mode", mode_var.get())
                    combo.configure(justify="center")
                combo.bind("<<ComboboxSelected>>", on_select)
                self.tree_modes[row_id] = combo
        style = ttk.Style(self.root)
        style.configure("Mode.TCombobox",
                        bordercolor="#000000",
                        borderwidth=4,
                        relief="solid",
                        foreground="black",
                        background="#2b2b40",
                        fieldbackground="#2b2b40",
                        justify="center")
        def refresh_mode_dropdowns():
            for combo in self.tree_modes.values():
                combo.destroy()
            self.tree_modes.clear()
            for row_id in self.tree.get_children():
                add_mode_dropdown(row_id)
        self.tree.bind("<Map>", lambda e: refresh_mode_dropdowns())
        self.tree.bind("<Configure>", lambda e: refresh_mode_dropdowns())
        self.tree.bind("<<TreeviewSelect>>", lambda e: refresh_mode_dropdowns())
        self.tree.bind("<ButtonRelease-1>", lambda e: refresh_mode_dropdowns())


        # Tree interactions
        self.tree.bind("<Double-1>", self.on_tree_double_click)  # bind double-click to edit mode

        # Settings button (top right corner)
        self.settings_btn = tk.Button(self.root, text="⚙", font=("Segoe UI", 8), bg=None, fg="white", relief="flat", borderwidth=0, highlightthickness=0, command=self.open_settings, height=1, width=2)
        self.settings_btn.place(relx=0.98, rely=0.02, anchor="ne")

        # Donation Button (above Start/Stop)
        def open_donation():
            import webbrowser
            webbrowser.open_new("paypal.me/clinton12")
        donation_btn = tk.Button(self.right_frame, text="☕ Donate", bg="#FFD700", fg="black", font=("Segoe UI", 8, "bold"), command=open_donation, height=1)
        donation_btn.grid(row=2, column=0, pady=(0, 2), sticky="ew")

        # Move control_frame down by one row (row=3)
        control_frame.grid_configure(row=3)

        # Move shortcut label down by one row (row=4)
        shortcut_label.grid_configure(row=4)

    def open_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings & Help")
        settings_win.geometry("420x340")
        settings_win.configure(bg="#1e1e2f")
        settings_win.resizable(False, False)
        # Tutorial/How to use
        tutorial = (
            "How to Use MultiClickerPro:\n\n"
            "1. Add positions: Click 'Add' and hover your mouse at the desired location.\n"
            "2. Each position is numbered and shown on the screen.\n"
            "3. Set click type and mode (Single/Double) for each position.\n"
            "4. Adjust delay, repeats, cycles, and cycle delay in Settings.\n"
            "   - Delay: Time (seconds) between each click at a position.\n"
            "   - Repeats: Number of times to click at each position before moving to the next.\n"
            "   - Cycles: Number of times to repeat the entire sequence of clicking all positions.\n"
            "   - Cycle Delay: Time (seconds) to wait between each cycle.\n"
            "5. Use F6 to start and F7 to stop the clicker.\n"
            "6. Double click a position in the list to change its mode.\n"
            "7. Use the 'Save' and 'Load' buttons to store or restore positions.\n"
            "8. The position overlays show saved positions.\n"
            "9. The click sound and visual effects indicate each click.\n"
            "10. Use the 'Clear' button to remove all positions and overlays.\n"
        )
        tutorial_frame = tk.Frame(settings_win, bg="#1e1e2f")
        tutorial_frame.pack(padx=18, pady=18, anchor="nw", fill="both", expand=True)
        tutorial_label = tk.Label(tutorial_frame, text=tutorial, justify="left", bg="#1e1e2f", fg="white", font=("Segoe UI", 9), wraplength=380)
        tutorial_label.pack(anchor="nw")
        # Exit button
        exit_btn = tk.Button(settings_win, text="Exit App", font=("Segoe UI", 10, "bold"), bg="#E74C3C", fg="white", relief="flat", command=self.root.destroy)
        exit_btn.pack(side="bottom", pady=14)

    # --- Helper Functions ---
    def log_message(self, msg):
        self.message_text_label.config(text=msg, fg="yellow")

    def add_position(self):
        # 3-second guided hover + capture
        self.log_message("Hover mouse in 3...")
        self.root.after(1000, lambda: self.log_message("Hover mouse in 2..."))
        self.root.after(2000, lambda: self.log_message("Hover mouse in 1..."))
        self.root.after(3000, self.capture_position)

    def show_water_effect(self, item_id):
        # Simple quick highlight animation for tree item
        colors = ["#B2EBF2", "#4DD0E1", "#00BCD4", "#0097A7", "#2b2b40"]
        def animate(idx=0):
            if idx < len(colors):
                self.tree.tag_configure("water", background=colors[idx])
                self.tree.item(item_id, tags=("centered", "water"))
                self.root.after(60, lambda: animate(idx+1))
            else:
                self.tree.tag_configure("water", background="")
        animate()

    def capture_position(self):
        x, y = pyautogui.position()
        pos_num = len(self.tree.get_children()) + 1
        click_type = self.click_type.get()
        self.tree.insert("", "end", values=(pos_num, x, y, click_type, "Single"), tags=("centered",))
        self.tree.tag_configure("centered", anchor="center")
        # Show overlay number
        self.show_position_number_persistent(x, y, pos_num)
        # Keep double options in sync
        self.update_double_positions()

    def show_position_number_persistent(self, x, y, num):
        # Overlay with only a yellow circle and number, no white square
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes('-topmost', True)
        try:
            overlay.attributes('-alpha', 0.85)
        except Exception:
            pass
        size = 28
        # Canvas with same bg as app, but only draw a filled yellow circle
        canvas = tk.Canvas(overlay, width=size, height=size, bg="#2b2b40", highlightthickness=0, borderwidth=0)
        canvas.pack()
        # Draw only a filled yellow circle with a number
        canvas.create_oval(2, 2, size-2, size-2, fill='#FFD700', outline='#B8860B', width=2)
        canvas.create_text(size//2, size//2, text=str(num), font=('Segoe UI', 13, 'bold'), fill='#222')
        overlay.geometry(f'{size}x{size}+{int(x-size//2)}+{int(y-size//2)}')
        overlay.update()
        self.position_overlays.append(overlay)

    def update_double_positions(self):
        positions = ["All Positions"]
        for i, _ in enumerate(self.tree.get_children(), start=1):
            positions.append(f"Position {i}")
        self.double_dropdown["values"] = positions
        if self.double_position.get() not in positions:
            self.double_position.set("All Positions")

    def start_clicking(self):
        if self.is_running:
            return
        if not self.tree.get_children():
            messagebox.showwarning("No positions", "Please add at least one position.")
            return

        self.is_running = True
        self.start_btn.config(bg="#7F8C8D")
        self.stop_btn.config(bg="#E74C3C")

        self.thread = threading.Thread(target=self.run_clicker, daemon=True)
        self.thread.start()
        self.log_message("Running")

    def stop_clicking(self):
        self.is_running = False
        self.start_btn.config(bg="#2ECC71")
        self.stop_btn.config(bg="#7F8C8D")
        self.log_message("Stopped")

    def play_click_sound(self, double=False):
        if not SOUND_AVAILABLE:
            return
        try:
            if double and DOUBLE_CLICK_SOUND:
                DOUBLE_CLICK_SOUND.play()
            elif CLICK_SOUND:
                CLICK_SOUND.play()
        except Exception as e:
            print("Sound play error:", e)

    def run_clicker(self):
        cycles = max(1, int(self.cycles.get()))
        delay = float(self.delay.get())
        repeats = max(1, int(self.repeats.get()))
        cycle_delay = float(self.cycle_delay.get())

        total_clicks = len(self.tree.get_children()) * repeats * cycles
        clicks_done = 0
        start_time = time.time()


        for cycle in range(1, cycles + 1):
            if not self.is_running:
                break

            # Hide overlays before clicking
            for overlay in self.position_overlays:
                try:
                    overlay.withdraw()
                except Exception:
                    pass

            # Double-click rule (applies before normal sequence)
            freq = max(1, int(self.double_freq.get()))
            if freq > 0 and cycle % freq == 0:
                mode = self.double_mode.get()
                target = self.double_position.get()

                if mode == "Random":
                    for item in self.tree.get_children():
                        _, x, y, _, pos_mode = self.tree.item(item, "values")
                        x, y = int(x), int(y)
                        btn = self.click_type.get().lower()
                        pyautogui.moveTo(x, y)
                        if pos_mode == "Double":
                            time.sleep(0.05)
                            pyautogui.doubleClick(button=btn, interval=0.1)
                            clicks_done += 2
                        else:
                            time.sleep(0.05)
                            pyautogui.click(button=btn)
                            clicks_done += 1
                        self.clicks_left_label.config(text=f"Clicks Left: {max(total_clicks - clicks_done, 0)}")
                elif mode == "Customize":
                    if target == "All Positions":
                        for item in self.tree.get_children():
                            _, x, y, _, pos_mode = self.tree.item(item, "values")
                            x, y = int(x), int(y)
                            btn = self.click_type.get().lower()
                            pyautogui.moveTo(x, y)
                            if pos_mode == "Double":
                                time.sleep(0.05)
                                pyautogui.doubleClick(button=btn, interval=0.1)
                                clicks_done += 2
                            else:
                                time.sleep(0.05)
                                pyautogui.click(button=btn)
                                clicks_done += 1
                            self.clicks_left_label.config(text=f"Clicks Left: {max(total_clicks - clicks_done, 0)}")
                    else:
                        try:
                            idx = int(target.split()[1]) - 1
                            items = self.tree.get_children()
                            if 0 <= idx < len(items):
                                item = items[idx]
                                _, x, y, _, pos_mode = self.tree.item(item, "values")
                                x, y = int(x), int(y)
                                btn = self.click_type.get().lower()
                                pyautogui.moveTo(x, y)
                                if pos_mode == "Double":
                                    time.sleep(0.05)
                                    pyautogui.doubleClick(button=btn, interval=0.1)
                                    clicks_done += 2
                                else:
                                    time.sleep(0.05)
                                    pyautogui.click(button=btn)
                                    clicks_done += 1
                                self.clicks_left_label.config(text=f"Clicks Left: {max(total_clicks - clicks_done, 0)}")
                        except Exception:
                            pass

            # Normal clicking sequence
            for item in self.tree.get_children():
                if not self.is_running:
                    break
                _, x, y, _, pos_mode = self.tree.item(item, "values")
                x, y = int(x), int(y)
                for _ in range(repeats):
                    if not self.is_running:
                        break
                    btn = self.click_type.get().lower()
                    pyautogui.moveTo(x, y)
                    if pos_mode == "Double":
                        time.sleep(0.05)
                        pyautogui.doubleClick(button=btn, interval=0.1)
                        clicks_done += 2
                    else:
                        time.sleep(0.05)
                        pyautogui.click(button=btn)
                        clicks_done += 1
                    self.clicks_left_label.config(text=f"Clicks Left: {max(total_clicks - clicks_done, 0)}")
                    elapsed = time.time() - start_time
                    self.timer_label.config(text=f"Timer: {int(elapsed)}s")
                    self.root.update_idletasks()
                    # Visual touch reaction
                    self.tree.selection_set(item)
                    self.tree.see(item)
                    self.tree.item(item, tags=("centered", "touched"))
                    self.tree.tag_configure("touched", background="#FFD700")
                    self.root.after(300, lambda i=item: self.tree.tag_configure("touched", background=""))
                    # Water effect
                    self.show_water_effect(item)
                    # Show click circle at screen position
                    try:
                        _, x, y, _, pos_mode = self.tree.item(item, "values")
                        x, y = int(x), int(y)
                        if pos_mode == 'Double':
                            self.show_click_circle(x, y)
                            threading.Timer(0.13, lambda: self.show_click_circle(x, y)).start()
                        else:
                            self.show_click_circle(x, y)
                    except Exception as e:
                        print(f"Circle effect error: {e}")
                    # Play custom click sound using pygame
                    try:
                        if pos_mode == 'Double':
                            pygame.mixer.music.load('click2.wav')
                            pygame.mixer.music.play()
                            threading.Timer(0.2, lambda: (pygame.mixer.music.load('click2.wav'), pygame.mixer.music.play())).start()
                        else:
                            pygame.mixer.music.load('click2.wav')
                            pygame.mixer.music.play()
                    except Exception as e:
                        print(f"Sound error: {e}")
                    time.sleep(delay)

            # Restore overlays after clicking
            for overlay in self.position_overlays:
                try:
                    overlay.deiconify()
                except Exception:
                    pass


            # Update cycles left & cycle delay countdown
            self.cycles_left_label.config(text=f"Cycles Left: {cycles - cycle}")
            self.root.update_idletasks()
            for sec in range(int(cycle_delay), 0, -1):
                if not self.is_running:
                    break
                self.timer_label.config(text=f"Cycle Delay: {sec}s left")
                self.root.update_idletasks()
                time.sleep(1)

        self.is_running = False
        self.start_btn.config(bg="#2ECC71")
        self.stop_btn.config(bg="#7F8C8D")
        self.log_message("Finished")

    def edit_position_mode(self, item_id):
        top = tk.Toplevel(self.root)
        top.title("Select Click Mode")
        top.geometry("220x120")
        tk.Label(top, text="Select Click Mode:", font=("Segoe UI", 11)).pack(pady=10)
        mode_var = tk.StringVar(value=self.tree.set(item_id, "Mode"))
        mode_menu = ttk.Combobox(top, textvariable=mode_var, values=["Single", "Double"], state="readonly")
        mode_menu.pack(pady=5)
        def save_mode():
            self.tree.set(item_id, "Mode", mode_var.get())
            top.destroy()
        ttk.Button(top, text="Save", command=save_mode).pack(pady=5)

    def on_tree_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.edit_position_mode(item)

    def show_click_circle(self, x, y, duration=350):
        # run animation on a separate thread so it doesn't block the clicker thread
        def animate_circle():
            overlay = tk.Toplevel(self.root)
            overlay.overrideredirect(True)
            overlay.attributes('-topmost', True)
            try:
                overlay.attributes('-alpha', 0.7)
            except Exception:
                pass
            size = 48
            overlay.geometry(f'{size}x{size}+{int(x-size//2)}+{int(y-size//2)}')
            canvas = tk.Canvas(overlay, width=size, height=size, bg="#1e1e2f", highlightthickness=0)
            canvas.pack()
            circle = canvas.create_oval(6, 6, size-6, size-6, outline='#00BCD4', width=4)
            steps = 10
            step_sleep = max(0.01, (duration / 1000.0) / steps)
            for i in range(steps):
                canvas.coords(circle, 6 + i*2, 6 + i*2, size-6 - i*2, size-6 - i*2)
                try:
                    overlay.attributes('-alpha', 0.7 - i*(0.7/steps))
                except Exception:
                    pass
                canvas.update()
                overlay.update()
                time.sleep(step_sleep)
            try:
                overlay.destroy()
            except Exception:
                pass
        threading.Thread(target=animate_circle, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = MultiClickerApp(root)
    root.mainloop()

