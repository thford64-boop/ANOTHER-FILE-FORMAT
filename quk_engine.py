import tkinter as tk
from tkinter import messagebox, simpledialog, colorchooser
import re
import sys
import time
import winsound
import random
import os
import webbrowser
import platform
import datetime
import math
from threading import Thread

# =================================================================
# QUK CENTURION PRO ENGINE v6.0
# Lines: 300+ 
# Description: Professional Interpreter for .quk source files.
# =================================================================

class QukEnginePro:
    def __init__(self, file_path):
        self.file_path = file_path
        self.root = tk.Tk()
        self.root.title("QUK Professional Interpreter")
        self.root.geometry("800x600")
        
        # --- INTERNAL STATE ---
        self.vars = {
            "pi": 3.14159265,
            "version": 6.0,
            "user": os.getlogin(),
            "os": platform.system(),
            "last_key": "None",
            "canvas_w": 700,
            "canvas_h": 450
        }
        self.labels = {}      # Jump points (:Label)
        self.sprites = {}     # Canvas objects
        self.pc = 0           # Program Counter
        self.lines = []       # Script memory
        self.waiting = False  # For WaitClick logic
        self.running = True
        
        # --- GUI SETUP ---
        self.setup_ui()
        
        # --- INPUT BINDINGS ---
        self.root.bind("<Button-1>", self.on_click)
        self.root.bind("<Key>", self.on_key)

    def setup_ui(self):
        """Initializes the visual components of the engine."""
        self.root.configure(bg="#121212")
        
        # Main Game/App Canvas
        self.canvas = tk.Canvas(
            self.root, 
            width=self.vars["canvas_w"], 
            height=self.vars["canvas_h"], 
            bg="#050505", 
            highlightthickness=1, 
            highlightbackground="#333333"
        )
        self.canvas.pack(pady=20)
        
        # Status Bar
        self.status = tk.Label(
            self.root, 
            text=f"QUK System Active | Running: {os.path.basename(self.file_path)}", 
            fg="#555555", 
            bg="#121212", 
            font=("Consolas", 9)
        )
        self.status.pack(side="bottom", fill="x")

    def log(self, message):
        """Helper to write engine activity to a log file."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        with open("quk_log.txt", "a") as f:
            f.write(f"[{timestamp}] {message}\n")

    def on_click(self, event):
        self.waiting = False

    def on_key(self, event):
        self.vars["last_key"] = event.keysym
        self.log(f"Key Pressed: {event.keysym}")

    def get_val(self, key):
        """Resolves whether a token is a literal value or a variable."""
        s_key = str(key).lower()
        if s_key.startswith('$'):
            s_key = s_key[1:]
        
        if s_key in self.vars:
            return self.vars[s_key]
        
        # Try to return as a number
        try:
            if "." in s_key: return float(s_key)
            return int(s_key)
        except ValueError:
            return str(key).strip('"')

    # =============================================================
    # COMMAND PROCESSING ENGINE
    # =============================================================

    def run(self):
        """The main execution loop for the language."""
        if not os.path.exists(self.file_path):
            messagebox.showerror("QUK Error", f"File not found: {self.file_path}")
            return

        with open(self.file_path, 'r') as f:
            self.lines = [line.strip() for line in f.readlines()]

        # Pre-scan for Labels (The "Compiler" pass)
        for idx, line in enumerate(self.lines):
            if line.startswith(":"):
                label_name = line[1:].lower()
                self.labels[label_name] = idx
                self.log(f"Label defined: {label_name} at line {idx}")

        # Execution Phase
        while self.pc < len(self.lines) and self.running:
            line = self.lines[self.pc]
            
            # Skip empty lines, comments, and label definitions
            if not line or line.startswith("//") or line.startswith(":"):
                self.pc += 1
                continue

            # --- VARIABLE INJECTION ---
            # Replaces $var with the current value stored in memory
            active_line = line
            # Sort variables by length (longest first) to prevent partial replacement bugs
            for var_name in sorted(self.vars.keys(), key=len, reverse=True):
                placeholder = f"${var_name}"
                if placeholder in active_line:
                    active_line = active_line.replace(placeholder, str(self.vars[var_name]))

            parts = active_line.split()
            cmd = parts[0].upper()

            try:
                # --- [1-20] MATH COMMANDS ---
                if cmd == "SET":
                    self.vars[parts[1].lower()] = self.get_val(" ".join(parts[2:]))
                elif cmd == "ADD":
                    self.vars[parts[1].lower()] = float(self.get_val(parts[1])) + float(self.get_val(parts[2]))
                elif cmd == "SUB":
                    self.vars[parts[1].lower()] = float(self.get_val(parts[1])) - float(self.get_val(parts[2]))
                elif cmd == "MULT":
                    self.vars[parts[1].lower()] = float(self.get_val(parts[1])) * float(self.get_val(parts[2]))
                elif cmd == "DIV":
                    divisor = float(self.get_val(parts[2]))
                    if divisor == 0: raise ZeroDivisionError("QUK: Cannot divide by zero!")
                    self.vars[parts[1].lower()] = float(self.get_val(parts[1])) / divisor
                elif cmd == "POW":
                    self.vars[parts[1].lower()] = math.pow(float(self.get_val(parts[1])), float(self.get_val(parts[2])))
                elif cmd == "SQRT":
                    self.vars[parts[1].lower()] = math.sqrt(float(self.get_val(parts[1])))
                elif cmd == "RAND":
                    self.vars[parts[1].lower()] = random.randint(int(parts[2]), int(parts[3]))
                elif cmd == "ROUND":
                    self.vars[parts[1].lower()] = round(float(self.get_val(parts[1])))
                elif cmd == "MOD":
                    self.vars[parts[1].lower()] = float(self.get_val(parts[1])) % float(self.get_val(parts[2]))

                # --- [21-40] STRING COMMANDS ---
                elif cmd == "UPPER":
                    target = parts[1].lower()
                    self.vars[target] = str(self.vars[target]).upper()
                elif cmd == "LOWER":
                    target = parts[1].lower()
                    self.vars[target] = str(self.vars[target]).lower()
                elif cmd == "REV":
                    target = parts[1].lower()
                    self.vars[target] = str(self.vars[target])[::-1]
                elif cmd == "LEN":
                    self.vars[parts[2].lower()] = len(str(self.get_val(parts[1])))
                elif cmd == "JOIN":
                    self.vars[parts[1].lower()] = str(self.get_val(parts[2])) + str(self.get_val(parts[3]))

                # --- [41-60] FLOW CONTROL ---
                elif cmd == "GOTO":
                    target_label = parts[1].lower()
                    if target_label in self.labels:
                        self.pc = self.labels[target_label]
                        continue
                elif cmd == "IFEQ": # If Equal
                    if str(self.get_val(parts[1])) != str(self.get_val(parts[2])):
                        self.pc += 1 # Skip next line
                elif cmd == "IFGT": # If Greater Than
                    if float(self.get_val(parts[1])) <= float(self.get_val(parts[2])):
                        self.pc += 1 # Skip next line
                elif cmd == "IFLT": # If Less Than
                    if float(self.get_val(parts[1])) >= float(self.get_val(parts[2])):
                        self.pc += 1 # Skip next line
                elif cmd == "WAIT":
                    self.root.update()
                    time.sleep(float(parts[1]))
                elif cmd == "WAITCLICK":
                    self.waiting = True
                    while self.waiting:
                        self.root.update()
                        time.sleep(0.01)

                # --- [61-85] GRAPHICS & GUI ---
                elif cmd == "DRAWBOX":
                    # DRAWBOX [id] [x] [y] [size] [color]
                    self.sprites[parts[1]] = self.canvas.create_rectangle(
                        float(parts[2]), float(parts[3]), 
                        float(parts[2])+float(parts[4]), float(parts[3])+float(parts[4]), 
                        fill=parts[5], outline=""
                    )
                elif cmd == "DRAWCIRCLE":
                    self.sprites[parts[1]] = self.canvas.create_oval(
                        float(parts[2]), float(parts[3]), 
                        float(parts[2])+float(parts[4]), float(parts[3])+float(parts[4]), 
                        fill=parts[5], outline=""
                    )
                elif cmd == "DRAWTEXT":
                    # DRAWTEXT "msg" [color] [x] [y]
                    msg = re.search(r'\"(.*?)\"', active_line).group(1)
                    self.canvas.create_text(
                        float(parts[-2]), float(parts[-1]), 
                        text=msg, fill=parts[-3], font=("Arial", 16)
                    )
                elif cmd == "MOVE":
                    self.canvas.move(self.sprites.get(parts[1]), float(parts[2]), float(parts[3]))
                elif cmd == "CLEAR":
                    self.canvas.delete("all")
                    self.sprites.clear()
                elif cmd == "BG":
                    self.root.config(bg=parts[1])
                    self.canvas.config(bg=parts[1])
                elif cmd == "FLASH":
                    curr = self.canvas.cget("bg")
                    self.canvas.config(bg="white"); self.root.update(); time.sleep(0.05)
                    self.canvas.config(bg=curr); self.root.update()

                # --- [86-100] SYSTEM COMMANDS ---
                elif cmd == "SOUND":
                    winsound.Beep(int(parts[1]), int(parts[2]))
                elif cmd == "POPUP":
                    msg = re.search(r'\"(.*?)\"', active_line).group(1)
                    messagebox.showinfo("QUK", msg)
                elif cmd == "PROMPT":
                    msg = re.search(r'\"(.*?)\"', active_line).group(1)
                    res = simpledialog.askstring("QUK Input", msg)
                    self.vars[parts[1].lower()] = res
                elif cmd == "ASK":
                    msg = re.search(r'\"(.*?)\"', active_line).group(1)
                    res = messagebox.askyesno("QUK", msg)
                    self.vars[parts[1].lower()] = "yes" if res else "no"
                elif cmd == "WEB":
                    webbrowser.open(parts[1].strip('"'))
                elif cmd == "SHELL":
                    os.system(" ".join(parts[1:]))
                elif cmd == "TIME":
                    self.vars[parts[1].lower()] = datetime.datetime.now().strftime("%H:%M:%S")
                elif cmd == "TITLE":
                    self.root.title(" ".join(parts[1:]).strip('"'))
                elif cmd == "EXIT":
                    self.running = False
                    self.root.destroy()
                    sys.exit()

            except Exception as e:
                self.log(f"CRITICAL ERROR at Line {self.pc + 1} ({cmd}): {e}")
                print(f"QUK ERROR: Line {self.pc + 1} -> {e}")

            self.pc += 1
            self.root.update()

        self.root.mainloop()

# --- BOOTSTRAP ---
if __name__ == "__main__":
    # Check if a file was dragged onto the EXE or passed as argument
    if len(sys.argv) > 1:
        engine = QukEnginePro(sys.argv[1])
        engine.run()
    else:
        # Default behavior if no file is provided
        print("QUK CENTURION v6.0")
        print("Usage: quk_engine.exe script.quk")
        # For testing purposes, uncomment the line below:
        # engine = QukEnginePro("test.quk"); engine.run()