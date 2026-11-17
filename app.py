import ctypes, io, math, os, queue, random, struct, sys, threading, time, wave
import tkinter as tk
if sys.platform == "win32":
    try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception: pass
    try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SlidesHost.Controller")  # taskbar shows OUR icon, not python.exe's
    except Exception: pass
import customtkinter as ctk, mss, qrcode
from PIL import Image, ImageTk, ImageFilter
from server import Hub, DATA

U = ctypes.windll.user32 if sys.platform == "win32" else None
if U:
    U.GetForegroundWindow.restype = ctypes.c_void_p
    U.LoadImageW.restype = ctypes.c_void_p
    U.LoadImageW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    U.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p]
PAGE_APPS = ("winword", "acrord32", "acrobat", "sumatrapdf", "foxitpdfreader", "chrome", "msedge", "firefox")
ACCENT, KEY = "#6366f1", "#010101"
HERE = os.path.dirname(os.path.abspath(__file__)); ICO = os.path.join(HERE, "logo.ico")
def set_icon(w):  # load the exact-size icon for this screen's DPI so the title bar / taskbar icon stays sharp
    if sys.platform != "win32": return
    def go():
        try:
            hwnd = U.GetParent(w.winfo_id()) or w.winfo_id(); dpi = U.GetDpiForWindow(hwnd) or 96
            for kind, metric in ((0, 49), (1, 11)):   # ICON_SMALL/SM_CXSMICON, ICON_BIG/SM_CXICON
                sz = ctypes.windll.user32.GetSystemMetricsForDpi(metric, dpi)
                U.SendMessageW(hwnd, 0x80, kind, U.LoadImageW(None, ICO, 1, sz, sz, 0x10))
        except Exception:
            try: w.iconbitmap(ICO)
            except Exception: pass
    w.after(500, go)

def pid_of(h):
    p = ctypes.c_ulong(); U.GetWindowThreadProcessId(ctypes.c_void_p(h), ctypes.byref(p)); return p.value

def pname(h):
    k = ctypes.windll.kernel32; ph = k.OpenProcess(0x1000, False, pid_of(h))
    buf, n = ctypes.create_unicode_buffer(260), ctypes.c_ulong(260)
    k.QueryFullProcessImageNameW(ph, 0, buf, ctypes.byref(n)); k.CloseHandle(ph)
    return os.path.basename(buf.value).lower().rsplit(".", 1)[0]

_tl = threading.local()
def grab_jpeg():
    s = getattr(_tl, "s", None) or mss.mss(); _tl.s = s
    im = s.grab(s.monitors[1]); img = Image.frombytes("RGB", im.size, im.bgra, "raw", "BGRX")
    img.thumbnail((960, 960)); b = io.BytesIO(); img.save(b, "JPEG", quality=55); return b.getvalue()

def make_wav(path):  # thud + high feedback squeal, soft-clipped for perceived loudness
    sr = 44100; f = wave.open(path, "wb"); f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr); out = bytearray()
    for i in range(int(sr * 2.2)):
        t = i / sr
        v = math.sin(2 * math.pi * 55 * t) * math.exp(-t * 9) + random.uniform(-1, 1) * math.exp(-t * 60) * .8
        if t > .3:
            a = min(1, (t - .3) * 3) * math.exp(-(t - .3) * 1.2)
            v += a * .6 * (math.sin(2 * math.pi * 3100 * t) + .5 * math.sin(2 * math.pi * 6200 * t))
        out += struct.pack("<h", int(math.tanh(v * 3) * 32000))
    f.writeframes(bytes(out)); f.close()

