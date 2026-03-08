import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageEnhance, ImageDraw, ImageFont, ImageFilter
import numpy as np
import threading
import os
import json


CHARS = {
    "Standard": list(' .\'`^",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$'),
    "Dense":    list('@#S%?*+;:,. '),
    "Sparse":   list(' .-:=+*#%@'),
    "Blocks":   list(' ░▒▓█'),
    "Braille":  list(' ⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏⠐⠑⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟⠠⠡⠢⠣⠤⠥⠦⠧⠨⠩⠪⠫⠬⠭⠮⠯⠰⠱⠲⠳⠴⠵⠶⠷⠸⠹⠺⠻⠼⠽⠾⠿'),
    "Minimal":  list(' :. #'),
}

HALF_BLOCK = "▀"

BG   = '#0d0d0d'
PANEL= '#141414'
CARD = '#1a1a1a'
BORDER='#2a2a2a'
FG   = '#e8e8e8'
DIM  = '#666666'
GREEN= '#00ff88'
CYAN = '#00ccff'
BTN  = '#1e1e1e'
INBG = '#111111'


def to_hex(r, g, b):
    return f'#{int(r):02x}{int(g):02x}{int(b):02x}'


def extract_gif_frames(gif):
    frames = []
    bg = Image.new('RGBA', gif.size, (0, 0, 0, 255))
    i = 0
    while True:
        try:
            gif.seek(i)
        except EOFError:
            break
        frame = gif.copy().convert('RGBA')
        dur = gif.info.get('duration', 100) or 100
        comp = bg.copy()
        comp.paste(frame, (0, 0), frame)
        frames.append((comp.convert('RGB'), dur))
        disposal = getattr(gif, 'disposal_method', 0)
        bg = Image.new('RGBA', gif.size, (0, 0, 0, 255)) if disposal == 2 else comp
        i += 1
    return frames


def px_to_char(val, chars):
    idx = int(val / 255 * (len(chars) - 1))
    return chars[max(0, min(idx, len(chars) - 1))]


def floyd_steinberg(px):
    arr = px.astype(float)
    h, w = arr.shape
    for y in range(h):
        for x in range(w):
            old = arr[y, x]
            new = round(old / 255) * 255
            arr[y, x] = new
            err = old - new
            if x+1 < w:           arr[y, x+1]   += err * 7/16
            if y+1 < h:
                if x-1 >= 0:      arr[y+1, x-1] += err * 3/16
                arr[y+1, x]       += err * 5/16
                if x+1 < w:       arr[y+1, x+1] += err * 1/16
    return np.clip(arr, 0, 255).astype(np.uint8)


