import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox, font as tkfont
from PIL import Image, ImageTk, ImageEnhance, ImageDraw, ImageFont, ImageFilter
import numpy as np
import os
import threading
import colorsys


# ─────────────────────────────────────────────────────────────────────────────
#  CHARACTER SETS
# ─────────────────────────────────────────────────────────────────────────────
ASCII_CHAR_SETS = {
    "Standard":     list(' .\'`^",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$'),
    "Dense":        list('@#S%?*+;:,. '),
    "Sparse":       list(' .-:=+*#%@'),
    "Blocks":       list(' ░▒▓█'),
    "Blocks+":      list(' ·∙●▪▫▬▮▯▲▴▸▾◆◇○◉★☆⬛⬜'),
    "Braille":      list(' ⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏⠐⠑⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟⠠⠡⠢⠣⠤⠥⠦⠧⠨⠩⠪⠫⠬⠭⠮⠯⠰⠱⠲⠳⠴⠵⠶⠷⠸⠹⠺⠻⠼⠽⠾⠿'),
    "Minimal":      list(' :. #'),
    "Mathematical": list(' ·÷×±∓∔∕∖∗∘∙√∛∜∝∞∟∠∡∢∣'),
    "Custom":       [],
}

# Half-block: ▀ (upper half) — foreground = top pixel, bg = bottom pixel
HALF_BLOCK_CHAR = "▀"

EDGE_CHARS = {
    "off":  None,
    "soft": ImageFilter.SMOOTH,
    "hard": ImageFilter.SHARPEN,
    "find": ImageFilter.FIND_EDGES,
}


# ─────────────────────────────────────────────────────────────────────────────
#  THEME
# ─────────────────────────────────────────────────────────────────────────────
THEME = {
    'bg':           '#0d0d0d',
    'panel':        '#141414',
    'card':         '#1a1a1a',
    'border':       '#2a2a2a',
    'fg':           '#e8e8e8',
    'fg_dim':       '#666666',
    'accent':       '#00ff88',
    'accent2':      '#00ccff',
    'danger':       '#ff4466',
    'btn':          '#1e1e1e',
    'btn_hover':    '#2a2a2a',
    'input_bg':     '#111111',
    'scrollbar':    '#222222',
    'tag_prefix':   'col_',
}


def hex_to_rgb(hex_color: str):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r, g, b):
    return f'#{int(r):02x}{int(g):02x}{int(b):02x}'