class Overlay(tk.Toplevel):
    """Click-through transparent layer: laser, sketches and zoomed snapshot, drawn over the presentation."""
    def __init__(self, master):
        super().__init__(master); self.overrideredirect(True); self.attributes("-topmost", True)
        self.attributes("-transparentcolor", KEY)
        self.cv = tk.Canvas(self, bg=KEY, highlightthickness=0); self.cv.pack(fill="both", expand=True)
        self.strokes, self.redo, self.cur, self.zoom, self.cx, self.cy, self.snap, self.img = [], [], None, 1, .5, .5, None, None
        with mss.mss() as s: self.m = s.monitors[1]
        self.W, self.H = self.m["width"], self.m["height"]
        self.bimg, self.cp, self.ct, self.anim = None, 0.0, 0.0, False   # blur image, curtain progress/target/animating
        self.clogo = ImageTk.PhotoImage(Image.open(os.path.join(HERE, "web", "logo.png")).resize((160, 160)))
        self.geometry(f"{self.W}x{self.H}+{self.m['left']}+{self.m['top']}"); self.update_idletasks()
        if U:
            h = U.GetParent(self.winfo_id()) or self.winfo_id()
            U.SetWindowLongW(h, -20, U.GetWindowLongW(h, -20) | 0x80000 | 0x20 | 0x80 | 0x8000000)

    def view(self):
        w = 1 / self.zoom
        return min(max(self.cx - w / 2, 0), 1 - w), min(max(self.cy - w / 2, 0), 1 - w), w
    def px(self, p):
        x0, y0, w = self.view(); return (p[0] - x0) / w * self.W, (p[1] - y0) / w * self.H
    def seg(self, col, pts):
        self.cv.create_line(*[v for p in pts for v in self.px(p)], fill=col, width=5, capstyle="round", joinstyle="round"); self.cv.tag_raise("curtain")
    def render(self):
        self.cv.delete("all")
        if self.snap:
            x0, y0, w = self.view(); W, H = self.W, self.H
            self.img = ImageTk.PhotoImage(self.snap.crop((int(x0 * W), int(y0 * H), int((x0 + w) * W), int((y0 + w) * H))).resize((W, H)))
            self.cv.create_image(0, 0, image=self.img, anchor="nw")
        elif self.bimg: self.cv.create_image(0, 0, image=self.bimg, anchor="nw")
        for col, pts in self.strokes: self.seg(col, pts)
        self.draw_curtain()
    def reset(self, hard=False):
        self.strokes, self.redo, self.cur, self.zoom, self.snap, self.bimg = [], [], None, 1, None, None
        if hard: self.cp = self.ct = 0.0
        self.render()
    def shot(self):
        self.cv.delete("all"); self.withdraw(); self.update(); time.sleep(.15)
        with mss.mss() as s: im = s.grab(self.m)
        self.deiconify(); return Image.frombytes("RGB", im.size, im.bgra, "raw", "BGRX")
    def take_snapshot(self): self.snap = self.shot()
    def blur_on(self):  # blurred, frozen copy of the screen shown over the slide
        sm = self.shot().resize((self.W // 4, self.H // 4)).filter(ImageFilter.GaussianBlur(5))
        self.bimg = ImageTk.PhotoImage(sm.resize((self.W, self.H), Image.BILINEAR)); self.render()
    def roll(self, down):  # curtain rolls down from the top / back up
        self.ct = 1.0 if down else 0.0
        if not self.anim: self.anim = True; self.step()
    def step(self):
        d = self.ct - self.cp; v = 0.008 + 0.022 * math.sin(math.pi * self.cp)
        if abs(d) <= v: self.cp, self.anim = self.ct, False
        else: self.cp += v if d > 0 else -v; self.after(14, self.step)
        self.draw_curtain()
    def draw_curtain(self):  # red velvet stage curtains closing from both sides, gold edges, pleats gather as they open
        c = self.cv; c.delete("curtain")
        if self.cp <= 0: return
        W, H = self.W, self.H; pw = self.cp * W / 2; n, k = 12, 4
        for side in (0, 1):
            for s in range(n * k):
                x0, x1 = pw * s / (n * k), pw * (s + 1) / (n * k)
                b = 0.5 + 0.5 * math.cos(2 * math.pi * s / k)
                col = "#%02x%02x%02x" % (int(70 + 125 * b), int(6 + 18 * b), int(16 + 30 * b))
                if side: x0, x1 = W - x1, W - x0
                c.create_rectangle(x0, 0, x1 + 1, H, fill=col, outline="", tags="curtain")
            gx = pw - 6 if side == 0 else W - pw
            c.create_rectangle(gx, 0, gx + 6, H, fill="#d4a017", outline="", tags="curtain")
        if self.cp >= 1: c.create_image(W // 2, H // 2, image=self.clogo, tags="curtain")

    def cmd(self, d):
        t = d["type"]
        if t == "laser":
            self.cv.delete("laser")
            if d.get("on"):
                x, y = self.px((d["x"], d["y"])); r = 14
                self.cv.create_oval(x - r, y - r, x + r, y + r, fill="#ff2a2a", outline="#ffd0d0", width=3, tags="laser")
        elif t == "stroke":
            ph = d["phase"]; p = (d.get("x", 0), d.get("y", 0))   # "end" carries no coordinates
            if ph == "start": self.cur = ("#ff2a2a", [p, p]); self.strokes.append(self.cur); self.redo.clear(); self.render()
            elif ph == "move" and self.cur:
                self.cur[1].append(p)
                if self.snap: self.render()
                else: self.seg(self.cur[0], self.cur[1][-2:])
            else: self.cur = None
        elif t == "blur":
            if d.get("on"): self.blur_on()
            else: self.bimg = None; self.render()
        elif t == "curtain": self.roll(bool(d.get("on")))
        elif t == "undo" and self.strokes: self.redo.append(self.strokes.pop()); self.render()
        elif t == "redo" and self.redo: self.strokes.append(self.redo.pop()); self.render()
        elif t == "clear": self.strokes.clear(); self.redo.clear(); self.cur = None; self.render()
        elif t in ("zoom", "resetzoom"):
            z = 1 if t == "resetzoom" else max(1, min(5, float(d["zoom"])))
            if z > 1 and not self.snap: self.take_snapshot()
            self.zoom = z; self.cx, self.cy = d.get("cx", .5), d.get("cy", .5)
            if z == 1: self.snap = None
            self.render()

class App(ctk.CTk):
    def __init__(self):
        super().__init__(); self.title("SlidesHost"); self.geometry("900x540"); self.resizable(False, False)
        set_icon(self)
        ctk.set_appearance_mode("system"); self.q, self.sel, self.target, self.last_mic, self.last_url = queue.Queue(), None, None, 0, None
        self.hub = Hub(lambda: self.q.put(("refresh",)), lambda n, cb: self.q.put(("ask", n, cb)), lambda d: self.q.put(("cmd", d)))
        self.hub.grab = grab_jpeg; self.ov = Overlay(self)
        _li = Image.open(os.path.join(HERE, "web", "logo.png")); self.logo, self.logo_s = ctk.CTkImage(_li, size=(64, 64)), ctk.CTkImage(_li, size=(32, 32))
        self.grid_columnconfigure(0, weight=3); self.grid_columnconfigure(1, weight=2); self.grid_rowconfigure(0, weight=1)
        L = ctk.CTkFrame(self, corner_radius=16); L.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")
        t = ctk.CTkFrame(L, fg_color="transparent"); t.pack(anchor="w", padx=22, pady=(20, 0))
        ctk.CTkLabel(t, text="", image=self.logo_s).pack(side="left")
        ctk.CTkLabel(t, text="  Phones", font=("Segoe UI", 22, "bold")).pack(side="left")
        ctk.CTkLabel(L, text="Phones that have scanned the QR code", text_color="gray").pack(anchor="w", padx=22)
        self.list = ctk.CTkScrollableFrame(L, fg_color="transparent"); self.list.pack(fill="both", expand=True, padx=12, pady=10)
        row = ctk.CTkFrame(L, fg_color="transparent"); row.pack(fill="x", padx=16, pady=(0, 18))
        ctk.CTkButton(row, text="Use as controller", fg_color=ACCENT, command=self.use).pack(side="left", padx=4)
        for txt, cmd in (("Rename", self.rename), ("Forget", self.forget)):
            ctk.CTkButton(row, text=txt, fg_color="transparent", border_width=1, text_color=("gray10", "gray90"), command=cmd, width=84).pack(side="left", padx=4)
        R = ctk.CTkFrame(self, corner_radius=16); R.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")
        ctk.CTkLabel(R, text="", image=self.logo).pack(pady=(18, 0))
        ctk.CTkLabel(R, text="Connect a phone", font=("Segoe UI", 22, "bold")).pack(pady=(6, 4))
        ctk.CTkLabel(R, text="Scan with your phone camera\n(same WiFi)", text_color="gray").pack()
        self.qr = ctk.CTkLabel(R, text=""); self.qr.pack(pady=14)
        ctk.CTkButton(R, text="New QR code", fg_color="transparent", border_width=1, text_color=("gray10", "gray90"), command=self.new_qr).pack()
        self.hub.start(); self.refresh(); self.after(15, self.pump)

    def new_qr(self): self.hub.token = None; self.refresh()
    def refresh(self):
        h = self.hub
        if not h.token or time.time() > h.token_exp: h.new_token()
        url = h.url()
        if url != self.last_url:
            self.last_url = url; self.qrimg = ctk.CTkImage(qrcode.make(url).convert("RGB"), size=(210, 210)); self.qr.configure(image=self.qrimg)
        for w in self.list.winfo_children(): w.destroy()
        for did, dev in h.db["devices"].items():
            tag = ("  ·  Controlling" if did == h.active else "") + ("  ·  Default" if did == h.db["default"] else "")
            ctk.CTkButton(self.list, anchor="w", height=44, corner_radius=10, text=f"{'●' if did in h.online else '○'}  {dev['name']}{tag}",
                          fg_color=ACCENT if did == self.sel else "transparent", text_color=("white" if did == self.sel else ("gray10", "gray90")),
                          hover_color=("gray85", "gray25"), command=lambda d=did: self.select(d)).pack(fill="x", pady=2)
    def select(self, did): self.sel = did; self.refresh()
    def use(self):
        if self.sel: self.hub.set_active(self.sel)
    def default(self):
        if self.sel: self.hub.db["default"] = None if self.hub.db["default"] == self.sel else self.sel; self.hub.save(); self.refresh()
    def rename(self):
        if self.sel:
            n = ctk.CTkInputDialog(text="New name for this phone:", title="Rename phone").get_input()
            if n: self.hub.rename(self.sel, n)
    def forget(self):
        if self.sel: self.hub.forget(self.sel); self.sel = None

    def ask(self, name, cb):
        done = []
        def fin(ok):
            if not done: done.append(1); cb(ok); d.destroy()
        d = ctk.CTkToplevel(self); d.title("New phone"); d.transient(self); set_icon(d); d.resizable(False, False)   # small fixed dialog, never maximised or fullscreen
        d.geometry(f"360x240+{self.winfo_x() + (self.winfo_width() - 360) // 2}+{self.winfo_y() + (self.winfo_height() - 240) // 2}")
        ctk.CTkLabel(d, text="", image=self.logo).pack(pady=(14, 0))
        ctk.CTkLabel(d, text=f"Allow “{name}” to control\nyour presentations?", font=("Segoe UI", 15)).pack(pady=(6, 12))
        f = ctk.CTkFrame(d, fg_color="transparent"); f.pack()
        ctk.CTkButton(f, text="Allow", fg_color=ACCENT, command=lambda: fin(True)).pack(side="left", padx=6)
        ctk.CTkButton(f, text="Deny", fg_color="gray40", command=lambda: fin(False)).pack(side="left", padx=6)
        d.protocol("WM_DELETE_WINDOW", lambda: fin(False))

    def pump(self):
        try:
            while True:
                m = self.q.get_nowait()
                try:
                    if m[0] == "refresh": self.refresh()
                    elif m[0] == "ask": self.ask(m[1], m[2])
                    else: self.cmd(m[1])
                except Exception:   # one bad command must never freeze the app
                    import traceback; traceback.print_exc()
        except queue.Empty: pass
        if U:
            h = U.GetForegroundWindow()
            if h and pid_of(h) != os.getpid(): self.target = h
        if time.time() > self.hub.token_exp: self.refresh()
        self.after(15, self.pump)

    def cmd(self, d):
        t = d["type"]
        if t in ("next", "prev"): self.nav(1 if t == "next" else -1)
        elif t == "micdrop": self.mic()
        elif t == "start": self.start()
        elif t == "stop": self.stop()
        else: self.ov.cmd(d)

    def nav(self, d):  # PowerPoint/others: arrows; Word/PDF/browsers: Page Up/Down
        if not U: return
        if self.target and pid_of(U.GetForegroundWindow()) == os.getpid():
            U.SetForegroundWindow(ctypes.c_void_p(self.target)); time.sleep(.08)
        page = bool(self.target) and pname(self.target) in PAGE_APPS
        vk = (0x22 if page else 0x27) if d > 0 else (0x21 if page else 0x25)
        for f in (1, 3): U.keybd_event(vk, 0, f, 0)
        self.ov.reset()

    def start(self):  # F5 (PowerPoint/Impress), Ctrl+L (Acrobat), F11 (browsers)
        if not U: return
        if self.target and pid_of(U.GetForegroundWindow()) == os.getpid():
            U.SetForegroundWindow(ctypes.c_void_p(self.target)); time.sleep(.08)
        pn = pname(self.target) if self.target else ""; vk = 0x7A if pn in ("chrome", "msedge", "firefox") else 0x74
        seq = [(0x11, 0), (0x4C, 0), (0x4C, 2), (0x11, 2)] if pn in ("acrord32", "acrobat") else [(vk, 0), (vk, 2)]
        for k, f in seq: U.keybd_event(k, 0, f, 0)
        self.ov.reset(hard=True)

    def stop(self):  # end the slideshow (Esc) and clear every overlay effect
        if not U: return
        if self.target and pid_of(U.GetForegroundWindow()) == os.getpid():
            U.SetForegroundWindow(ctypes.c_void_p(self.target)); time.sleep(.08)
        for f in (0, 2): U.keybd_event(0x1B, 0, f, 0)
        self.ov.reset(hard=True)

    def mic(self):
        if time.time() - self.last_mic < 4 or sys.platform != "win32": return
        self.last_mic = time.time(); import winsound
        p = os.path.join(DATA, "micdrop.wav")
        if not os.path.exists(p): make_wav(p)
        winsound.PlaySound(p, winsound.SND_FILENAME | winsound.SND_ASYNC)

if __name__ == "__main__":
    App().mainloop()