def convert_frame(img, mode, width, chars, brightness, contrast, saturation, invert, dither, edge, prog_cb=None):
    img = img.copy()

    if saturation != 1.0:
        img = ImageEnhance.Color(img.convert('RGB')).enhance(saturation)

    aspect = img.size[1] / img.size[0]

    if mode == 'halfblock':
        raw_h = max(2, int(width * aspect))
        if raw_h % 2: raw_h += 1
        img = img.resize((width, raw_h), Image.Resampling.LANCZOS).convert('RGB')
        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Contrast(img).enhance(contrast)
        px = np.array(img)
        if invert: px = 255 - px
        rows = []
        total = raw_h // 2
        for i in range(0, raw_h - 1, 2):
            row = [(HALF_BLOCK, to_hex(*px[i][j]), to_hex(*px[i+1][j])) for j in range(width)]
            rows.append(row)
            if prog_cb: prog_cb(int((i//2+1)/total*100))
        return rows

    h = max(1, int(width * aspect * 0.55))
    img = img.resize((width, h), Image.Resampling.LANCZOS)

    edge_filters = {'soft': ImageFilter.SMOOTH, 'hard': ImageFilter.SHARPEN, 'find': ImageFilter.FIND_EDGES}
    if edge in edge_filters:
        img = img.filter(edge_filters[edge])

    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Contrast(img).enhance(contrast)

    if mode == 'grayscale':
        img = img.convert('L')
        px = np.array(img)
        if invert: px = 255 - px
        if dither: px = floyd_steinberg(px)
        rows = []
        for i, row in enumerate(px):
            rows.append(''.join(px_to_char(p, chars) for p in row))
            if prog_cb and (i % 5 == 0 or i == len(px)-1):
                prog_cb(int((i+1)/len(px)*100))
        return rows

    # color mode
    img = img.convert('RGB')
    gray = img.convert('L')
    gray = ImageEnhance.Contrast(gray).enhance(1.0)  # already done above but gray needs separate pass
    cpx = np.array(img)
    gpx = np.array(gray)
    if invert:
        cpx = 255 - cpx
        gpx = 255 - gpx
    rows = []
    for i, (grow, crow) in enumerate(zip(gpx, cpx)):
        rows.append([(px_to_char(g, chars), to_hex(*c)) for g, c in zip(grow, crow)])
        if prog_cb and (i % 5 == 0 or i == len(gpx)-1):
            prog_cb(int((i+1)/len(gpx)*100))
    return rows


def frame_to_html(rows, mode):
    lines = []
    def esc(c): return c.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    if mode == 'grayscale':
        for row in rows: lines.append(esc(row))
    elif mode == 'color':
        for row in rows:
            lines.append(''.join(f'<span style="color:{col}">{esc(ch)}</span>' for ch, col in row))
    elif mode == 'halfblock':
        for row in rows:
            lines.append(''.join(f'<span style="color:{fg};background:{bg}">{HALF_BLOCK}</span>' for _, fg, bg in row))
    return '\n'.join(lines)


def make_static_html(rows, mode, fontsize=10, bg='#000000'):
    body = frame_to_html(rows, mode)
    return f'''<!DOCTYPE html><html><head><meta charset="utf-8"><title>ASCII Art</title>
<style>body{{background:{bg};margin:0;padding:16px}}
pre{{font-family:"Courier New",monospace;font-size:{fontsize}px;line-height:1.2;margin:0}}
span{{display:inline}}</style></head><body><pre>{body}</pre></body></html>'''


def make_animated_html(all_rows, durations, mode, fontsize=10, bg='#000000'):
    fdata = json.dumps([frame_to_html(r, mode) for r in all_rows])
    ddata = json.dumps(durations)
    return f'''<!DOCTYPE html><html><head><meta charset="utf-8"><title>ASCII GIF</title>
<style>
body{{background:{bg};margin:0;padding:16px;user-select:none}}
pre{{font-family:"Courier New",monospace;font-size:{fontsize}px;line-height:1.2;margin:0;white-space:pre}}
span{{display:inline}}
#bar{{position:fixed;bottom:10px;left:50%;transform:translateX(-50%);
      background:rgba(0,0,0,.8);border-radius:8px;padding:6px 14px;
      display:flex;gap:10px;align-items:center;color:#00ff88;font-family:monospace;font-size:13px}}
button{{background:#1e1e1e;color:#00ff88;border:1px solid #333;border-radius:4px;
        padding:2px 9px;cursor:pointer;font-size:13px}}
button:hover{{background:#2a2a2a}}
input[type=range]{{accent-color:#00ff88}}
</style></head><body>
<pre id="out"></pre>
<div id="bar">
  <button id="btn">⏸</button>
  frame <input type="range" id="scrub" min="0" value="0" style="width:150px">
  <span id="info">1/1</span>
  speed <input type="range" id="spd" min="10" max="400" value="100" style="width:80px">
  <span id="sl">100%</span>
</div>
<script>
const frames={fdata}, dur={ddata};
const out=document.getElementById('out'), btn=document.getElementById('btn'),
      scrub=document.getElementById('scrub'), info=document.getElementById('info'),
      spd=document.getElementById('spd'), sl=document.getElementById('sl');
scrub.max=frames.length-1;
let idx=0, playing=true, t=null;
const show=i=>{{ out.innerHTML=frames[i]; scrub.value=i; info.textContent=(i+1)+'/'+frames.length; }};
const next=()=>{{ idx=(idx+1)%frames.length; show(idx); t=setTimeout(next, Math.max(16, dur[idx]*(100/+spd.value))); }};
btn.onclick=()=>{{ playing=!playing; btn.textContent=playing?'⏸':'▶'; playing?next():clearTimeout(t); }};
scrub.oninput=()=>{{ clearTimeout(t); idx=+scrub.value; show(idx); if(playing) next(); }};
spd.oninput=()=>sl.textContent=spd.value+'%';
show(0); next();
</script></body></html>'''


def rows_to_image(rows, mode, fnt, cw, ch):
    ncols = max((len(r) for r in rows), default=1)
    img = Image.new('RGB', (ncols * cw, len(rows) * ch), 'black')
    draw = ImageDraw.Draw(img)
    if mode == 'grayscale':
        for ri, row in enumerate(rows):
            draw.text((0, ri*ch), row, font=fnt, fill='white')
    elif mode == 'color':
        for ri, row in enumerate(rows):
            x = 0
            for ch_, col in row:
                draw.text((x, ri*ch), ch_, font=fnt, fill=col); x += cw
    elif mode == 'halfblock':
        for ri, row in enumerate(rows):
            x = 0
            for _, fg, bg in row:
                draw.rectangle([x, ri*ch, x+cw-1, ri*ch+ch-1], fill=bg)
                draw.text((x, ri*ch), HALF_BLOCK, font=fnt, fill=fg); x += cw
    return img


class App:
    def __init__(self, root):
        self.root = root
        root.title("ASCII Art Converter")
        root.geometry("1400x880")
        root.minsize(1000, 650)
        root.configure(bg=BG)

        # image state
        self.img = None           # current PIL image (first frame for GIFs)
        self.img_path = None
        self.result = None        # (mode, rows) for static images

        # gif state
        self.is_gif = False
        self.gif_frames = []      # list of (PIL img, duration ms)
        self.gif_converted = []   # list of rows per frame
        self.gif_durations = []
        self.gif_mode = 'color'
        self.playing = False
        self.anim_idx = 0
        self.anim_job = None
        self.gif_thumb_photos = []
        self.gif_thumb_job = None
        self.gif_thumb_idx = 0

        self.converting = False
        self.tags = set()

        # vars
        self.v_width      = tk.IntVar(value=120)
        self.v_bright     = tk.DoubleVar(value=1.0)
        self.v_contrast   = tk.DoubleVar(value=1.1)
        self.v_sat        = tk.DoubleVar(value=1.2)
        self.v_invert     = tk.BooleanVar(value=False)
        self.v_dither     = tk.BooleanVar(value=False)
        self.v_live       = tk.BooleanVar(value=False)
        self.v_loop       = tk.BooleanVar(value=True)
        self.v_charset    = tk.StringVar(value="Standard")
        self.v_mode       = tk.StringVar(value="color")
        self.v_edge       = tk.StringVar(value="off")
        self.v_fontsize   = tk.IntVar(value=9)
        self.v_custom     = tk.StringVar(value="")
        self.v_progress   = tk.IntVar(value=0)
        self.v_status     = tk.StringVar(value="Load an image or GIF to get started")
        self.v_speed      = tk.IntVar(value=100)
        self.v_frame      = tk.IntVar(value=0)

        self._style()
        self._ui()
        self._shortcuts()

    def _style(self):
        s = ttk.Style()
        s.theme_use('default')
        s.configure('TFrame', background=BG)
        s.configure('TLabel', background=CARD, foreground=FG, font=('Consolas', 9))
        s.configure('TCheckbutton', background=CARD, foreground=FG, font=('Consolas', 9))
        s.map('TCheckbutton', background=[('active', CARD)], foreground=[('active', GREEN)])
        s.configure('TCombobox', fieldbackground=INBG, background=INBG,
                    foreground=FG, selectbackground=GREEN, font=('Consolas', 9))
        s.configure('Go.TButton', background=GREEN, foreground='#000',
                    font=('Consolas', 9, 'bold'), padding=(10, 6))
        s.map('Go.TButton', background=[('active', CYAN), ('disabled', BTN)])
        s.configure('TButton', background=BTN, foreground=FG, font=('Consolas', 9), padding=(8, 5))
        s.map('TButton', background=[('active', '#2a2a2a'), ('disabled', BORDER)])
        s.configure('TProgressbar', troughcolor=BORDER, background=GREEN, thickness=4)
        s.configure('TRadiobutton', background=CARD, foreground=FG, font=('Consolas', 9))
        s.map('TRadiobutton', background=[('active', CARD)], foreground=[('active', GREEN)])
        s.configure('TSpinbox', background=INBG, fieldbackground=INBG,
                    foreground=FG, font=('Consolas', 9))

    def _ui(self):
        self._header()
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))
        self._sidebar(body)
        self._output(body)
        self._statusbar()

    def _header(self):
        h = tk.Frame(self.root, bg=PANEL, height=50)
        h.pack(fill=tk.X)
        h.pack_propagate(False)
        tk.Label(h, text="▓▒░ ASCII CONVERTER ░▒▓", bg=PANEL, fg=GREEN,
                 font=('Consolas', 12, 'bold')).pack(side=tk.LEFT, padx=14)
        actions = [
            ("↺ Reset",        self.reset,          'TButton'),
            ("🖼 PNG",          self.export_png,     'TButton'),
            ("🌐 HTML",         self.export_html,    'TButton'),
            ("💾 Save",         self.save_txt,       'TButton'),
            ("⎘ Copy",          self.copy,           'TButton'),
            ("▶ Convert",       self.convert,        'TButton'),
            ("⬆ Load",          self.load,           'Go.TButton'),
        ]
        for lbl, cmd, sty in actions:
            ttk.Button(h, text=lbl, command=cmd, style=sty).pack(side=tk.RIGHT, padx=3, pady=8)

    def _sidebar(self, parent):
        sb = tk.Frame(parent, bg=BG, width=265)
        sb.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        sb.pack_propagate(False)

        # preview box
        pf = tk.LabelFrame(sb, text=" Preview ", bg=CARD, fg=CYAN,
                           font=('Consolas', 9, 'bold'), bd=1, relief='flat', labelanchor='n')
        pf.pack(fill=tk.X, pady=(4,2), padx=2)
        self.preview = tk.Label(pf, bg=CARD, fg=DIM, font=('Consolas', 9),
                                text="no image loaded", width=27, height=9, anchor='center')
        self.preview.pack(padx=4, pady=4)
        self.info_lbl = tk.Label(sb, text="", bg=BG, fg=DIM, font=('Consolas', 8))
        self.info_lbl.pack()

        self._divider(sb, "RENDER MODE")
        mf = tk.Frame(sb, bg=CARD)
        mf.pack(fill=tk.X, padx=2, pady=1)
        for text, val in [("🎨 Color", "color"), ("◐ Half-Block HD", "halfblock"), ("▓ Grayscale", "grayscale")]:
            ttk.Radiobutton(mf, text=text, variable=self.v_mode,
                            value=val, command=self._live).pack(anchor='w', padx=8, pady=2)
        tk.Label(mf, text="Half-block uses ▀ — doubles vertical resolution.",
                 bg=CARD, fg=DIM, font=('Consolas', 7), justify='left').pack(anchor='w', padx=8, pady=(0,4))

        self._divider(sb, "CHARACTERS")
        cf = tk.Frame(sb, bg=CARD)
        cf.pack(fill=tk.X, padx=2, pady=1)
        self.charset_box = ttk.Combobox(cf, values=list(CHARS.keys()),
                                        textvariable=self.v_charset, state='readonly', width=22)
        self.charset_box.pack(padx=8, pady=(6,2))
        self.charset_box.bind("<<ComboboxSelected>>", self._live)
        tk.Label(cf, text="custom (leave blank to use set above):",
                 bg=CARD, fg=DIM, font=('Consolas', 7)).pack(anchor='w', padx=8)
        tk.Entry(cf, textvariable=self.v_custom, bg=INBG, fg=FG,
                 insertbackground=FG, font=('Consolas', 9), width=24,
                 relief='flat').pack(padx=8, pady=(0,6))

        self._divider(sb, "ADJUSTMENTS")
        af = tk.Frame(sb, bg=CARD)
        af.pack(fill=tk.X, padx=2, pady=1)
        self._slider(af, "Width",      self.v_width,    20,  300, True)
        self._slider(af, "Brightness", self.v_bright,   0.1, 3.0)
        self._slider(af, "Contrast",   self.v_contrast, 0.1, 3.0)
        self._slider(af, "Saturation", self.v_sat,      0.0, 3.0)

        self._divider(sb, "OPTIONS")
        of = tk.Frame(sb, bg=CARD)
        of.pack(fill=tk.X, padx=2, pady=1)
        ttk.Checkbutton(of, text="Invert",        variable=self.v_invert, command=self._live).pack(anchor='w', padx=8, pady=2)
        ttk.Checkbutton(of, text="Dither (F-S)",  variable=self.v_dither, command=self._live).pack(anchor='w', padx=8, pady=2)
        ttk.Checkbutton(of, text="Live Preview",  variable=self.v_live).pack(anchor='w', padx=8, pady=2)

        tk.Label(of, text="Edge:", bg=CARD, fg=DIM, font=('Consolas', 8)).pack(anchor='w', padx=8, pady=(4,0))
        ec = ttk.Combobox(of, values=['off','soft','hard','find'],
                          textvariable=self.v_edge, state='readonly', width=14)
        ec.pack(padx=8, pady=(0,4))
        ec.bind("<<ComboboxSelected>>", self._live)

        tk.Label(of, text="Font size:", bg=CARD, fg=DIM, font=('Consolas', 8)).pack(anchor='w', padx=8)
        sp = ttk.Spinbox(of, from_=5, to=24, increment=1, textvariable=self.v_fontsize,
                         width=6, command=self._apply_fontsize)
        sp.pack(anchor='w', padx=8, pady=(0,6))
        sp.bind('<Return>', lambda e: self._apply_fontsize())

    def _output(self, parent):
        right = tk.Frame(parent, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # tiny toolbar
        tb = tk.Frame(right, bg=BG, height=28)
        tb.pack(fill=tk.X)
        tb.pack_propagate(False)
        tk.Label(tb, text="OUTPUT", bg=BG, fg=DIM, font=('Consolas', 8)).pack(side=tk.LEFT, padx=6)
        for sym, d in [("−",-1),("+",1)]:
            tk.Button(tb, text=f" {sym} ", bg=BTN, fg=FG, font=('Consolas', 10, 'bold'),
                      relief='flat', bd=0, activebackground='#2a2a2a', activeforeground=GREEN,
                      command=lambda delta=d: self._zoom(delta)).pack(side=tk.RIGHT, padx=1)
        tk.Label(tb, text="zoom:", bg=BG, fg=DIM, font=('Consolas', 8)).pack(side=tk.RIGHT, padx=(0,4))

        # gif controls — hidden until needed
        self.gif_bar = tk.Frame(right, bg=PANEL)
        self._gif_controls(self.gif_bar)

        self.out = tk.Text(right, wrap=tk.NONE,
                           font=('Courier New', self.v_fontsize.get()),
                           bg=INBG, fg=FG, insertbackground=FG,
                           selectbackground=GREEN, selectforeground='#000',
                           relief='flat', bd=4, cursor='arrow')
        self.out.pack(fill=tk.BOTH, expand=True, pady=(2,0))

        ys = ttk.Scrollbar(right, orient='vertical',   command=self.out.yview)
        xs = ttk.Scrollbar(right, orient='horizontal', command=self.out.xview)
        self.out.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        ys.place(relx=1.0, rely=0,   relheight=1.0, anchor='ne')
        xs.place(relx=0,   rely=1.0, relwidth=1.0,  anchor='sw')

    def _gif_controls(self, bar):
        self.play_btn = tk.Button(bar, text="⏸ Pause", bg=BTN, fg=GREEN,
                                  font=('Consolas', 9, 'bold'), relief='flat', bd=0,
                                  activebackground='#2a2a2a', activeforeground=GREEN,
                                  command=self.toggle_play, width=9)
        self.play_btn.pack(side=tk.LEFT, padx=(8,4), pady=4)

        tk.Button(bar, text="⏹", bg=BTN, fg=DIM, font=('Consolas', 9),
                  relief='flat', bd=0, activebackground='#2a2a2a',
                  command=self.stop_gif).pack(side=tk.LEFT, padx=2, pady=4)

        tk.Label(bar, text="frame:", bg=PANEL, fg=DIM, font=('Consolas', 8)).pack(side=tk.LEFT, padx=(10,2))
        self.frame_lbl = tk.Label(bar, text="—", bg=PANEL, fg=GREEN, font=('Consolas', 8), width=7)
        self.frame_lbl.pack(side=tk.LEFT)

        self.scrubber = tk.Scale(bar, from_=0, to=0, orient=tk.HORIZONTAL, variable=self.v_frame,
                                 bg=PANEL, fg=GREEN, highlightthickness=0, troughcolor=BORDER,
                                 activebackground=GREEN, length=240, relief='flat', showvalue=False,
                                 command=self._scrub)
        self.scrubber.pack(side=tk.LEFT, padx=6)

        tk.Label(bar, text="speed:", bg=PANEL, fg=DIM, font=('Consolas', 8)).pack(side=tk.LEFT, padx=(8,2))
        self.speed_lbl = tk.Label(bar, text="100%", bg=PANEL, fg=GREEN, font=('Consolas', 8), width=4)
        self.speed_lbl.pack(side=tk.LEFT)
        tk.Scale(bar, from_=10, to=400, orient=tk.HORIZONTAL, variable=self.v_speed,
                 bg=PANEL, fg=GREEN, highlightthickness=0, troughcolor=BORDER,
                 activebackground=GREEN, length=110, relief='flat', showvalue=False,
                 command=lambda v: self.speed_lbl.config(text=f"{int(float(v))}%")
                 ).pack(side=tk.LEFT, padx=4)

        tk.Checkbutton(bar, text="loop", variable=self.v_loop, bg=PANEL, fg=FG,
                       font=('Consolas', 8), selectcolor=INBG,
                       activebackground=PANEL).pack(side=tk.LEFT, padx=6)

    def _statusbar(self):
        bar = tk.Frame(self.root, bg=PANEL, height=26)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        self.progress = ttk.Progressbar(bar, orient='horizontal', mode='determinate',
                                        variable=self.v_progress, length=180)
        self.progress.pack(side=tk.LEFT, padx=8, pady=5)
        tk.Label(bar, textvariable=self.v_status, bg=PANEL, fg=DIM,
                 font=('Consolas', 8)).pack(side=tk.LEFT, padx=4)
        self.stats = tk.Label(bar, text="", bg=PANEL, fg=GREEN, font=('Consolas', 8))
        self.stats.pack(side=tk.RIGHT, padx=10)

    def _divider(self, parent, title):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill=tk.X, padx=2, pady=(8,0))
        tk.Label(f, text=f"  {title}", bg=BG, fg=GREEN, font=('Consolas', 8, 'bold')).pack(anchor='w')
        tk.Frame(f, bg=BORDER, height=1).pack(fill=tk.X, pady=(1,2))

    def _slider(self, parent, label, var, lo, hi, is_int=False):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill=tk.X, padx=4, pady=1)
        tk.Label(row, text=label, bg=CARD, fg=FG, font=('Consolas', 8),
                 width=12, anchor='w').pack(side=tk.LEFT)
        vl = tk.Label(row, bg=CARD, fg=GREEN, font=('Consolas', 8), width=5, anchor='e')
        vl.pack(side=tk.RIGHT)
        def upd(*_):
            v = var.get()
            vl.config(text=str(v) if is_int else f"{v:.2f}")
        var.trace_add('write', upd); upd()
        tk.Scale(row, from_=lo, to=hi, orient=tk.HORIZONTAL,
                 resolution=1 if is_int else 0.05, variable=var,
                 bg=CARD, fg=GREEN, highlightthickness=0, troughcolor=BORDER,
                 activebackground=GREEN, length=135, relief='flat',
                 command=lambda v: self._live()).pack(side=tk.LEFT, padx=4)

    def _shortcuts(self):
        self.root.bind('<Control-o>',      lambda e: self.load())
        self.root.bind('<Control-Return>', lambda e: self.convert())
        self.root.bind('<Control-s>',      lambda e: self.save_txt())
        self.root.bind('<Control-e>',      lambda e: self.export_html())
        self.root.bind('<Control-p>',      lambda e: self.export_png())
        self.root.bind('<space>',          lambda e: self.toggle_play())
        self.root.bind('<Control-equal>',  lambda e: self._zoom(1))
        self.root.bind('<Control-minus>',  lambda e: self._zoom(-1))

    def _apply_fontsize(self):
        self.out.configure(font=('Courier New', self.v_fontsize.get()))

    def _zoom(self, d):
        self.v_fontsize.set(max(4, min(28, self.v_fontsize.get() + d)))
        self._apply_fontsize()

    def _live(self, *_):
        if self.v_live.get() and self.img and not self.converting:
            self.convert()

    def _get_chars(self):
        c = self.v_custom.get().strip()
        return list(c) if c else CHARS.get(self.v_charset.get(), list(' .:-=+*#%@'))

    def _set_ui(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        def walk(w):
            for child in w.winfo_children():
                if isinstance(child, (ttk.Button, tk.Button)):
                    try: child.config(state=state)
                    except: pass
                walk(child)
        walk(self.root)

    # loading
    def load(self):
        path = filedialog.askopenfilename(
            filetypes=[('Images', '*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tiff'), ('All', '*.*')])
        if not path: return
        try:
            raw = Image.open(path)
            self.img_path = path
            self.stop_gif()

            # count frames
            nf = 0
            try:
                while True: raw.seek(nf); nf += 1
            except EOFError: pass
            raw.seek(0)

            if nf > 1 and path.lower().endswith('.gif'):
                self.is_gif = True
                self.v_status.set(f"Extracting {nf} frames...")
                self.root.update()
                self.gif_frames    = extract_gif_frames(raw)
                self.gif_durations = [f[1] for f in self.gif_frames]
                self.gif_converted = []
                self.img           = self.gif_frames[0][0]
                self.result        = None
                n = len(self.gif_frames)
                w, h = self.img.size
                self.info_lbl.config(text=f"{os.path.basename(path)}\n{w}×{h}  {n} frames  GIF")
                self.v_status.set(f"Loaded GIF — {n} frames. Hit Convert.")
                self.scrubber.config(to=max(0, n-1))
                self.frame_lbl.config(text=f"—/{n}")
                self._build_gif_thumbs()
                self._cycle_gif_preview()
            else:
                self.is_gif = False
                self.gif_frames = []
                self.gif_converted = []
                self.img = raw.convert('RGB')
                self.gif_bar.pack_forget()
                w, h = self.img.size
                self.info_lbl.config(text=f"{os.path.basename(path)}\n{w}×{h} | {raw.mode}")
                self.v_status.set(f"Loaded: {os.path.basename(path)}")
                self._update_preview()
        except Exception as e:
            messagebox.showerror("Couldn't open", str(e))

    def _update_preview(self):
        if not self.img: return
        thumb = self.img.copy()
        thumb.thumbnail((235, 175), Image.Resampling.LANCZOS)
        self._preview_photo = ImageTk.PhotoImage(thumb)
        self.preview.configure(image=self._preview_photo, text='')

    def _build_gif_thumbs(self):
        if self.gif_thumb_job: self.root.after_cancel(self.gif_thumb_job)
        self.gif_thumb_photos = []
        for pil, _ in self.gif_frames:
            t = pil.copy(); t.thumbnail((235, 175), Image.Resampling.LANCZOS)
            self.gif_thumb_photos.append(ImageTk.PhotoImage(t))
        self.gif_thumb_idx = 0

    def _cycle_gif_preview(self):
        if not self.gif_thumb_photos: return
        photo = self.gif_thumb_photos[self.gif_thumb_idx]
        self.preview.configure(image=photo, text='')
        self._preview_photo = photo
        self.gif_thumb_idx = (self.gif_thumb_idx + 1) % len(self.gif_thumb_photos)
        dur = self.gif_durations[self.gif_thumb_idx] if self.gif_durations else 100
        self.gif_thumb_job = self.root.after(max(50, dur), self._cycle_gif_preview)

    # conversion
    def convert(self):
        if not self.img:
            messagebox.showwarning("Nothing loaded", "Load an image first!"); return
        if self.converting: return
        self.converting = True
        self.stop_gif()
        self._set_ui(False)
        self.v_progress.set(0)
        if self.is_gif:
            self.v_status.set(f"Converting {len(self.gif_frames)} frames...")
            threading.Thread(target=self._gif_thread, daemon=True).start()
        else:
            self.v_status.set("Converting...")
            threading.Thread(target=self._static_thread, daemon=True).start()

    def _static_thread(self):
        try:
            rows = convert_frame(
                self.img, self.v_mode.get(), self.v_width.get(), self._get_chars(),
                self.v_bright.get(), self.v_contrast.get(), self.v_sat.get(),
                self.v_invert.get(), self.v_dither.get(), self.v_edge.get(),
                lambda v: self.root.after(0, self.v_progress.set, v))
            self.result = (self.v_mode.get(), rows)
            self.root.after(0, self._show, self.v_mode.get(), rows)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.converting = False
            self.root.after(0, self._set_ui, True)
            self.root.after(0, self.v_status.set, "Done ✓")

    def _gif_thread(self):
        try:
            mode = self.v_mode.get()
            total = len(self.gif_frames)
            out = []
            for i, (frame, _) in enumerate(self.gif_frames):
                rows = convert_frame(
                    frame, mode, self.v_width.get(), self._get_chars(),
                    self.v_bright.get(), self.v_contrast.get(), self.v_sat.get(),
                    self.v_invert.get(), self.v_dither.get(), self.v_edge.get())
                out.append(rows)
                self.root.after(0, self.v_progress.set, int((i+1)/total*100))
                self.root.after(0, self.v_status.set, f"Frame {i+1}/{total}...")
            self.gif_converted = out
            self.gif_mode = mode
            self.root.after(0, self._gif_ready, mode)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.converting = False
            self.root.after(0, self._set_ui, True)

    def _gif_ready(self, mode):
        n = len(self.gif_converted)
        self.scrubber.config(to=max(0, n-1))
        self.gif_bar.pack(fill=tk.X, before=self.out)
        self.anim_idx = 0
        self.playing = True
        self.play_btn.config(text="⏸ Pause")
        self.v_status.set(f"Done ✓  {n} frames — Space to pause")
        self._tick()

    # playback
    def _tick(self):
        if not self.playing or not self.gif_converted: return
        rows = self.gif_converted[self.anim_idx]
        self._show(self.gif_mode, rows)
        self.v_frame.set(self.anim_idx)
        self.frame_lbl.config(text=f"{self.anim_idx+1}/{len(self.gif_converted)}")

        nxt = self.anim_idx + 1
        if nxt >= len(self.gif_converted):
            if not self.v_loop.get():
                self.playing = False
                self.play_btn.config(text="▶ Play")
                return
            nxt = 0

        delay = max(16, int((self.gif_durations[self.anim_idx] if self.gif_durations else 100)
                            / (self.v_speed.get() / 100.0)))
        self.anim_idx = nxt
        self.anim_job = self.root.after(delay, self._tick)

    def toggle_play(self):
        if not self.gif_converted: return
        if self.playing:
            self.playing = False
            if self.anim_job: self.root.after_cancel(self.anim_job)
            self.play_btn.config(text="▶ Play")
        else:
            self.playing = True
            self.play_btn.config(text="⏸ Pause")
            self._tick()

    def stop_gif(self):
        self.playing = False
        if self.anim_job: self.root.after_cancel(self.anim_job); self.anim_job = None
        self.anim_idx = 0
        self.v_frame.set(0)
        if hasattr(self, 'play_btn'): self.play_btn.config(text="▶ Play")

    def _scrub(self, val):
        if not self.gif_converted: return
        idx = max(0, min(int(float(val)), len(self.gif_converted)-1))
        self.anim_idx = idx
        self._show(self.gif_mode, self.gif_converted[idx])
        self.frame_lbl.config(text=f"{idx+1}/{len(self.gif_converted)}")

    # rendering text widget
    def _show(self, mode, rows):
        w = self.out
        w.config(state=tk.NORMAL)
        w.delete('1.0', tk.END)

        # only clear tags when not mid-animation (slow otherwise)
        if not self.playing:
            for tag in list(self.tags):
                try: w.tag_delete(tag)
                except: pass
            self.tags.clear()

        nrows = len(rows)
        chars = 0

        if mode == 'grayscale':
            w.insert(tk.END, '\n'.join(rows))
            chars = sum(len(r) for r in rows)
        elif mode == 'color':
            for i, row in enumerate(rows):
                for ch, col in row:
                    t = 'c' + col[1:]
                    if t not in self.tags:
                        w.tag_configure(t, foreground=col); self.tags.add(t)
                    w.insert(tk.END, ch, t); chars += 1
                if i < nrows-1: w.insert(tk.END, '\n')
        elif mode == 'halfblock':
            for i, row in enumerate(rows):
                for ch, fg, bg in row:
                    t = 'h' + fg[1:] + bg[1:]
                    if t not in self.tags:
                        w.tag_configure(t, foreground=fg, background=bg); self.tags.add(t)
                    w.insert(tk.END, ch, t); chars += 1
                if i < nrows-1: w.insert(tk.END, '\n')

        w.config(state=tk.DISABLED)
        if not self.playing:
            self.stats.config(text=f"{nrows} rows × {self.v_width.get()} cols  {chars:,} chars")

    # exports
    def copy(self):
        txt = self.out.get('1.0', tk.END).strip()
        if not txt: messagebox.showwarning("Empty", "Nothing to copy."); return
        self.root.clipboard_clear(); self.root.clipboard_append(txt)
        self.v_status.set("Copied ✓")

    def save_txt(self):
        txt = self.out.get('1.0', tk.END).strip()
        if not txt: messagebox.showwarning("Empty", "Nothing to save."); return
        path = filedialog.asksaveasfilename(defaultextension='.txt',
                                            filetypes=[('Text', '*.txt'), ('All', '*.*')])
        if path:
            open(path, 'w', encoding='utf-8').write(txt)
            self.v_status.set("Saved ✓")

    def export_html(self):
        if self.is_gif and self.gif_converted:
            path = filedialog.asksaveasfilename(defaultextension='.html',
                                                filetypes=[('HTML', '*.html'), ('All', '*.*')])
            if not path: return
            html = make_animated_html(self.gif_converted, self.gif_durations, self.gif_mode,
                                      fontsize=self.v_fontsize.get())
            open(path, 'w', encoding='utf-8').write(html)
            self.v_status.set("Animated HTML exported ✓")
            if messagebox.askyesno("Open?", "Open in browser?"):
                import webbrowser; webbrowser.open('file://' + os.path.abspath(path))
        elif self.result:
            mode, rows = self.result
            path = filedialog.asksaveasfilename(defaultextension='.html',
                                                filetypes=[('HTML', '*.html'), ('All', '*.*')])
            if not path: return
            open(path, 'w', encoding='utf-8').write(
                make_static_html(rows, mode, fontsize=self.v_fontsize.get()))
            self.v_status.set("HTML exported ✓")
            if messagebox.askyesno("Open?", "Open in browser?"):
                import webbrowser; webbrowser.open('file://' + os.path.abspath(path))
        else:
            messagebox.showwarning("Nothing", "Convert something first.")

    def export_png(self):
        if self.is_gif and self.gif_converted:
            all_frames = messagebox.askyesno("GIF export",
                f"Export all {len(self.gif_converted)} frames as separate PNGs?\n"
                "Yes = all to a folder, No = just current frame")
            if all_frames:
                folder = filedialog.askdirectory(title="Output folder")
                if not folder: return
                fnt = self._get_font(); cw, ch = self._measure(fnt)
                base = os.path.splitext(os.path.basename(self.img_path))[0]
                def go():
                    for i, rows in enumerate(self.gif_converted):
                        rows_to_image(rows, self.gif_mode, fnt, cw, ch)\
                            .save(os.path.join(folder, f"{base}_{i:04d}.png"))
                        self.root.after(0, self.v_progress.set, int((i+1)/len(self.gif_converted)*100))
                    self.root.after(0, self.v_status.set, f"Exported {len(self.gif_converted)} PNGs ✓")
                threading.Thread(target=go, daemon=True).start()
                return
            else:
                rows = self.gif_converted[self.anim_idx]
                mode = self.gif_mode
        elif self.result:
            mode, rows = self.result
        else:
            messagebox.showwarning("Nothing", "Convert something first."); return

        path = filedialog.asksaveasfilename(defaultextension='.png',
                                            filetypes=[('PNG', '*.png'), ('All', '*.*')])
        if not path: return
        try:
            fnt = self._get_font(); cw, ch = self._measure(fnt)
            rows_to_image(rows, mode, fnt, cw, ch).save(path)
            self.v_status.set("PNG exported ✓")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def _get_font(self):
        sz = max(8, self.v_fontsize.get())
        for name in ("cour.ttf", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"):
            try: return ImageFont.truetype(name, sz)
            except: pass
        return ImageFont.load_default()

    def _measure(self, fnt):
        d = ImageDraw.Draw(Image.new('RGB', (80, 80)))
        bb = d.textbbox((0,0), 'X', font=fnt)
        return bb[2]-bb[0]+1, bb[3]-bb[1]+2

    def reset(self):
        self.stop_gif()
        self.v_width.set(120);    self.v_bright.set(1.0)
        self.v_contrast.set(1.1); self.v_sat.set(1.2)
        self.v_invert.set(False); self.v_dither.set(False)
        self.v_live.set(False);   self.v_charset.set("Standard")
        self.v_edge.set("off");   self.v_fontsize.set(9)
        self.v_custom.set("");    self.v_speed.set(100)
        self._apply_fontsize()
        self.v_status.set("Reset ✓")


if __name__ == '__main__':
    root = tk.Tk()
    root.resizable(True, True)
    App(root)
    root.mainloop()