# ─────────────────────────────────────────────────────────────────────────────
#  CONVERSION ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class ConversionEngine:

    @staticmethod
    def pixel_to_ascii(pixel_value: int, chars: list) -> str:
        idx = int(pixel_value / 255 * (len(chars) - 1))
        return chars[max(0, min(idx, len(chars) - 1))]

    @staticmethod
    def apply_dithering(pixels: np.ndarray) -> np.ndarray:
        """Floyd-Steinberg dithering for better grayscale accuracy."""
        arr = pixels.astype(float)
        h, w = arr.shape
        for y in range(h):
            for x in range(w):
                old = arr[y, x]
                new = round(old / 255) * 255
                arr[y, x] = new
                err = old - new
                if x + 1 < w:            arr[y, x+1]   += err * 7/16
                if y + 1 < h:
                    if x - 1 >= 0:        arr[y+1, x-1] += err * 3/16
                    arr[y+1, x]           += err * 5/16
                    if x + 1 < w:         arr[y+1, x+1] += err * 1/16
        return np.clip(arr, 0, 255).astype(np.uint8)

    @staticmethod
    def convert_grayscale(image: Image.Image, width: int, chars: list,
                          brightness: float, contrast: float, invert: bool,
                          dither: bool, edge_mode: str,
                          progress_cb=None) -> list:
        """Returns list of strings (rows of ASCII chars)."""
        aspect = image.size[1] / image.size[0]
        height = max(1, int(width * aspect * 0.55))
        img = image.resize((width, height), Image.Resampling.LANCZOS)

        if edge_mode != "off" and EDGE_CHARS[edge_mode]:
            img = img.filter(EDGE_CHARS[edge_mode])

        img = img.convert('L')
        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Contrast(img).enhance(contrast)

        pixels = np.array(img)
        if invert:
            pixels = 255 - pixels
        if dither:
            pixels = ConversionEngine.apply_dithering(pixels)

        rows = []
        total = pixels.shape[0]
        for i, row in enumerate(pixels):
            rows.append(''.join(ConversionEngine.pixel_to_ascii(p, chars) for p in row))
            if progress_cb and (i % 5 == 0 or i == total - 1):
                progress_cb(int((i + 1) / total * 100))
        return rows

    @staticmethod
    def convert_color(image: Image.Image, width: int, chars: list,
                      brightness: float, contrast: float, invert: bool,
                      dither: bool, edge_mode: str,
                      progress_cb=None) -> list:
        """
        Returns list of rows; each row is a list of (char, '#rrggbb') tuples.
        """
        aspect = image.size[1] / image.size[0]
        height = max(1, int(width * aspect * 0.55))
        img_color = image.resize((width, height), Image.Resampling.LANCZOS).convert('RGB')

        if edge_mode != "off" and EDGE_CHARS[edge_mode]:
            img_color = img_color.filter(EDGE_CHARS[edge_mode])

        img_gray = img_color.convert('L')
        img_gray = ImageEnhance.Brightness(img_gray).enhance(brightness)
        img_gray = ImageEnhance.Contrast(img_gray).enhance(contrast)
        img_color = ImageEnhance.Brightness(img_color).enhance(brightness)
        img_color = ImageEnhance.Contrast(img_color).enhance(contrast)

        gray_px = np.array(img_gray)
        color_px = np.array(img_color)

        if invert:
            gray_px = 255 - gray_px
            color_px = 255 - color_px

        rows = []
        total = gray_px.shape[0]
        for i, (gray_row, color_row) in enumerate(zip(gray_px, color_px)):
            row = []
            for g, c in zip(gray_row, color_row):
                char = ConversionEngine.pixel_to_ascii(g, chars)
                row.append((char, rgb_to_hex(c[0], c[1], c[2])))
            rows.append(row)
            if progress_cb and (i % 5 == 0 or i == total - 1):
                progress_cb(int((i + 1) / total * 100))
        return rows

    @staticmethod
    def convert_halfblock(image: Image.Image, width: int,
                          brightness: float, contrast: float, invert: bool,
                          progress_cb=None) -> list:
        """
        Half-block HD mode: each character = 2 vertical pixels.
        Returns list of rows; each row is list of (char, fg_hex, bg_hex).
        char is always HALF_BLOCK_CHAR (▀).
        fg = top pixel color, bg = bottom pixel color.
        Effectively DOUBLES the vertical resolution.
        """
        aspect = image.size[1] / image.size[0]
        # For half-block, use 0.5 factor since each char covers 2 rows
        raw_height = max(2, int(width * aspect))
        # Make even
        if raw_height % 2 != 0:
            raw_height += 1

        img = image.resize((width, raw_height), Image.Resampling.LANCZOS).convert('RGB')
        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Contrast(img).enhance(contrast)

        pixels = np.array(img)
        if invert:
            pixels = 255 - pixels

        rows = []
        total = raw_height // 2
        for i in range(0, raw_height - 1, 2):
            top_row    = pixels[i]
            bottom_row = pixels[i + 1]
            row = []
            for top, bot in zip(top_row, bottom_row):
                fg = rgb_to_hex(top[0], top[1], top[2])
                bg = rgb_to_hex(bot[0], bot[1], bot[2])
                row.append((HALF_BLOCK_CHAR, fg, bg))
            rows.append(row)
            if progress_cb:
                progress_cb(int((i // 2 + 1) / total * 100))
        return rows

    @staticmethod
    def rows_to_html(rows, mode: str, font_size: int = 10, bg: str = '#000000') -> str:
        """Export colored/half-block result as an HTML file."""
        lines = []
        lines.append(f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>ASCII Art — Pro Export</title>
<style>
  body {{ background:{bg}; margin:0; padding:16px; }}
  pre {{
    font-family: 'Courier New', monospace;
    font-size: {font_size}px;
    line-height: 1.2;
    letter-spacing: 0;
    margin: 0;
  }}
  span {{ display: inline; }}
</style>
</head>
<body><pre>""")

        if mode == 'grayscale':
            for row in rows:
                lines.append(row.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
        elif mode == 'color':
            for row in rows:
                row_html = ''
                for char, col in row:
                    safe = char.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    row_html += f'<span style="color:{col}">{safe}</span>'
                lines.append(row_html)
        elif mode == 'halfblock':
            for row in rows:
                row_html = ''
                for char, fg, bg_c in row:
                    row_html += (f'<span style="color:{fg};background:{bg_c}">'
                                 f'{char}</span>')
                lines.append(row_html)

        lines.append('</pre></body></html>')
        return '\n'.join(lines)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN GUI
# ─────────────────────────────────────────────────────────────────────────────
class ASCIIArtConverterPro:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ASCII Art Converter PRO")
        self.root.geometry("1440x900")
        self.root.minsize(1100, 700)
        self.root.configure(bg=THEME['bg'])

        # ── State ────────────────────────────────────────────────────────────
        self.image_path      = None
        self.original_image  = None
        self.preview_photo   = None
        self._last_result    = None   # (mode, rows)
        self._converting     = False
        self._registered_tags = set()

        # ── Tkinter Vars ─────────────────────────────────────────────────────
        self.width_var       = tk.IntVar(value=120)
        self.brightness_var  = tk.DoubleVar(value=1.0)
        self.contrast_var    = tk.DoubleVar(value=1.1)
        self.saturation_var  = tk.DoubleVar(value=1.2)
        self.invert_var      = tk.BooleanVar(value=False)
        self.dither_var      = tk.BooleanVar(value=False)
        self.live_var        = tk.BooleanVar(value=False)
        self.charset_var     = tk.StringVar(value="Standard")
        self.mode_var        = tk.StringVar(value="color")
        self.edge_var        = tk.StringVar(value="off")
        self.font_size_var   = tk.IntVar(value=9)
        self.custom_chars_var = tk.StringVar(value="")
        self.bg_color_var    = tk.StringVar(value="#000000")
        self.progress_var    = tk.IntVar(value=0)
        self.status_var      = tk.StringVar(value="Ready — load an image to begin")

        # ── Build UI ─────────────────────────────────────────────────────────
        self._apply_ttk_styles()
        self._build_ui()
        self._bind_shortcuts()

    # ─────────────────────────────────────────────────────────────────────────
    #  STYLES
    # ─────────────────────────────────────────────────────────────────────────
    def _apply_ttk_styles(self):
        s = ttk.Style()
        s.theme_use('default')
        s.configure('TFrame',       background=THEME['bg'])
        s.configure('Card.TFrame',  background=THEME['card'])
        s.configure('TLabel',       background=THEME['card'],  foreground=THEME['fg'],
                    font=('Consolas', 9))
        s.configure('Head.TLabel',  background=THEME['bg'],    foreground=THEME['accent'],
                    font=('Consolas', 10, 'bold'))
        s.configure('Dim.TLabel',   background=THEME['card'],  foreground=THEME['fg_dim'],
                    font=('Consolas', 8))

        s.configure('TCheckbutton', background=THEME['card'],  foreground=THEME['fg'],
                    font=('Consolas', 9))
        s.map('TCheckbutton',
              background=[('active', THEME['card'])],
              foreground=[('active', THEME['accent'])])

        s.configure('TCombobox',    fieldbackground=THEME['input_bg'],
                    background=THEME['input_bg'], foreground=THEME['fg'],
                    selectbackground=THEME['accent'], font=('Consolas', 9))

        s.configure('Accent.TButton', background=THEME['accent'],
                    foreground='#000000', font=('Consolas', 9, 'bold'), padding=(10, 6))
        s.map('Accent.TButton',
              background=[('active', THEME['accent2']), ('disabled', THEME['btn'])])

        s.configure('TButton', background=THEME['btn'],
                    foreground=THEME['fg'], font=('Consolas', 9), padding=(8, 5))
        s.map('TButton',
              background=[('active', THEME['btn_hover']), ('disabled', THEME['border'])])

        s.configure('TProgressbar', troughcolor=THEME['border'],
                    background=THEME['accent'], thickness=4)

        s.configure('TScale',       background=THEME['card'],
                    troughcolor=THEME['border'], sliderlength=12)
        s.map('TScale', background=[('active', THEME['accent'])])

        s.configure('TSpinbox',     background=THEME['input_bg'],
                    fieldbackground=THEME['input_bg'],
                    foreground=THEME['fg'], font=('Consolas', 9))

        s.configure('TLabelframe',  background=THEME['card'],
                    foreground=THEME['fg_dim'], font=('Consolas', 8))
        s.configure('TLabelframe.Label', background=THEME['card'],
                    foreground=THEME['accent2'], font=('Consolas', 9, 'bold'))

        s.configure('TRadiobutton', background=THEME['card'], foreground=THEME['fg'],
                    font=('Consolas', 9))
        s.map('TRadiobutton',
              background=[('active', THEME['card'])],
              foreground=[('active', THEME['accent'])])

    # ─────────────────────────────────────────────────────────────────────────
    #  UI CONSTRUCTION
    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header bar
        self._build_header()

        # Main area (sidebar + output)
        body = ttk.Frame(self.root, style='TFrame')
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        self._build_sidebar(body)
        self._build_output_panel(body)

        # Status bar
        self._build_status_bar()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=THEME['panel'], height=52)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)

        # Logo
        tk.Label(hdr, text="▓▒░ ASCII ART CONVERTER PRO ░▒▓",
                 bg=THEME['panel'], fg=THEME['accent'],
                 font=('Consolas', 13, 'bold')).pack(side=tk.LEFT, padx=16)

        # Action buttons (right-aligned)
        btn_specs = [
            ("⬆  Load Image",      self.select_image,        'Accent.TButton'),
            ("▶  Convert",         self.start_conversion,    'TButton'),
            ("⎘  Copy",            self.copy_to_clipboard,   'TButton'),
            ("💾  Save .txt",       self.save_ascii_txt,      'TButton'),
            ("🌐  Export HTML",     self.export_html,         'TButton'),
            ("🖼  Export PNG",      self.export_png,          'TButton'),
            ("↺  Reset",           self.reset_settings,      'TButton'),
        ]
        for label, cmd, style in reversed(btn_specs):
            ttk.Button(hdr, text=label, command=cmd, style=style)\
                .pack(side=tk.RIGHT, padx=4, pady=10)

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=THEME['bg'], width=270)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        sidebar.pack_propagate(False)

        # ── Image Preview ────────────────────────────────────────────────────
        prev_card = tk.LabelFrame(sidebar, text="  Preview  ", bg=THEME['card'],
                                  fg=THEME['accent2'], font=('Consolas', 9, 'bold'),
                                  bd=1, relief='flat', labelanchor='n')
        prev_card.pack(fill=tk.X, pady=(4, 2), padx=2)

        self.preview_label = tk.Label(prev_card, bg=THEME['card'],
                                      text="No image loaded\n\nDrop an image or\nclick ⬆ Load Image",
                                      fg=THEME['fg_dim'], font=('Consolas', 9),
                                      width=28, height=10, anchor='center')
        self.preview_label.pack(padx=4, pady=4)

        self.img_info_lbl = tk.Label(sidebar, text="", bg=THEME['bg'],
                                     fg=THEME['fg_dim'], font=('Consolas', 8))
        self.img_info_lbl.pack()

        # ── Mode ─────────────────────────────────────────────────────────────
        self._section(sidebar, "RENDER MODE")
        mode_f = tk.Frame(sidebar, bg=THEME['card'], bd=0)
        mode_f.pack(fill=tk.X, padx=2, pady=1)
        modes = [
            ("🎨 Color ASCII",   "color"),
            ("◐ Half-Block HD",  "halfblock"),
            ("▓ Grayscale",      "grayscale"),
        ]
        for txt, val in modes:
            r = ttk.Radiobutton(mode_f, text=txt, variable=self.mode_var,
                                value=val, command=self._on_change)
            r.pack(anchor='w', padx=8, pady=2)
        tk.Label(mode_f,
                 text="Half-Block HD uses ▀ chars for\n2× vertical resolution + full color.",
                 bg=THEME['card'], fg=THEME['fg_dim'],
                 font=('Consolas', 7), justify='left').pack(anchor='w', padx=8, pady=(0,4))

        # ── Characters ───────────────────────────────────────────────────────
        self._section(sidebar, "CHARACTER SET")
        cs_f = tk.Frame(sidebar, bg=THEME['card'])
        cs_f.pack(fill=tk.X, padx=2, pady=1)

        self.charset_combo = ttk.Combobox(cs_f, values=list(ASCII_CHAR_SETS.keys()),
                                          textvariable=self.charset_var,
                                          state='readonly', width=22)
        self.charset_combo.pack(padx=8, pady=(6, 2))
        self.charset_combo.bind("<<ComboboxSelected>>", self._on_change)

        tk.Label(cs_f, text="Custom chars (overrides set):",
                 bg=THEME['card'], fg=THEME['fg_dim'],
                 font=('Consolas', 7)).pack(anchor='w', padx=8)
        cust_entry = tk.Entry(cs_f, textvariable=self.custom_chars_var,
                              bg=THEME['input_bg'], fg=THEME['fg'],
                              insertbackground=THEME['fg'],
                              font=('Consolas', 9), width=24, relief='flat')
        cust_entry.pack(padx=8, pady=(0, 6))
        cust_entry.bind('<Return>', self._on_change)

        # ── Image Adjustments ────────────────────────────────────────────────
        self._section(sidebar, "IMAGE ADJUSTMENTS")
        adj_f = tk.Frame(sidebar, bg=THEME['card'])
        adj_f.pack(fill=tk.X, padx=2, pady=1)

        sliders = [
            ("Width (chars)",  self.width_var,      20, 300, 1,  True),
            ("Brightness",     self.brightness_var,  0.1, 3.0, 0.05, False),
            ("Contrast",       self.contrast_var,    0.1, 3.0, 0.05, False),
            ("Saturation",     self.saturation_var,  0.0, 3.0, 0.05, False),
        ]
        for label, var, lo, hi, res, is_int in sliders:
            self._slider_row(adj_f, label, var, lo, hi, res, is_int)

        # ── Options ──────────────────────────────────────────────────────────
        self._section(sidebar, "OPTIONS")
        opt_f = tk.Frame(sidebar, bg=THEME['card'])
        opt_f.pack(fill=tk.X, padx=2, pady=1)

        checks = [
            ("Invert",        self.invert_var),
            ("Floyd-Steinberg Dither", self.dither_var),
            ("Live Preview",  self.live_var),
        ]
        for txt, var in checks:
            ttk.Checkbutton(opt_f, text=txt, variable=var,
                            command=self._on_change).pack(anchor='w', padx=8, pady=2)

        tk.Label(opt_f, text="Edge Enhancement:",
                 bg=THEME['card'], fg=THEME['fg_dim'],
                 font=('Consolas', 8)).pack(anchor='w', padx=8, pady=(4, 0))
        edge_combo = ttk.Combobox(opt_f, values=list(EDGE_CHARS.keys()),
                                  textvariable=self.edge_var,
                                  state='readonly', width=16)
        edge_combo.pack(padx=8, pady=(0, 6))
        edge_combo.bind("<<ComboboxSelected>>", self._on_change)

        # Font size for output
        tk.Label(opt_f, text="Output Font Size:",
                 bg=THEME['card'], fg=THEME['fg_dim'],
                 font=('Consolas', 8)).pack(anchor='w', padx=8)
        fs_spin = ttk.Spinbox(opt_f, from_=5, to=24, increment=1,
                              textvariable=self.font_size_var, width=6,
                              command=self._update_font_size)
        fs_spin.pack(anchor='w', padx=8, pady=(0, 6))
        fs_spin.bind('<Return>', lambda e: self._update_font_size())

    # ─── Output panel ────────────────────────────────────────────────────────
    def _build_output_panel(self, parent):
        right = tk.Frame(parent, bg=THEME['bg'])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Toolbar above output
        toolbar = tk.Frame(right, bg=THEME['bg'], height=30)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="OUTPUT", bg=THEME['bg'],
                 fg=THEME['fg_dim'], font=('Consolas', 8)).pack(side=tk.LEFT, padx=6)

        # Zoom buttons
        for sym, delta in [("−", -1), ("+", +1)]:
            tk.Button(toolbar, text=f"  {sym}  ", bg=THEME['btn'], fg=THEME['fg'],
                      font=('Consolas', 10, 'bold'), relief='flat', bd=0,
                      activebackground=THEME['btn_hover'], activeforeground=THEME['accent'],
                      command=lambda d=delta: self._zoom(d)).pack(side=tk.RIGHT, padx=1)
        tk.Label(toolbar, text="zoom:", bg=THEME['bg'],
                 fg=THEME['fg_dim'], font=('Consolas', 8)).pack(side=tk.RIGHT, padx=(0, 4))

        # Output text widget
        self.output_text = tk.Text(
            right, wrap=tk.NONE,
            font=('Courier New', self.font_size_var.get()),
            bg=THEME['input_bg'], fg=THEME['fg'],
            insertbackground=THEME['fg'],
            selectbackground=THEME['accent'], selectforeground='#000000',
            relief='flat', bd=4,
            cursor='arrow',
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        # Scrollbars
        vsb = ttk.Scrollbar(right, orient='vertical',
                            command=self.output_text.yview)
        hsb = ttk.Scrollbar(right, orient='horizontal',
                            command=self.output_text.xview)
        self.output_text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.place(relx=1.0, rely=0, relheight=1.0, anchor='ne')
        hsb.place(relx=0, rely=1.0, relwidth=1.0, anchor='sw')

    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg=THEME['panel'], height=28)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        self.progress_bar = ttk.Progressbar(bar, orient='horizontal',
                                            mode='determinate',
                                            variable=self.progress_var,
                                            length=200)
        self.progress_bar.pack(side=tk.LEFT, padx=8, pady=6)

        tk.Label(bar, textvariable=self.status_var, bg=THEME['panel'],
                 fg=THEME['fg_dim'], font=('Consolas', 8)).pack(side=tk.LEFT, padx=4)

        self.stats_lbl = tk.Label(bar, text="", bg=THEME['panel'],
                                  fg=THEME['accent'], font=('Consolas', 8))
        self.stats_lbl.pack(side=tk.RIGHT, padx=12)

    # ─────────────────────────────────────────────────────────────────────────
    #  HELPER WIDGETS
    # ─────────────────────────────────────────────────────────────────────────
    def _section(self, parent, title):
        f = tk.Frame(parent, bg=THEME['bg'])
        f.pack(fill=tk.X, padx=2, pady=(8, 0))
        tk.Label(f, text=f"  {title}",
                 bg=THEME['bg'], fg=THEME['accent'],
                 font=('Consolas', 8, 'bold')).pack(anchor='w')
        tk.Frame(f, bg=THEME['border'], height=1).pack(fill=tk.X, pady=(1, 2))

    def _slider_row(self, parent, label, var, lo, hi, res, is_int=False):
        row = tk.Frame(parent, bg=THEME['card'])
        row.pack(fill=tk.X, padx=4, pady=1)

        tk.Label(row, text=label, bg=THEME['card'], fg=THEME['fg'],
                 font=('Consolas', 8), width=16, anchor='w').pack(side=tk.LEFT)

        val_lbl = tk.Label(row, bg=THEME['card'], fg=THEME['accent'],
                           font=('Consolas', 8), width=5, anchor='e')
        val_lbl.pack(side=tk.RIGHT)

        def update_label(*_):
            v = var.get()
            val_lbl.config(text=str(v) if is_int else f"{v:.2f}")

        var.trace_add('write', update_label)
        update_label()

        scale_kw = dict(from_=lo, to=hi, orient=tk.HORIZONTAL,
                        resolution=res, variable=var,
                        bg=THEME['card'], fg=THEME['accent'],
                        highlightthickness=0, troughcolor=THEME['border'],
                        activebackground=THEME['accent'],
                        length=140, relief='flat',
                        command=lambda v: self._on_change())
        if is_int:
            scale_kw['resolution'] = 1
        tk.Scale(row, **scale_kw).pack(side=tk.LEFT, padx=4)

    # ─────────────────────────────────────────────────────────────────────────
    #  SHORTCUTS
    # ─────────────────────────────────────────────────────────────────────────
    def _bind_shortcuts(self):
        binds = [
            ('<Control-o>', lambda e: self.select_image()),
            ('<Control-Return>', lambda e: self.start_conversion()),
            ('<Control-s>', lambda e: self.save_ascii_txt()),
            ('<Control-e>', lambda e: self.export_html()),
            ('<Control-p>', lambda e: self.export_png()),
            ('<Control-c>', lambda e: self.copy_to_clipboard()),
            ('<Control-equal>', lambda e: self._zoom(+1)),
            ('<Control-minus>', lambda e: self._zoom(-1)),
        ]
        for seq, fn in binds:
            self.root.bind(seq, fn)

    # ─────────────────────────────────────────────────────────────────────────
    #  IMAGE LOADING
    # ─────────────────────────────────────────────────────────────────────────
    def select_image(self):
        ft = [('Images', '*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tiff'), ('All', '*.*')]
        path = filedialog.askopenfilename(filetypes=ft)
        if not path:
            return
        try:
            self.original_image = Image.open(path)
            self.image_path = path
            self._update_preview()
            w, h = self.original_image.size
            self.img_info_lbl.config(
                text=f"{os.path.basename(path)}\n{w}×{h} px | {self.original_image.mode}")
            self.status_var.set(f"Loaded: {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Error", f"Cannot open image:\n{exc}")

    def _update_preview(self):
        if not self.original_image:
            return
        img = self.original_image.copy()
        img.thumbnail((240, 180), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(img)
        self.preview_label.configure(image=self.preview_photo, text='')

    # ─────────────────────────────────────────────────────────────────────────
    #  CONVERSION
    # ─────────────────────────────────────────────────────────────────────────
    def _get_chars(self):
        custom = self.custom_chars_var.get().strip()
        if custom:
            return list(custom)
        chars = ASCII_CHAR_SETS.get(self.charset_var.get(), [])
        return chars if chars else list(' .:-=+*#%@')

    def start_conversion(self):
        if not self.original_image:
            messagebox.showwarning("No image", "Please load an image first!")
            return
        if self._converting:
            return
        self._converting = True
        self._set_buttons_state(tk.DISABLED)
        self.progress_var.set(0)
        self.status_var.set("Converting…")
        thread = threading.Thread(target=self._worker, daemon=True)
        thread.start()

    def _worker(self):
        try:
            img = self.original_image.copy()
            # Apply saturation before passing to engine
            if self.saturation_var.get() != 1.0:
                img_rgb = img.convert('RGB')
                img = ImageEnhance.Color(img_rgb).enhance(self.saturation_var.get())

            mode    = self.mode_var.get()
            width   = self.width_var.get()
            bright  = self.brightness_var.get()
            contrast = self.contrast_var.get()
            invert  = self.invert_var.get()
            dither  = self.dither_var.get()
            edge    = self.edge_var.get()
            chars   = self._get_chars()

            def prog(v):
                self.root.after(0, self.progress_var.set, v)

            if mode == 'grayscale':
                rows = ConversionEngine.convert_grayscale(
                    img, width, chars, bright, contrast, invert, dither, edge, prog)
            elif mode == 'color':
                rows = ConversionEngine.convert_color(
                    img, width, chars, bright, contrast, invert, dither, edge, prog)
            elif mode == 'halfblock':
                rows = ConversionEngine.convert_halfblock(
                    img, width, bright, contrast, invert, prog)
            else:
                rows = []

            self._last_result = (mode, rows)
            self.root.after(0, self._render_output, mode, rows)

        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror("Conversion error", str(exc)))
        finally:
            self._converting = False
            self.root.after(0, self._set_buttons_state, tk.NORMAL)
            self.root.after(0, self.status_var.set, "Done ✓")

    def _render_output(self, mode, rows):
        widget = self.output_text
        widget.config(state=tk.NORMAL)
        widget.delete('1.0', tk.END)

        # Clear old color tags
        for tag in list(self._registered_tags):
            try:
                widget.tag_delete(tag)
            except Exception:
                pass
        self._registered_tags.clear()

        if mode == 'grayscale':
            widget.insert(tk.END, '\n'.join(rows))
            char_count = sum(len(r) for r in rows)
            line_count = len(rows)

        elif mode == 'color':
            char_count = 0
            line_count = len(rows)
            for i, row in enumerate(rows):
                for char, col in row:
                    tag = THEME['tag_prefix'] + col[1:]   # strip '#'
                    if tag not in self._registered_tags:
                        widget.tag_configure(tag, foreground=col)
                        self._registered_tags.add(tag)
                    widget.insert(tk.END, char, tag)
                    char_count += 1
                if i < line_count - 1:
                    widget.insert(tk.END, '\n')

        elif mode == 'halfblock':
            char_count = 0
            line_count = len(rows)
            for i, row in enumerate(rows):
                for char, fg, bg in row:
                    ftag = 'fg_' + fg[1:]
                    btag = 'bg_' + bg[1:]
                    combo = ftag + '__' + btag
                    if combo not in self._registered_tags:
                        widget.tag_configure(combo, foreground=fg, background=bg)
                        self._registered_tags.add(combo)
                    widget.insert(tk.END, char, combo)
                    char_count += 1
                if i < line_count - 1:
                    widget.insert(tk.END, '\n')

        widget.config(state=tk.DISABLED)

        self.stats_lbl.config(
            text=f"{line_count} rows × {self.width_var.get()} cols  |  {char_count:,} chars")

    # ─────────────────────────────────────────────────────────────────────────
    #  FONT / ZOOM
    # ─────────────────────────────────────────────────────────────────────────
    def _update_font_size(self):
        self.output_text.configure(font=('Courier New', self.font_size_var.get()))

    def _zoom(self, delta):
        new_size = max(4, min(28, self.font_size_var.get() + delta))
        self.font_size_var.set(new_size)
        self._update_font_size()

    # ─────────────────────────────────────────────────────────────────────────
    #  LIVE PREVIEW / CHANGE HANDLER
    # ─────────────────────────────────────────────────────────────────────────
    def _on_change(self, *_):
        if self.live_var.get() and self.original_image and not self._converting:
            self.start_conversion()

    # ─────────────────────────────────────────────────────────────────────────
    #  CLIPBOARD
    # ─────────────────────────────────────────────────────────────────────────
    def copy_to_clipboard(self):
        txt = self.output_text.get('1.0', tk.END).strip()
        if not txt:
            messagebox.showwarning("Empty", "Nothing to copy yet.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(txt)
        self.status_var.set("Copied to clipboard ✓")

    # ─────────────────────────────────────────────────────────────────────────
    #  SAVE .TXT
    # ─────────────────────────────────────────────────────────────────────────
    def save_ascii_txt(self):
        txt = self.output_text.get('1.0', tk.END).strip()
        if not txt:
            messagebox.showwarning("Empty", "Nothing to save yet.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension='.txt',
            filetypes=[('Text', '*.txt'), ('All', '*.*')])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(txt)
            self.status_var.set(f"Saved: {os.path.basename(path)} ✓")

    # ─────────────────────────────────────────────────────────────────────────
    #  EXPORT HTML (color-preserving)
    # ─────────────────────────────────────────────────────────────────────────
    def export_html(self):
        if not self._last_result:
            messagebox.showwarning("Empty", "Convert an image first.")
            return
        mode, rows = self._last_result
        path = filedialog.asksaveasfilename(
            defaultextension='.html',
            filetypes=[('HTML', '*.html'), ('All', '*.*')])
        if not path:
            return
        html = ConversionEngine.rows_to_html(
            rows, mode, font_size=self.font_size_var.get(),
            bg=self.bg_color_var.get())
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        self.status_var.set(f"HTML exported: {os.path.basename(path)} ✓")
        if messagebox.askyesno("Open?", "Open the exported HTML in browser?"):
            import webbrowser
            webbrowser.open(f'file://{os.path.abspath(path)}')

    # ─────────────────────────────────────────────────────────────────────────
    #  EXPORT PNG
    # ─────────────────────────────────────────────────────────────────────────
    def export_png(self):
        if not self._last_result:
            messagebox.showwarning("Empty", "Convert an image first.")
            return
        mode, rows = self._last_result

        path = filedialog.asksaveasfilename(
            defaultextension='.png',
            filetypes=[('PNG', '*.png'), ('All', '*.*')])
        if not path:
            return

        try:
            fs = max(8, self.font_size_var.get())
            try:
                fnt = ImageFont.truetype("cour.ttf", fs)
            except Exception:
                try:
                    fnt = ImageFont.truetype("DejaVuSansMono.ttf", fs)
                except Exception:
                    fnt = ImageFont.load_default()

            # Measure one character
            dummy = Image.new('RGB', (100, 100))
            dd = ImageDraw.Draw(dummy)
            bbox = dd.textbbox((0, 0), 'A', font=fnt)
            cw = bbox[2] - bbox[0] + 1
            ch = bbox[3] - bbox[1] + 2

            if mode == 'grayscale':
                cols_n = max(len(r) for r in rows)
                W = cols_n * cw
                H = len(rows) * ch
                img = Image.new('RGB', (W, H), color='black')
                draw = ImageDraw.Draw(img)
                for ri, row in enumerate(rows):
                    draw.text((0, ri * ch), row, font=fnt, fill='white')

            elif mode == 'color':
                cols_n = max(len(r) for r in rows)
                W = cols_n * cw
                H = len(rows) * ch
                img = Image.new('RGB', (W, H), color='black')
                draw = ImageDraw.Draw(img)
                for ri, row in enumerate(rows):
                    x = 0
                    for char, col in row:
                        draw.text((x, ri * ch), char, font=fnt, fill=col)
                        x += cw

            elif mode == 'halfblock':
                cols_n = max(len(r) for r in rows)
                W = cols_n * cw
                H = len(rows) * ch
                img = Image.new('RGB', (W, H), color='black')
                draw = ImageDraw.Draw(img)
                for ri, row in enumerate(rows):
                    x = 0
                    for char, fg, bg in row:
                        draw.rectangle([x, ri*ch, x+cw-1, ri*ch+ch-1], fill=bg)
                        draw.text((x, ri * ch), char, font=fnt, fill=fg)
                        x += cw

            img.save(path, 'PNG')
            self.status_var.set(f"PNG exported: {os.path.basename(path)} ✓")
        except Exception as exc:
            messagebox.showerror("Export error", str(exc))

    # ─────────────────────────────────────────────────────────────────────────
    #  RESET
    # ─────────────────────────────────────────────────────────────────────────
    def reset_settings(self):
        self.width_var.set(120)
        self.brightness_var.set(1.0)
        self.contrast_var.set(1.1)
        self.saturation_var.set(1.2)
        self.invert_var.set(False)
        self.dither_var.set(False)
        self.live_var.set(False)
        self.charset_var.set("Standard")
        self.edge_var.set("off")
        self.font_size_var.set(9)
        self.custom_chars_var.set("")
        self._update_font_size()
        self.status_var.set("Settings reset ✓")

    # ─────────────────────────────────────────────────────────────────────────
    #  BUTTON STATE
    # ─────────────────────────────────────────────────────────────────────────
    def _set_buttons_state(self, state):
        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, (ttk.Button, tk.Button)):
                    try:
                        child.config(state=state)
                    except Exception:
                        pass
                walk(child)
        walk(self.root)


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    root.resizable(True, True)

    # Try to set a nice icon
    try:
        root.iconbitmap(default='')
    except Exception:
        pass

    app = ASCIIArtConverterPro(root)
    root.mainloop()


if __name__ == "__main__":
    main()
