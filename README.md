# ASCII Art Converter

Converts images and animated GIFs into ASCII art. Supports full color, half-block high-resolution mode, and grayscale. Runs as a desktop app built with Python and Tkinter.

![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **3 render modes** — Color ASCII, Half-Block HD (▀ characters, double vertical resolution), Grayscale
- **Animated GIF support** — converts every frame, plays back in the app with scrubber and speed control
- **Export options** — save as `.txt`, render to `.png`, or export a self-contained `.html` file (animated for GIFs)
- **Floyd-Steinberg dithering** for smoother gradients in grayscale mode
- **8 character sets** including Braille, Unicode blocks, and a custom input field
- **Live preview** mode — reconverts on every slider change
- Edge enhancement filters (smooth, sharpen, find edges)
- Zoom in/out on the output with `Ctrl +` / `Ctrl -`

---

## Requirements

Python 3.8 or newer, plus a few packages:

```
pip install pillow numpy
```

Tkinter is included with most Python installations. On Linux you may need:

```
sudo apt install python3-tk
```

---

## Running it

```
python ascii_converter_pro.py
```

---

## How to use

1. Click **⬆ Load** (or `Ctrl+O`) to open an image or GIF
2. Pick a render mode on the left — Color is the default
3. Adjust width, brightness, contrast, saturation with the sliders
4. Hit **▶ Convert** (or `Ctrl+Enter`)
5. Use the export buttons in the header to save your result

For GIFs, a playback bar appears after converting. Use the scrubber to jump to any frame, adjust speed, or pause with `Space`.

---

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+O` | Load image |
| `Ctrl+Enter` | Convert |
| `Ctrl+S` | Save as .txt |
| `Ctrl+E` | Export HTML |
| `Ctrl+P` | Export PNG |
| `Ctrl+C` | Copy to clipboard |
| `Ctrl+` / `Ctrl-` | Zoom output font |
| `Space` | Play / pause GIF |

---

## Render modes explained

**Color ASCII** — each character is colored with the original pixel's RGB value. Looks best at smaller font sizes where the color does most of the work.

**Half-Block HD** — uses the `▀` block character. The top half gets the foreground color, the bottom half gets the background color. This effectively doubles the vertical resolution compared to regular ASCII, so you get much more detail. Works especially well for GIFs.

**Grayscale** — classic ASCII art. Enable Floyd-Steinberg dithering for smoother tones at lower widths.

---

## Export formats

**HTML export** — produces a single `.html` file with inline CSS. For GIFs, this includes a JavaScript player with a scrubber and speed control. Open it in any browser, no internet needed.

**PNG export** — renders the ASCII art to an actual image using a monospace font. For GIFs you can export all frames to a folder as numbered PNGs, or just the current frame.

---

## Tips

- Wider = more detail, but slower to convert and harder to read. 80–150 chars is a good range.
- Boost contrast a bit (1.2–1.5) for images with flat areas — it brings out more character variation.
- Half-Block mode with a small font size (6–8px) gets very close to the original image.
- For GIFs, lower the width first — converting 60 frames at width 200 takes a while.
- The HTML export for GIFs is a good way to share results since it works in any browser without needing the app.

---

## License

MIT — do whatever you want with it.
