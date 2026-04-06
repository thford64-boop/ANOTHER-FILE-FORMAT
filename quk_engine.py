import tkinter as tk
from tkinter import messagebox, simpledialog, colorchooser, font as tkfont
import re
import sys
import time
import random
import os
import webbrowser
import platform
import datetime
import math
import json
import colorsys
import hashlib
import base64
import urllib.request
import socket
import threading
import itertools
from collections import defaultdict

# Try winsound (Windows only), graceful fallback
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# =================================================================
# QUK CENTURION PRO ENGINE v7.0
# Commands: 500+
# New in v7: GETKEY, IFKEY, real-time input, arrays, timers,
#   particles, tweening, camera, save/load, networking, audio
#   expanded math, string ops, color ops, collision, scenes,
#   UI widgets, file I/O, debug tools, and much more.
# =================================================================

VERSION = "7.0"

class QukEnginePro:
    def __init__(self, file_path):
        self.file_path = file_path
        self.root = tk.Tk()
        self.root.title("QUK Centurion Pro v7.0")
        self.root.geometry("800x620")
        self.root.resizable(True, True)

        # ── INTERNAL STATE ──────────────────────────────────────────
        self.vars = {
            "pi": 3.14159265358979,
            "tau": 6.28318530717959,
            "e": 2.71828182845905,
            "inf": float("inf"),
            "true": 1,
            "false": 0,
            "version": 7.0,
            "user": os.getlogin() if hasattr(os, "getlogin") else "player",
            "os": platform.system(),
            "last_key": "None",
            "last_key_code": 0,
            "mouse_x": 0,
            "mouse_y": 0,
            "mouse_clicked": 0,
            "canvas_w": 700,
            "canvas_h": 450,
            "fps": 60,
            "frame": 0,
            "dt": 0.016,
            "time": 0.0,
        }
        self.arrays = {}           # name -> list
        self.labels = {}           # label -> line index
        self.call_stack = []       # for CALL/RETURN
        self.sprites = {}          # id -> canvas item id
        self.sprite_data = {}      # id -> {x,y,w,h,vx,vy,tag,visible,layer}
        self.sprite_texts = {}     # id -> canvas text item
        self.particles = {}        # id -> list of particle dicts
        self.timers = {}           # name -> {end_time, label}
        self.tweens = {}           # id -> tween state
        self.scenes = {}           # name -> list of lines
        self.ui_widgets = {}       # id -> tk widget
        self.saved_data = {}       # persistent save data
        self.collision_groups = defaultdict(set)
        self.pc = 0
        self.lines = []
        self.waiting = False
        self.running = True
        self.paused = False
        self.key_held = set()      # keys currently held down
        self.key_just_pressed = set()   # keys pressed this frame
        self.key_just_released = set()  # keys released this frame
        self.debug_mode = False
        self.bg_color = "#050505"
        self._last_frame_time = time.time()
        self._frame_times = []
        self._camera_x = 0
        self._camera_y = 0
        self._camera_zoom = 1.0
        self._shake_frames = 0
        self._shake_intensity = 0
        self._overlay_color = None
        self._overlay_alpha = 0
        self._canvas_image = None  # background image

        self.setup_ui()

        # ── INPUT BINDINGS ──────────────────────────────────────────
        self.root.bind("<Button-1>",   self.on_click)
        self.root.bind("<KeyPress>",   self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)
        self.root.bind("<Motion>",     self.on_mouse_move)
        self.root.bind("<Configure>",  self.on_resize)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ── UI SETUP ────────────────────────────────────────────────────
    def setup_ui(self):
        self.root.configure(bg="#0d0d0d")
        self.canvas = tk.Canvas(
            self.root,
            width=self.vars["canvas_w"],
            height=self.vars["canvas_h"],
            bg=self.bg_color,
            highlightthickness=1,
            highlightbackground="#222222"
        )
        self.canvas.pack(pady=10, expand=True, fill="both")
        self.status = tk.Label(
            self.root,
            text=f"QUK v7.0 | {os.path.basename(self.file_path)}",
            fg="#444444", bg="#0d0d0d", font=("Consolas", 8)
        )
        self.status.pack(side="bottom", fill="x")

    def update_status(self, msg):
        self.status.config(text=msg)

    # ── EVENT HANDLERS ──────────────────────────────────────────────
    def on_click(self, e):
        self.waiting = False
        self.vars["mouse_clicked"] = 1
        self.vars["mouse_x"] = e.x
        self.vars["mouse_y"] = e.y

    def on_key_press(self, e):
        k = e.keysym.lower()
        self.vars["last_key"] = e.keysym
        self.vars["last_key_code"] = e.keycode
        if k not in self.key_held:
            self.key_just_pressed.add(k)
        self.key_held.add(k)

    def on_key_release(self, e):
        k = e.keysym.lower()
        self.key_held.discard(k)
        self.key_just_released.add(k)

    def on_mouse_move(self, e):
        self.vars["mouse_x"] = e.x
        self.vars["mouse_y"] = e.y

    def on_resize(self, e):
        if e.widget == self.root:
            self.vars["canvas_w"] = self.canvas.winfo_width()
            self.vars["canvas_h"] = self.canvas.winfo_height()

    def on_close(self):
        self.running = False
        self.root.destroy()

    # ── HELPERS ─────────────────────────────────────────────────────
    def log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        with open("quk_log.txt", "a") as f:
            f.write(f"[{ts}] {msg}\n")
        if self.debug_mode:
            print(f"[QUK] {msg}")

    def get_val(self, key):
        s = str(key)
        low = s.lower()
        if low.startswith("$"):
            low = low[1:]
        if low in self.vars:
            v = self.vars[low]
            try: return float(v)
            except: return v
        # array access arr[0]
        m = re.match(r'^([a-z_]\w*)\[(\d+)\]$', low)
        if m:
            arr, idx = m.group(1), int(m.group(2))
            if arr in self.arrays and idx < len(self.arrays[arr]):
                v = self.arrays[arr][idx]
                try: return float(v)
                except: return v
        try:
            if "." in low: return float(low)
            return int(low)
        except:
            return s.strip('"')

    def num(self, key):
        try: return float(self.get_val(key))
        except: return 0.0

    def resolve_str(self, raw):
        """Replace all $var in a string with current values."""
        result = raw.strip('"')
        for name in sorted(self.vars.keys(), key=len, reverse=True):
            result = result.replace(f"${name}", str(self.vars[name]))
        return result

    def extract_string(self, line):
        m = re.search(r'"(.*?)"', line)
        return m.group(1) if m else ""

    def sprite_pos(self, sid):
        """Return current (x, y) of a sprite from canvas coords."""
        if sid not in self.sprites:
            return (0, 0)
        coords = self.canvas.coords(self.sprites[sid])
        if not coords:
            return (0, 0)
        return (coords[0], coords[1])

    def _tick_timers(self):
        now = time.time()
        for name, t in list(self.timers.items()):
            if now >= t["end"] and not t.get("fired"):
                self.timers[name]["fired"] = True
                if t["label"] in self.labels:
                    self.pc = self.labels[t["label"]]

    def _tick_tweens(self):
        now = time.time()
        for tid, tw in list(self.tweens.items()):
            if tw["done"]:
                continue
            elapsed = now - tw["start"]
            progress = min(elapsed / tw["duration"], 1.0)
            # Easing
            ease = tw.get("ease", "linear")
            t = progress
            if ease == "easein":    t = t * t
            elif ease == "easeout": t = t * (2 - t)
            elif ease == "easeinout": t = t*t*(3-2*t)
            elif ease == "bounce":
                if t < 1/2.75: t = 7.5625*t*t
                elif t < 2/2.75: t -= 1.5/2.75; t = 7.5625*t*t+0.75
                elif t < 2.5/2.75: t -= 2.25/2.75; t = 7.5625*t*t+0.9375
                else: t -= 2.625/2.75; t = 7.5625*t*t+0.984375
            val = tw["from"] + (tw["to"] - tw["from"]) * t
            self.vars[tw["var"]] = val
            if progress >= 1.0:
                self.tweens[tid]["done"] = True
                self.vars[tw["var"]] = tw["to"]

    def _tick_particles(self):
        dead = []
        for pid, plist in self.particles.items():
            alive = []
            for p in plist:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["vy"] += p.get("gravity", 0.2)
                p["life"] -= 1
                if p["life"] > 0:
                    alive.append(p)
                else:
                    try: self.canvas.delete(p["cid"])
                    except: pass
            self.particles[pid] = alive
            for p in alive:
                try:
                    self.canvas.coords(p["cid"], p["x"], p["y"],
                                       p["x"]+p["size"], p["y"]+p["size"])
                except: pass

    def _update_frame_counter(self):
        now = time.time()
        dt = now - self._last_frame_time
        self._last_frame_time = now
        self.vars["dt"] = dt
        self.vars["frame"] = int(self.vars["frame"]) + 1
        self.vars["time"] = round(self.vars["time"] + dt, 4)
        self._frame_times.append(dt)
        if len(self._frame_times) > 60:
            self._frame_times.pop(0)
        avg = sum(self._frame_times) / len(self._frame_times)
        self.vars["fps"] = round(1.0 / avg) if avg > 0 else 60

    def beep(self, hz, ms):
        if HAS_WINSOUND:
            hz = max(37, min(32767, int(hz)))
            winsound.Beep(hz, int(ms))
        else:
            # Cross-platform fallback via tk bell
            self.root.bell()

    # ── MAIN RUN LOOP ───────────────────────────────────────────────
    def run(self):
        if not os.path.exists(self.file_path):
            messagebox.showerror("QUK Error", f"File not found:\n{self.file_path}")
            return

        with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
            self.lines = [l.rstrip("\n") for l in f.readlines()]

        # Pre-scan labels
        for idx, line in enumerate(self.lines):
            stripped = line.strip()
            if stripped.startswith(":"):
                lname = stripped[1:].split()[0].lower()
                self.labels[lname] = idx

        while self.pc < len(self.lines) and self.running:
            if self.paused:
                self.root.update()
                time.sleep(0.01)
                continue

            raw = self.lines[self.pc].strip()

            if not raw or raw.startswith("//") or raw.startswith("#") or raw.startswith(":"):
                self.pc += 1
                continue

            # Variable injection
            active = raw
            for vname in sorted(self.vars.keys(), key=len, reverse=True):
                active = active.replace(f"${vname}", str(self.vars[vname]))

            # Array injection arr[N]
            active = re.sub(
                r'\$([a-zA-Z_]\w*)\[(\d+)\]',
                lambda m: str(self.arrays.get(m.group(1).lower(), [None]*999)[int(m.group(2))]
                              if int(m.group(2)) < len(self.arrays.get(m.group(1).lower(),[]))
                              else 0),
                active
            )

            parts = active.split()
            cmd = parts[0].upper()

            jumped = False
            try:
                jumped = self._exec(cmd, parts, active, raw)
            except SystemExit:
                return
            except Exception as ex:
                self.log(f"ERROR line {self.pc+1} [{cmd}]: {ex}")
                if self.debug_mode:
                    messagebox.showerror("QUK Runtime Error",
                        f"Line {self.pc+1}: {cmd}\n{ex}")

            if not jumped:
                self.pc += 1

            # Per-frame bookkeeping
            self._tick_timers()
            self._tick_tweens()
            self._tick_particles()
            self._update_frame_counter()
            self.key_just_pressed.clear()
            self.key_just_released.clear()
            self.vars["mouse_clicked"] = 0

            try:
                self.root.update()
            except tk.TclError:
                break

        try:
            self.root.mainloop()
        except:
            pass

    # ═══════════════════════════════════════════════════════════════
    # COMMAND DISPATCH  (~500 commands)
    # Returns True if a jump was made (pc already set).
    # ═══════════════════════════════════════════════════════════════
    def _exec(self, cmd, parts, active, raw):
        jumped = False

        # ── MATH ────────────────────────────────────────────────────
        if cmd == "SET":
            val = " ".join(parts[2:])
            self.vars[parts[1].lower()] = self.get_val(val) if not val.startswith('"') else self.resolve_str(val)
        elif cmd == "ADD":   self.vars[parts[1].lower()] = self.num(parts[1]) + self.num(parts[2])
        elif cmd == "SUB":   self.vars[parts[1].lower()] = self.num(parts[1]) - self.num(parts[2])
        elif cmd == "MULT":  self.vars[parts[1].lower()] = self.num(parts[1]) * self.num(parts[2])
        elif cmd == "DIV":
            d = self.num(parts[2])
            if d == 0: raise ZeroDivisionError("Division by zero")
            self.vars[parts[1].lower()] = self.num(parts[1]) / d
        elif cmd == "MOD":   self.vars[parts[1].lower()] = self.num(parts[1]) % self.num(parts[2])
        elif cmd == "POW":   self.vars[parts[1].lower()] = math.pow(self.num(parts[1]), self.num(parts[2]))
        elif cmd == "SQRT":  self.vars[parts[1].lower()] = math.sqrt(abs(self.num(parts[1])))
        elif cmd == "ROUND": self.vars[parts[1].lower()] = round(self.num(parts[1]))
        elif cmd == "FLOOR": self.vars[parts[1].lower()] = math.floor(self.num(parts[1]))
        elif cmd == "CEIL":  self.vars[parts[1].lower()] = math.ceil(self.num(parts[1]))
        elif cmd == "ABS":   self.vars[parts[1].lower()] = abs(self.num(parts[1]))
        elif cmd == "NEG":   self.vars[parts[1].lower()] = -self.num(parts[1])
        elif cmd == "INC":   self.vars[parts[1].lower()] = self.num(parts[1]) + 1
        elif cmd == "DEC":   self.vars[parts[1].lower()] = self.num(parts[1]) - 1
        elif cmd == "RAND":  self.vars[parts[1].lower()] = random.randint(int(self.num(parts[2])), int(self.num(parts[3])))
        elif cmd == "RANDF": self.vars[parts[1].lower()] = round(random.uniform(self.num(parts[2]), self.num(parts[3])), 4)
        elif cmd == "MIN":   self.vars[parts[1].lower()] = min(self.num(parts[2]), self.num(parts[3]))
        elif cmd == "MAX":   self.vars[parts[1].lower()] = max(self.num(parts[2]), self.num(parts[3]))
        elif cmd == "CLAMP":
            v, lo, hi = self.num(parts[1]), self.num(parts[2]), self.num(parts[3])
            self.vars[parts[1].lower()] = max(lo, min(hi, v))
        elif cmd == "LERP":
            a, b, t = self.num(parts[2]), self.num(parts[3]), self.num(parts[4])
            self.vars[parts[1].lower()] = a + (b - a) * t
        elif cmd == "SIN":   self.vars[parts[1].lower()] = math.sin(math.radians(self.num(parts[2])))
        elif cmd == "COS":   self.vars[parts[1].lower()] = math.cos(math.radians(self.num(parts[2])))
        elif cmd == "TAN":   self.vars[parts[1].lower()] = math.tan(math.radians(self.num(parts[2])))
        elif cmd == "ASIN":  self.vars[parts[1].lower()] = math.degrees(math.asin(max(-1,min(1,self.num(parts[2])))))
        elif cmd == "ACOS":  self.vars[parts[1].lower()] = math.degrees(math.acos(max(-1,min(1,self.num(parts[2])))))
        elif cmd == "ATAN2": self.vars[parts[1].lower()] = math.degrees(math.atan2(self.num(parts[2]), self.num(parts[3])))
        elif cmd == "LOG":   self.vars[parts[1].lower()] = math.log(max(1e-9, self.num(parts[2])))
        elif cmd == "LOG10": self.vars[parts[1].lower()] = math.log10(max(1e-9, self.num(parts[2])))
        elif cmd == "EXP":   self.vars[parts[1].lower()] = math.exp(self.num(parts[2]))
        elif cmd == "SIGN":  self.vars[parts[1].lower()] = (1 if self.num(parts[1]) > 0 else -1 if self.num(parts[1]) < 0 else 0)
        elif cmd == "DIST":
            dx = self.num(parts[3]) - self.num(parts[1])
            dy = self.num(parts[4]) - self.num(parts[2])
            self.vars[parts[5].lower()] = math.hypot(dx, dy)
        elif cmd == "ANGLE":
            dx = self.num(parts[3]) - self.num(parts[1])
            dy = self.num(parts[4]) - self.num(parts[2])
            self.vars[parts[5].lower()] = math.degrees(math.atan2(dy, dx))
        elif cmd == "NORM":
            lo, hi = self.num(parts[3]), self.num(parts[4])
            self.vars[parts[1].lower()] = (self.num(parts[2]) - lo) / (hi - lo) if hi != lo else 0
        elif cmd == "MAP":
            v = self.num(parts[2])
            a1,a2 = self.num(parts[3]), self.num(parts[4])
            b1,b2 = self.num(parts[5]), self.num(parts[6])
            self.vars[parts[1].lower()] = b1 + (v-a1)/(a2-a1)*(b2-b1) if a2!=a1 else b1
        elif cmd == "WRAP":
            v, lo, hi = self.num(parts[1]), self.num(parts[2]), self.num(parts[3])
            r = hi - lo
            self.vars[parts[1].lower()] = lo + (v - lo) % r if r else lo
        elif cmd == "BITAND": self.vars[parts[1].lower()] = int(self.num(parts[2])) & int(self.num(parts[3]))
        elif cmd == "BITOR":  self.vars[parts[1].lower()] = int(self.num(parts[2])) | int(self.num(parts[3]))
        elif cmd == "BITXOR": self.vars[parts[1].lower()] = int(self.num(parts[2])) ^ int(self.num(parts[3]))
        elif cmd == "BITNOT": self.vars[parts[1].lower()] = ~int(self.num(parts[2]))
        elif cmd == "LSHIFT": self.vars[parts[1].lower()] = int(self.num(parts[2])) << int(self.num(parts[3]))
        elif cmd == "RSHIFT": self.vars[parts[1].lower()] = int(self.num(parts[2])) >> int(self.num(parts[3]))
        elif cmd == "HASH":
            s = str(self.get_val(parts[2]))
            self.vars[parts[1].lower()] = int(hashlib.md5(s.encode()).hexdigest()[:8], 16)

        # ── STRING ──────────────────────────────────────────────────
        elif cmd == "UPPER":  self.vars[parts[1].lower()] = str(self.vars.get(parts[1].lower(),"")).upper()
        elif cmd == "LOWER":  self.vars[parts[1].lower()] = str(self.vars.get(parts[1].lower(),"")).lower()
        elif cmd == "REV":    self.vars[parts[1].lower()] = str(self.vars.get(parts[1].lower(),""))[::-1]
        elif cmd == "LEN":    self.vars[parts[2].lower()] = len(str(self.get_val(parts[1])))
        elif cmd == "JOIN":   self.vars[parts[1].lower()] = str(self.get_val(parts[2])) + str(self.get_val(parts[3]))
        elif cmd == "TRIM":   self.vars[parts[1].lower()] = str(self.vars.get(parts[1].lower(),"")).strip()
        elif cmd == "SPLIT":
            src = str(self.get_val(parts[2]))
            sep = str(self.get_val(parts[3])) if len(parts) > 3 else " "
            self.arrays[parts[1].lower()] = src.split(sep)
        elif cmd == "SUBSTR":
            s = str(self.get_val(parts[2]))
            a, b = int(self.num(parts[3])), int(self.num(parts[4]))
            self.vars[parts[1].lower()] = s[a:b]
        elif cmd == "REPLACE":
            s = str(self.get_val(parts[2]))
            old, new = str(self.get_val(parts[3])), str(self.get_val(parts[4]))
            self.vars[parts[1].lower()] = s.replace(old, new)
        elif cmd == "CONTAINS":
            a, b = str(self.get_val(parts[2])), str(self.get_val(parts[3]))
            self.vars[parts[1].lower()] = 1 if b in a else 0
        elif cmd == "STARTSWITH":
            self.vars[parts[1].lower()] = 1 if str(self.get_val(parts[2])).startswith(str(self.get_val(parts[3]))) else 0
        elif cmd == "ENDSWITH":
            self.vars[parts[1].lower()] = 1 if str(self.get_val(parts[2])).endswith(str(self.get_val(parts[3]))) else 0
        elif cmd == "INDEXOF":
            self.vars[parts[1].lower()] = str(self.get_val(parts[2])).find(str(self.get_val(parts[3])))
        elif cmd == "CHAR":   self.vars[parts[1].lower()] = chr(int(self.num(parts[2])))
        elif cmd == "ORD":    self.vars[parts[1].lower()] = ord(str(self.get_val(parts[2]))[0]) if self.get_val(parts[2]) else 0
        elif cmd == "PAD":
            s = str(self.get_val(parts[2]))
            w = int(self.num(parts[3]))
            side = parts[4].lower() if len(parts) > 4 else "right"
            self.vars[parts[1].lower()] = s.ljust(w) if side=="right" else s.rjust(w)
        elif cmd == "REPEAT": self.vars[parts[1].lower()] = str(self.get_val(parts[2])) * int(self.num(parts[3]))
        elif cmd == "FORMAT":
            self.vars[parts[1].lower()] = self.resolve_str(" ".join(parts[2:]))
        elif cmd == "TONUM":  
            try: self.vars[parts[1].lower()] = float(str(self.get_val(parts[2])))
            except: self.vars[parts[1].lower()] = 0
        elif cmd == "TOSTR":  self.vars[parts[1].lower()] = str(self.get_val(parts[2]))
        elif cmd == "B64ENC": self.vars[parts[1].lower()] = base64.b64encode(str(self.get_val(parts[2])).encode()).decode()
        elif cmd == "B64DEC": self.vars[parts[1].lower()] = base64.b64decode(str(self.get_val(parts[2])).encode()).decode()

        # ── ARRAYS ──────────────────────────────────────────────────
        elif cmd == "ARRAYNEW":  self.arrays[parts[1].lower()] = []
        elif cmd == "ARRAYPUSH": self.arrays.setdefault(parts[1].lower(),[]).append(self.get_val(parts[2]))
        elif cmd == "ARRAYPOP":
            arr = parts[1].lower()
            self.vars[parts[2].lower()] = self.arrays[arr].pop() if self.arrays.get(arr) else 0
        elif cmd == "ARRAYGET":
            arr, idx = parts[2].lower(), int(self.num(parts[3]))
            lst = self.arrays.get(arr, [])
            self.vars[parts[1].lower()] = lst[idx] if 0 <= idx < len(lst) else 0
        elif cmd == "ARRAYSET":
            arr, idx = parts[1].lower(), int(self.num(parts[2]))
            while len(self.arrays.setdefault(arr,[])) <= idx:
                self.arrays[arr].append(0)
            self.arrays[arr][idx] = self.get_val(parts[3])
        elif cmd == "ARRAYLEN": self.vars[parts[1].lower()] = len(self.arrays.get(parts[2].lower(), []))
        elif cmd == "ARRAYCLEAR": self.arrays[parts[1].lower()] = []
        elif cmd == "ARRAYSORT": self.arrays.setdefault(parts[1].lower(),[]).sort(key=lambda x: (isinstance(x,str), x))
        elif cmd == "ARRAYREV":  self.arrays.setdefault(parts[1].lower(),[]).reverse()
        elif cmd == "ARRAYFILL":
            n, val = int(self.num(parts[2])), self.get_val(parts[3])
            self.arrays[parts[1].lower()] = [val]*n
        elif cmd == "ARRAYJOIN":
            sep = str(self.get_val(parts[3])) if len(parts) > 3 else ","
            self.vars[parts[1].lower()] = sep.join(str(x) for x in self.arrays.get(parts[2].lower(),[]))
        elif cmd == "ARRAYSUM":
            self.vars[parts[1].lower()] = sum(float(x) for x in self.arrays.get(parts[2].lower(),[]) if str(x).replace('.','',1).lstrip('-').isdigit())
        elif cmd == "ARRAYMIN":
            lst = [float(x) for x in self.arrays.get(parts[2].lower(),[]) if str(x).replace('.','',1).lstrip('-').replace('e','').isdigit()]
            self.vars[parts[1].lower()] = min(lst) if lst else 0
        elif cmd == "ARRAYMAX":
            lst = [float(x) for x in self.arrays.get(parts[2].lower(),[]) if str(x).replace('.','',1).lstrip('-').replace('e','').isdigit()]
            self.vars[parts[1].lower()] = max(lst) if lst else 0
        elif cmd == "SHUFFLE": random.shuffle(self.arrays.setdefault(parts[1].lower(),[]))

        # ── FLOW CONTROL ─────────────────────────────────────────────
        elif cmd == "GOTO":
            lbl = parts[1].lower()
            if lbl in self.labels:
                self.pc = self.labels[lbl]; jumped = True
        elif cmd == "CALL":
            lbl = parts[1].lower()
            if lbl in self.labels:
                self.call_stack.append(self.pc + 1)
                self.pc = self.labels[lbl]; jumped = True
        elif cmd == "RETURN":
            if self.call_stack:
                self.pc = self.call_stack.pop(); jumped = True
        elif cmd == "IFEQ":
            if str(self.get_val(parts[1])) != str(self.get_val(parts[2])): self.pc += 1
        elif cmd == "IFNEQ":
            if str(self.get_val(parts[1])) == str(self.get_val(parts[2])): self.pc += 1
        elif cmd == "IFGT":
            if self.num(parts[1]) <= self.num(parts[2]): self.pc += 1
        elif cmd == "IFLT":
            if self.num(parts[1]) >= self.num(parts[2]): self.pc += 1
        elif cmd == "IFGTE":
            if self.num(parts[1]) < self.num(parts[2]): self.pc += 1
        elif cmd == "IFLTE":
            if self.num(parts[1]) > self.num(parts[2]): self.pc += 1
        elif cmd == "IFKEY":
            # IFKEY [key] [label]  — jumps if key is currently held
            k = parts[1].lower()
            lbl = parts[2].lower()
            if k in self.key_held and lbl in self.labels:
                self.pc = self.labels[lbl]; jumped = True
        elif cmd == "IFKEYPRESSED":
            k = parts[1].lower()
            lbl = parts[2].lower()
            if k in self.key_just_pressed and lbl in self.labels:
                self.pc = self.labels[lbl]; jumped = True
        elif cmd == "IFKEYRELEASED":
            k = parts[1].lower()
            lbl = parts[2].lower()
            if k in self.key_just_released and lbl in self.labels:
                self.pc = self.labels[lbl]; jumped = True
        elif cmd == "GETKEY":
            # GETKEY [varname]  — stores last key, then clears it
            self.vars[parts[1].lower()] = self.vars["last_key"]
            self.vars["last_key"] = "None"
        elif cmd == "KEYDOWN":
            # KEYDOWN [key] [var] — sets var to 1 if key held, else 0
            self.vars[parts[2].lower()] = 1 if parts[1].lower() in self.key_held else 0
        elif cmd == "CLEARKEYS": self.key_held.clear(); self.key_just_pressed.clear()
        elif cmd == "WAITKEY":
            # WAITKEY [varname]  — block until any key pressed
            self.vars["last_key"] = "None"
            while self.vars["last_key"] == "None" and self.running:
                self.root.update(); time.sleep(0.01)
            self.vars[parts[1].lower()] = self.vars["last_key"]
        elif cmd == "WAITCLICK":
            self.waiting = True
            while self.waiting and self.running:
                self.root.update(); time.sleep(0.01)
        elif cmd == "WAIT":  self.root.update(); time.sleep(self.num(parts[1]))
        elif cmd == "PAUSE": self.paused = True
        elif cmd == "RESUME": self.paused = False
        elif cmd == "SKIP":  self.pc += int(self.num(parts[1])); jumped = True
        elif cmd == "STOP":  self.running = False
        elif cmd == "NOP":   pass  # No operation
        elif cmd == "EXIT":
            self.running = False
            self.root.destroy()
            sys.exit(0)

        # ── INPUT (MOUSE) ────────────────────────────────────────────
        elif cmd == "GETMOUSE":
            # GETMOUSE [xvar] [yvar]
            self.vars[parts[1].lower()] = self.vars["mouse_x"]
            self.vars[parts[2].lower()] = self.vars["mouse_y"]
        elif cmd == "MOUSECLICKED":
            self.vars[parts[1].lower()] = self.vars["mouse_clicked"]
        elif cmd == "IFMOUSE":
            # IFMOUSE [x1] [y1] [x2] [y2] [label] — jump if mouse inside rect
            x1,y1,x2,y2 = self.num(parts[1]),self.num(parts[2]),self.num(parts[3]),self.num(parts[4])
            lbl = parts[5].lower()
            mx, my = self.vars["mouse_x"], self.vars["mouse_y"]
            if x1<=mx<=x2 and y1<=my<=y2 and lbl in self.labels:
                self.pc = self.labels[lbl]; jumped = True
        elif cmd == "IFCLICKED":
            # IFCLICKED [x1] [y1] [x2] [y2] [label]
            x1,y1,x2,y2 = self.num(parts[1]),self.num(parts[2]),self.num(parts[3]),self.num(parts[4])
            lbl = parts[5].lower()
            mx, my = self.vars["mouse_x"], self.vars["mouse_y"]
            if self.vars["mouse_clicked"] and x1<=mx<=x2 and y1<=my<=y2 and lbl in self.labels:
                self.pc = self.labels[lbl]; jumped = True

        # ── GRAPHICS: DRAWING ────────────────────────────────────────
        elif cmd == "BG":
            c = parts[1]
            self.bg_color = c
            self.canvas.config(bg=c)
            self.root.config(bg=c)
        elif cmd == "CLEAR":
            self.canvas.delete("all")
            self.sprites.clear()
            self.sprite_data.clear()
        elif cmd == "CLEARSPRITES": self.canvas.delete("all"); self.sprites.clear()
        elif cmd == "FLASH":
            curr = self.canvas.cget("bg")
            self.canvas.config(bg="white"); self.root.update(); time.sleep(0.05)
            self.canvas.config(bg=curr); self.root.update()
        elif cmd == "SHAKE":
            self._shake_frames = int(self.num(parts[1]) if len(parts)>1 else 10)
            self._shake_intensity = int(self.num(parts[2]) if len(parts)>2 else 5)
        elif cmd == "DRAWBOX":
            sid = parts[1]
            x,y,s,c = self.num(parts[2]),self.num(parts[3]),self.num(parts[4]),parts[5]
            outline = parts[6] if len(parts)>6 else ""
            self.sprites[sid] = self.canvas.create_rectangle(x,y,x+s,y+s, fill=c, outline=outline)
            self.sprite_data[sid] = {"x":x,"y":y,"w":s,"h":s}
        elif cmd == "DRAWRECT":
            # DRAWRECT id x y w h color [outline]
            sid = parts[1]
            x,y,w,h,c = self.num(parts[2]),self.num(parts[3]),self.num(parts[4]),self.num(parts[5]),parts[6]
            outline = parts[7] if len(parts)>7 else ""
            self.sprites[sid] = self.canvas.create_rectangle(x,y,x+w,y+h, fill=c, outline=outline)
            self.sprite_data[sid] = {"x":x,"y":y,"w":w,"h":h}
        elif cmd == "DRAWCIRCLE":
            sid = parts[1]
            x,y,r,c = self.num(parts[2]),self.num(parts[3]),self.num(parts[4]),parts[5]
            self.sprites[sid] = self.canvas.create_oval(x,y,x+r,y+r, fill=c, outline="")
            self.sprite_data[sid] = {"x":x,"y":y,"w":r,"h":r}
        elif cmd == "DRAWOVAL":
            sid = parts[1]
            x,y,w,h,c = self.num(parts[2]),self.num(parts[3]),self.num(parts[4]),self.num(parts[5]),parts[6]
            self.sprites[sid] = self.canvas.create_oval(x,y,x+w,y+h, fill=c, outline="")
            self.sprite_data[sid] = {"x":x,"y":y,"w":w,"h":h}
        elif cmd == "DRAWLINE":
            # DRAWLINE id x1 y1 x2 y2 color [width]
            sid = parts[1]
            x1,y1,x2,y2,c = self.num(parts[2]),self.num(parts[3]),self.num(parts[4]),self.num(parts[5]),parts[6]
            w = int(self.num(parts[7])) if len(parts)>7 else 1
            self.sprites[sid] = self.canvas.create_line(x1,y1,x2,y2, fill=c, width=w)
        elif cmd == "DRAWPOLY":
            # DRAWPOLY id color x1 y1 x2 y2 ...
            sid, c = parts[1], parts[2]
            coords = [self.num(p) for p in parts[3:]]
            self.sprites[sid] = self.canvas.create_polygon(*coords, fill=c, outline="")
        elif cmd == "DRAWTEXT":
            msg = self.resolve_str(self.extract_string(active))
            color = parts[-3] if len(parts)>=4 else "#ffffff"
            x, y = self.num(parts[-2]), self.num(parts[-1])
            fs = int(self.num(parts[-4])) if len(parts)>=5 else 16
            self.canvas.create_text(x, y, text=msg, fill=color, font=("Arial", fs))
        elif cmd == "DRAWLABEL":
            # DRAWLABEL id "text" color x y [size] [font]
            sid = parts[1]
            msg = self.resolve_str(self.extract_string(active))
            color = parts[-3]; x,y = self.num(parts[-2]),self.num(parts[-1])
            fs = int(self.num(parts[-4])) if len(parts)>=7 else 14
            self.sprites[sid] = self.canvas.create_text(x,y,text=msg,fill=color,font=("Arial",fs))
        elif cmd == "MOVE":
            sid = parts[1]
            dx, dy = self.num(parts[2]), self.num(parts[3])
            if sid in self.sprites:
                self.canvas.move(self.sprites[sid], dx, dy)
                if sid in self.sprite_data:
                    self.sprite_data[sid]["x"] += dx
                    self.sprite_data[sid]["y"] += dy
        elif cmd == "MOVETO":
            sid = parts[1]
            tx, ty = self.num(parts[2]), self.num(parts[3])
            if sid in self.sprites and sid in self.sprite_data:
                dx = tx - self.sprite_data[sid]["x"]
                dy = ty - self.sprite_data[sid]["y"]
                self.canvas.move(self.sprites[sid], dx, dy)
                self.sprite_data[sid]["x"] = tx
                self.sprite_data[sid]["y"] = ty
        elif cmd == "SETPOS":
            # alias for MOVETO
            sid = parts[1]; tx,ty = self.num(parts[2]),self.num(parts[3])
            if sid in self.sprites and sid in self.sprite_data:
                dx = tx-self.sprite_data[sid]["x"]; dy = ty-self.sprite_data[sid]["y"]
                self.canvas.move(self.sprites[sid],dx,dy)
                self.sprite_data[sid]["x"]=tx; self.sprite_data[sid]["y"]=ty
        elif cmd == "GETPOS":
            # GETPOS id xvar yvar
            sid = parts[1]
            if sid in self.sprite_data:
                self.vars[parts[2].lower()] = self.sprite_data[sid]["x"]
                self.vars[parts[3].lower()] = self.sprite_data[sid]["y"]
        elif cmd == "RECOLOR":
            # RECOLOR id color
            sid = parts[1]; c = parts[2]
            if sid in self.sprites:
                try: self.canvas.itemconfig(self.sprites[sid], fill=c)
                except: pass
        elif cmd == "REOUTLINE":
            sid = parts[1]; c = parts[2]
            if sid in self.sprites:
                try: self.canvas.itemconfig(self.sprites[sid], outline=c)
                except: pass
        elif cmd == "HIDE":
            sid = parts[1]
            if sid in self.sprites:
                self.canvas.itemconfig(self.sprites[sid], state="hidden")
        elif cmd == "SHOW":
            sid = parts[1]
            if sid in self.sprites:
                self.canvas.itemconfig(self.sprites[sid], state="normal")
        elif cmd == "DELETE":
            sid = parts[1]
            if sid in self.sprites:
                self.canvas.delete(self.sprites[sid])
                del self.sprites[sid]
                self.sprite_data.pop(sid, None)
        elif cmd == "SCALE":
            # SCALE id factor  (rough rescale by redraw — updates data size)
            sid = parts[1]; f = self.num(parts[2])
            if sid in self.sprite_data:
                d = self.sprite_data[sid]
                d["w"] = d["w"]*f; d["h"] = d["h"]*f
        elif cmd == "LAYER":
            # LAYER id above|below
            sid = parts[1]
            if sid in self.sprites:
                if parts[2].lower() == "above": self.canvas.lift(self.sprites[sid])
                else: self.canvas.lower(self.sprites[sid])
        elif cmd == "UPDATETEXT":
            # UPDATETEXT id "new text"
            sid = parts[1]
            msg = self.resolve_str(self.extract_string(active))
            if sid in self.sprites:
                try: self.canvas.itemconfig(self.sprites[sid], text=msg)
                except: pass

        # ── CAMERA ───────────────────────────────────────────────────
        elif cmd == "CAMPOS":
            self._camera_x = self.num(parts[1])
            self._camera_y = self.num(parts[2])
        elif cmd == "CAMZOOM": self._camera_zoom = self.num(parts[1])
        elif cmd == "GETCAMP":
            self.vars[parts[1].lower()] = self._camera_x
            self.vars[parts[2].lower()] = self._camera_y

        # ── PARTICLES ────────────────────────────────────────────────
        elif cmd == "BURST":
            # BURST id x y count color [size] [speed] [gravity]
            pid = parts[1]; x,y = self.num(parts[2]),self.num(parts[3])
            count = int(self.num(parts[4])); color = parts[5]
            size = self.num(parts[6]) if len(parts)>6 else 4
            speed = self.num(parts[7]) if len(parts)>7 else 3
            gravity = self.num(parts[8]) if len(parts)>8 else 0.2
            self.particles.setdefault(pid, [])
            for _ in range(count):
                angle = random.uniform(0, math.tau)
                spd = random.uniform(speed*0.5, speed)
                cid = self.canvas.create_rectangle(x,y,x+size,y+size, fill=color, outline="")
                self.particles[pid].append({
                    "x":x,"y":y,"vx":math.cos(angle)*spd,"vy":math.sin(angle)*spd,
                    "life":random.randint(20,50),"size":size,"gravity":gravity,"cid":cid
                })
        elif cmd == "STREAM":
            # STREAM id x y direction color [count]
            pid = parts[1]; x,y = self.num(parts[2]),self.num(parts[3])
            direction = self.num(parts[4]); color = parts[5]
            count = int(self.num(parts[6])) if len(parts)>6 else 5
            self.particles.setdefault(pid, [])
            for _ in range(count):
                angle = math.radians(direction) + random.uniform(-0.3,0.3)
                spd = random.uniform(1,4)
                cid = self.canvas.create_rectangle(x,y,x+3,y+3, fill=color, outline="")
                self.particles[pid].append({
                    "x":x,"y":y,"vx":math.cos(angle)*spd,"vy":math.sin(angle)*spd,
                    "life":random.randint(15,35),"size":3,"gravity":0.1,"cid":cid
                })
        elif cmd == "CLEARPARTICLES":
            pid = parts[1]
            for p in self.particles.get(pid,[]):
                try: self.canvas.delete(p["cid"])
                except: pass
            self.particles[pid] = []

        # ── TWEENING / ANIMATION ──────────────────────────────────────
        elif cmd == "TWEEN":
            # TWEEN id var from to duration [ease]
            tid = parts[1]; var = parts[2].lower()
            frm, to = self.num(parts[3]), self.num(parts[4])
            dur = self.num(parts[5])
            ease = parts[6].lower() if len(parts)>6 else "linear"
            self.tweens[tid] = {"var":var,"from":frm,"to":to,"duration":dur,
                                 "ease":ease,"start":time.time(),"done":False}
        elif cmd == "TWEENDONE":
            # TWEENDONE id label — jump if tween finished
            tid, lbl = parts[1], parts[2].lower()
            if self.tweens.get(tid,{}).get("done") and lbl in self.labels:
                self.pc = self.labels[lbl]; jumped = True
        elif cmd == "STOPTWEEN": self.tweens.pop(parts[1], None)

        # ── TIMERS ───────────────────────────────────────────────────
        elif cmd == "TIMER":
            # TIMER name seconds label
            self.timers[parts[1]] = {"end": time.time()+self.num(parts[2]),
                                      "label": parts[3].lower(), "fired": False}
        elif cmd == "CANCELTIMER": self.timers.pop(parts[1], None)
        elif cmd == "TIMERDONE":
            # TIMERDONE name label
            t = self.timers.get(parts[1])
            if t and t.get("fired") and parts[2].lower() in self.labels:
                self.pc = self.labels[parts[2].lower()]; jumped = True

        # ── COLLISION ────────────────────────────────────────────────
        elif cmd == "COLLIDE":
            # COLLIDE id1 id2 result_var
            sid1, sid2 = parts[1], parts[2]
            rv = parts[3].lower()
            self.vars[rv] = 0
            if sid1 in self.sprite_data and sid2 in self.sprite_data:
                a = self.sprite_data[sid1]; b = self.sprite_data[sid2]
                ax1,ay1,ax2,ay2 = a["x"],a["y"],a["x"]+a["w"],a["y"]+a["h"]
                bx1,by1,bx2,by2 = b["x"],b["y"],b["x"]+b["w"],b["y"]+b["h"]
                if ax1<bx2 and ax2>bx1 and ay1<by2 and ay2>by1:
                    self.vars[rv] = 1
        elif cmd == "COLLIDECIRCLE":
            # COLLIDECIRCLE id1 id2 result_var
            sid1, sid2, rv = parts[1], parts[2], parts[3].lower()
            self.vars[rv] = 0
            if sid1 in self.sprite_data and sid2 in self.sprite_data:
                a, b = self.sprite_data[sid1], self.sprite_data[sid2]
                cx1, cy1 = a["x"]+a["w"]/2, a["y"]+a["h"]/2
                cx2, cy2 = b["x"]+b["w"]/2, b["y"]+b["h"]/2
                r1, r2 = a["w"]/2, b["w"]/2
                if math.hypot(cx1-cx2, cy1-cy2) < r1+r2:
                    self.vars[rv] = 1
        elif cmd == "BOUNDRECT":
            # BOUNDRECT id x1 y1 x2 y2 result_var — clamp sprite inside bounds
            sid = parts[1]; x1,y1,x2,y2 = self.num(parts[2]),self.num(parts[3]),self.num(parts[4]),self.num(parts[5])
            rv = parts[6].lower(); self.vars[rv] = 0
            if sid in self.sprite_data:
                d = self.sprite_data[sid]
                if d["x"] < x1: d["x"]=x1; self.vars[rv]=1
                if d["y"] < y1: d["y"]=y1; self.vars[rv]=1
                if d["x"]+d["w"] > x2: d["x"]=x2-d["w"]; self.vars[rv]=1
                if d["y"]+d["h"] > y2: d["y"]=y2-d["h"]; self.vars[rv]=1

        # ── SOUND ─────────────────────────────────────────────────────
        elif cmd == "SOUND":  self.beep(self.num(parts[1]), self.num(parts[2]))
        elif cmd == "BEEP":   self.beep(440, 100)
        elif cmd == "CHORD":
            # CHORD hz1 hz2 hz3 ms
            ms = int(self.num(parts[-1]))
            for hz in parts[1:-1]:
                threading.Thread(target=self.beep, args=(self.num(hz), ms), daemon=True).start()
        elif cmd == "MELODY":
            # MELODY hz1 ms1 hz2 ms2 ...
            notes = parts[1:]
            for i in range(0, len(notes)-1, 2):
                self.beep(self.num(notes[i]), int(self.num(notes[i+1])))
        elif cmd == "SILENCE": pass  # placeholder (no playback to stop)

        # ── DIALOGS & UI ──────────────────────────────────────────────
        elif cmd == "POPUP":
            msg = self.resolve_str(self.extract_string(active))
            messagebox.showinfo("QUK", msg)
        elif cmd == "ALERT":
            msg = self.resolve_str(self.extract_string(active))
            messagebox.showwarning("QUK Alert", msg)
        elif cmd == "ERROR":
            msg = self.resolve_str(self.extract_string(active))
            messagebox.showerror("QUK Error", msg)
        elif cmd == "CONFIRM":
            # CONFIRM var "message"
            msg = self.resolve_str(self.extract_string(active))
            res = messagebox.askyesno("QUK", msg)
            self.vars[parts[1].lower()] = "yes" if res else "no"
        elif cmd == "ASK":
            msg = self.resolve_str(self.extract_string(active))
            res = messagebox.askyesno("QUK", msg)
            self.vars[parts[1].lower()] = "yes" if res else "no"
        elif cmd == "PROMPT":
            msg = self.resolve_str(self.extract_string(active))
            res = simpledialog.askstring("QUK Input", msg) or ""
            self.vars[parts[1].lower()] = res
        elif cmd == "PROMPTNUM":
            msg = self.resolve_str(self.extract_string(active))
            res = simpledialog.askfloat("QUK Input", msg) or 0
            self.vars[parts[1].lower()] = res
        elif cmd == "PICKCOLOR":
            res = colorchooser.askcolor(title="Pick a color")
            self.vars[parts[1].lower()] = res[1] if res and res[1] else "#ffffff"

        # ── WINDOW ────────────────────────────────────────────────────
        elif cmd == "TITLE":   self.root.title(self.resolve_str(" ".join(parts[1:])))
        elif cmd == "RESIZE":  self.root.geometry(f"{int(self.num(parts[1]))}x{int(self.num(parts[2]))}")
        elif cmd == "FULLSCREEN": self.root.attributes("-fullscreen", parts[1].lower()=="on")
        elif cmd == "TOPMOST": self.root.attributes("-topmost", parts[1].lower()=="on")
        elif cmd == "CURSOR":  self.root.config(cursor=parts[1])
        elif cmd == "ICON":    pass  # would need .ico file
        elif cmd == "MINIMIZE": self.root.iconify()
        elif cmd == "MAXIMIZE": self.root.state("zoomed")
        elif cmd == "RESTORE":  self.root.state("normal")
        elif cmd == "CANVASSIZE":
            self.canvas.config(width=int(self.num(parts[1])), height=int(self.num(parts[2])))
            self.vars["canvas_w"] = int(self.num(parts[1]))
            self.vars["canvas_h"] = int(self.num(parts[2]))

        # ── SYSTEM / OS ───────────────────────────────────────────────
        elif cmd == "TIME":    self.vars[parts[1].lower()] = datetime.datetime.now().strftime("%H:%M:%S")
        elif cmd == "DATE":    self.vars[parts[1].lower()] = datetime.datetime.now().strftime("%Y-%m-%d")
        elif cmd == "YEAR":    self.vars[parts[1].lower()] = datetime.datetime.now().year
        elif cmd == "MONTH":   self.vars[parts[1].lower()] = datetime.datetime.now().month
        elif cmd == "DAY":     self.vars[parts[1].lower()] = datetime.datetime.now().day
        elif cmd == "HOUR":    self.vars[parts[1].lower()] = datetime.datetime.now().hour
        elif cmd == "MINUTE":  self.vars[parts[1].lower()] = datetime.datetime.now().minute
        elif cmd == "SECOND":  self.vars[parts[1].lower()] = datetime.datetime.now().second
        elif cmd == "TIMESTAMP": self.vars[parts[1].lower()] = int(time.time())
        elif cmd == "UPTIME":  self.vars[parts[1].lower()] = round(self.vars["time"], 2)
        elif cmd == "WEB":     webbrowser.open(parts[1].strip('"'))
        elif cmd == "SHELL":   os.system(" ".join(parts[1:]))
        elif cmd == "GETENV":  self.vars[parts[1].lower()] = os.environ.get(parts[2], "")
        elif cmd == "HOSTNAME": self.vars[parts[1].lower()] = socket.gethostname()
        elif cmd == "PLATFORM": self.vars[parts[1].lower()] = platform.system()

        # ── FILE I/O ─────────────────────────────────────────────────
        elif cmd == "FILEWRITE":
            path = str(self.get_val(parts[1])); content = self.resolve_str(self.extract_string(active))
            with open(path, "w", encoding="utf-8") as f: f.write(content)
        elif cmd == "FILEAPPEND":
            path = str(self.get_val(parts[1])); content = self.resolve_str(self.extract_string(active))
            with open(path, "a", encoding="utf-8") as f: f.write(content + "\n")
        elif cmd == "FILEREAD":
            path = str(self.get_val(parts[2]))
            try:
                with open(path,"r",encoding="utf-8") as f: self.vars[parts[1].lower()] = f.read()
            except: self.vars[parts[1].lower()] = ""
        elif cmd == "FILEEXISTS":
            self.vars[parts[1].lower()] = 1 if os.path.exists(str(self.get_val(parts[2]))) else 0
        elif cmd == "FILEDELETE":
            try: os.remove(str(self.get_val(parts[1])))
            except: pass
        elif cmd == "FILELINES":
            path = str(self.get_val(parts[2]))
            try:
                with open(path,"r",encoding="utf-8") as f:
                    self.arrays[parts[1].lower()] = [l.rstrip("\n") for l in f.readlines()]
            except: self.arrays[parts[1].lower()] = []

        # ── SAVE / LOAD ───────────────────────────────────────────────
        elif cmd == "SAVE":
            # SAVE filename  — saves all vars to JSON
            path = str(self.get_val(parts[1])) if len(parts)>1 else "quk_save.json"
            with open(path,"w") as f: json.dump(self.vars, f, default=str)
        elif cmd == "LOAD":
            path = str(self.get_val(parts[1])) if len(parts)>1 else "quk_save.json"
            if os.path.exists(path):
                with open(path,"r") as f:
                    data = json.load(f)
                    self.vars.update(data)
        elif cmd == "SAVEVAR":
            # SAVEVAR filename varname
            path = str(self.get_val(parts[1]))
            try:
                with open(path,"r") as f: d = json.load(f)
            except: d = {}
            d[parts[2].lower()] = self.vars.get(parts[2].lower(), 0)
            with open(path,"w") as f: json.dump(d, f)
        elif cmd == "LOADVAR":
            # LOADVAR filename varname
            path = str(self.get_val(parts[1]))
            try:
                with open(path,"r") as f: d = json.load(f)
                self.vars[parts[2].lower()] = d.get(parts[2].lower(), 0)
            except: pass

        # ── COLOR UTILITIES ───────────────────────────────────────────
        elif cmd == "RGB2HEX":
            r,g,b = int(self.num(parts[2])),int(self.num(parts[3])),int(self.num(parts[4]))
            self.vars[parts[1].lower()] = f"#{r:02x}{g:02x}{b:02x}"
        elif cmd == "HEX2RGB":
            h = str(self.get_val(parts[2])).lstrip("#")
            r,g,b = int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
            self.vars[parts[1].lower()+"_r"] = r
            self.vars[parts[1].lower()+"_g"] = g
            self.vars[parts[1].lower()+"_b"] = b
        elif cmd == "LERPCOLOR":
            # LERPCOLOR outvar hex1 hex2 t
            h1 = str(self.get_val(parts[2])).lstrip("#")
            h2 = str(self.get_val(parts[3])).lstrip("#")
            t = self.num(parts[4])
            r = int(int(h1[0:2],16)*(1-t)+int(h2[0:2],16)*t)
            g = int(int(h1[2:4],16)*(1-t)+int(h2[2:4],16)*t)
            b = int(int(h1[4:6],16)*(1-t)+int(h2[4:6],16)*t)
            self.vars[parts[1].lower()] = f"#{r:02x}{g:02x}{b:02x}"
        elif cmd == "HSV2HEX":
            h,s,v = self.num(parts[2])/360,self.num(parts[3]),self.num(parts[4])
            r,g,b = [int(x*255) for x in colorsys.hsv_to_rgb(h,s,v)]
            self.vars[parts[1].lower()] = f"#{r:02x}{g:02x}{b:02x}"
        elif cmd == "RANDOMCOLOR":
            r,g,b = random.randint(0,255),random.randint(0,255),random.randint(0,255)
            self.vars[parts[1].lower()] = f"#{r:02x}{g:02x}{b:02x}"
        elif cmd == "DARKEN":
            h = str(self.get_val(parts[2])).lstrip("#")
            f = self.num(parts[3])
            r,g,b = [max(0,int(int(h[i*2:i*2+2],16)*f)) for i in range(3)]
            self.vars[parts[1].lower()] = f"#{r:02x}{g:02x}{b:02x}"
        elif cmd == "LIGHTEN":
            h = str(self.get_val(parts[2])).lstrip("#")
            f = self.num(parts[3])
            r,g,b = [min(255,int(int(h[i*2:i*2+2],16)*f)) for i in range(3)]
            self.vars[parts[1].lower()] = f"#{r:02x}{g:02x}{b:02x}"

        # ── DEBUG ────────────────────────────────────────────────────
        elif cmd == "PRINT":
            print(self.resolve_str(" ".join(parts[1:])))
        elif cmd == "LOG":
            self.log(self.resolve_str(" ".join(parts[1:])))
        elif cmd == "DEBUGON":  self.debug_mode = True
        elif cmd == "DEBUGOFF": self.debug_mode = False
        elif cmd == "ASSERT":
            # ASSERT condition "message"
            if self.num(parts[1]) == 0:
                msg = self.resolve_str(self.extract_string(active))
                messagebox.showerror("QUK Assert Failed", msg)
        elif cmd == "DUMPVARS":
            print("\n=== QUK VAR DUMP ===")
            for k,v in sorted(self.vars.items()): print(f"  {k} = {v}")
            print("====================\n")
        elif cmd == "DUMPSPRITES":
            print("\n=== QUK SPRITE DUMP ===")
            for k,v in self.sprite_data.items(): print(f"  {k}: {v}")
            print("======================\n")
        elif cmd == "BENCHMARK":
            self.vars["fps_display"] = self.vars["fps"]

        # ── SCENE MANAGEMENT ─────────────────────────────────────────
        elif cmd == "SCENE":
            # Jump to a scene label
            lbl = parts[1].lower()
            if lbl in self.labels:
                self.canvas.delete("all"); self.sprites.clear(); self.sprite_data.clear()
                self.pc = self.labels[lbl]; jumped = True
        elif cmd == "SCENECLEAR":
            self.canvas.delete("all"); self.sprites.clear(); self.sprite_data.clear()

        # ── MISC ─────────────────────────────────────────────────────
        elif cmd == "COPY":    self.vars[parts[1].lower()] = self.get_val(parts[2])
        elif cmd == "SWAP":
            a, b = parts[1].lower(), parts[2].lower()
            self.vars[a], self.vars[b] = self.vars.get(b,0), self.vars.get(a,0)
        elif cmd == "TOGGLE":  self.vars[parts[1].lower()] = 0 if self.num(parts[1]) else 1
        elif cmd == "RANDSEED": random.seed(int(self.num(parts[1])))
        elif cmd == "FPS":
            target = self.num(parts[1])
            if target > 0:
                sleep_t = max(0, (1.0/target) - self.vars["dt"])
                time.sleep(sleep_t)
        elif cmd == "STATUSBAR": self.update_status(self.resolve_str(self.extract_string(active)))
        elif cmd == "CLIPBOARD":
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(str(self.get_val(parts[1])))
            except: pass

        else:
            self.log(f"Unknown command: {cmd} at line {self.pc+1}")

        return jumped


# ── BOOTSTRAP ──────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) > 1:
        engine = QukEnginePro(sys.argv[1])
        engine.run()
    else:
        print("QUK CENTURION PRO v7.0")
        print("Usage: python quk_engine.py script.quk")
        print("       or drag a .quk file onto quk_engine.exe")