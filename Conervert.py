import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from PIL import Image, ImageTk, ImageEnhance, ImageDraw, ImageFont
import numpy as np
import os
import threading

class ASCIIArtConverterGUI:
    def __init__(self, root):
        """Initialize the GUI, variables, and bind keyboard shortcuts."""
        self.root = root
        self.root.title("ASCII Art Converter")
        self.root.geometry("1300x950")
        
        # Dark theme colors
        self.colors = {
            'bg': '#1e1e1e',
            'fg': '#ffffff',
            'button': '#3d3d3d',
            'frame': '#252526',
            'input_bg': '#333333',
            'input_fg': '#ffffff',
            'highlight': '#007acc'
        }
        
        # Preset ASCII character sets (customizable)
        self.ascii_char_sets = {
            "Default": [".", ",", ":", ";", "+", "*", "?", "%", "S", "#", "@"],
            "Dense": ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."],
            "Sparse": [" ", ".", "-", ":", "=", "+", "*", "#", "%", "@"]
        }
        self.ASCII_CHARS = self.ascii_char_sets["Default"]
        
        # Image variables
        self.image_path = None
        self.original_image = None
        self.preview_photo = None
        
        # Conversion settings variables
        self.width_var = tk.IntVar(value=100)
        self.brightness_var = tk.DoubleVar(value=1.0)
        self.contrast_var = tk.DoubleVar(value=1.0)
        self.invert_var = tk.BooleanVar(value=False)
        self.live_preview_var = tk.BooleanVar(value=False)
        self.ascii_set_var = tk.StringVar(value="Default")
        
        # Progress variables
        self.progress_var = tk.IntVar(value=0)
        self.status_var = tk.StringVar(value="Idle")
        
        # Setup theme, layout, and keyboard shortcuts
        self.setup_dark_theme()
        self.create_gui()
        self.bind_shortcuts()
        
    def setup_dark_theme(self):
        """Configure dark theme styles for the app."""
        self.root.configure(bg=self.colors['bg'])
        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure('Dark.TFrame', background=self.colors['bg'])
        self.style.configure('Dark.TButton', background=self.colors['button'],
                             foreground=self.colors['fg'], padding=5)
        self.style.map('Dark.TButton',
                       background=[('active', self.colors['highlight'])],
                       foreground=[('active', 'white')])
        self.style.configure('Dark.TLabelframe', background=self.colors['frame'],
                             foreground=self.colors['fg'], padding=10)
        self.style.configure('Dark.TLabelframe.Label', background=self.colors['frame'],
                             foreground=self.colors['fg'])
        self.style.configure('Dark.TLabel', background=self.colors['frame'],
                             foreground=self.colors['fg'])
        self.style.configure('Dark.TCheckbutton', background=self.colors['frame'],
                             foreground=self.colors['fg'])
        
    def create_gui(self):
        """Build the main GUI layout with top buttons, content area, and status bar."""
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.create_top_frame(main_frame)
        self.create_content_frame(main_frame)
        self.create_status_bar(main_frame)
        
    def create_top_frame(self, parent):
        """Create the top frame with control buttons and additional export button."""
        top_frame = ttk.Frame(parent, style='Dark.TFrame')
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        buttons = [
            ("Select Image", self.select_image),
            ("Convert to ASCII", self.start_conversion_thread),
            ("Copy to Clipboard", self.copy_to_clipboard),
            ("Save ASCII Art", self.save_ascii),
            ("Export as Image", self.export_as_image),
            ("Reset Settings", self.reset_settings)
        ]
        for text, command in buttons:
            btn = ttk.Button(top_frame, text=text, command=command, style='Dark.TButton')
            btn.pack(side=tk.LEFT, padx=5)
    
    def create_content_frame(self, parent):
        """Create the content area with settings, image preview, and ASCII output."""
        content_frame = ttk.Frame(parent, style='Dark.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel: Settings and Image Preview
        left_frame = ttk.Frame(content_frame, style='Dark.TFrame')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Settings panel
        settings_frame = ttk.LabelFrame(left_frame, text="Settings", style='Dark.TLabelframe')
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Width setting
        label_width = ttk.Label(settings_frame, text="Width (characters):", style='Dark.TLabel')
        label_width.grid(row=0, column=0, padx=5, pady=5, sticky='w')
        spin_width = ttk.Spinbox(settings_frame, from_=20, to=200, increment=1,
                                 textvariable=self.width_var, width=10, style='Dark.TSpinbox',
                                 command=self.on_parameter_change)
        spin_width.grid(row=0, column=1, padx=5, pady=5)
        spin_width.configure(background=self.colors['input_bg'], foreground=self.colors['input_fg'])
        
        # Brightness slider
        label_brightness = ttk.Label(settings_frame, text="Brightness:", style='Dark.TLabel')
        label_brightness.grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.brightness_scale = tk.Scale(settings_frame, from_=0.1, to=2.0, orient=tk.HORIZONTAL,
                                         resolution=0.1, variable=self.brightness_var,
                                         bg=self.colors['frame'], fg=self.colors['fg'],
                                         highlightbackground=self.colors['frame'],
                                         command=lambda val: self.on_parameter_change())
        self.brightness_scale.grid(row=1, column=1, padx=5, pady=5)
        
        # Contrast slider
        label_contrast = ttk.Label(settings_frame, text="Contrast:", style='Dark.TLabel')
        label_contrast.grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.contrast_scale = tk.Scale(settings_frame, from_=0.1, to=2.0, orient=tk.HORIZONTAL,
                                       resolution=0.1, variable=self.contrast_var,
                                       bg=self.colors['frame'], fg=self.colors['fg'],
                                       highlightbackground=self.colors['frame'],
                                       command=lambda val: self.on_parameter_change())
        self.contrast_scale.grid(row=2, column=1, padx=5, pady=5)
        
        # Invert Colors checkbox
        invert_check = ttk.Checkbutton(settings_frame, text="Invert Colors",
                                       variable=self.invert_var,
                                       style='Dark.TCheckbutton',
                                       command=self.on_parameter_change)
        invert_check.grid(row=3, column=0, columnspan=2, pady=5, sticky='w')
        
        # ASCII Character Set combobox
        label_ascii_set = ttk.Label(settings_frame, text="ASCII Char Set:", style='Dark.TLabel')
        label_ascii_set.grid(row=4, column=0, padx=5, pady=5, sticky='w')
        ascii_combo = ttk.Combobox(settings_frame, values=list(self.ascii_char_sets.keys()),
                                   textvariable=self.ascii_set_var, state="readonly")
        ascii_combo.grid(row=4, column=1, padx=5, pady=5)
        ascii_combo.bind("<<ComboboxSelected>>", self.update_ascii_char_set)
        
        # Live Preview checkbox
        live_check = ttk.Checkbutton(settings_frame, text="Live Preview",
                                     variable=self.live_preview_var,
                                     style='Dark.TCheckbutton')
        live_check.grid(row=5, column=0, columnspan=2, pady=5, sticky='w')
        
        # Image Preview panel
        preview_frame = ttk.LabelFrame(left_frame, text="Image Preview", style='Dark.TLabelframe')
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.preview_label = ttk.Label(preview_frame, style='Dark.TLabel')
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Right panel: ASCII Output
        right_frame = ttk.LabelFrame(content_frame, text="ASCII Output", style='Dark.TLabelframe')
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.output_text = scrolledtext.ScrolledText(right_frame, wrap=tk.NONE,
                                                      font=('Courier', 10),
                                                      bg=self.colors['input_bg'],
                                                      fg=self.colors['input_fg'],
                                                      insertbackground=self.colors['input_fg'])
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_status_bar(self, parent):
        """Create a status bar with a progress bar and status label."""
        status_frame = ttk.Frame(parent, style='Dark.TFrame')
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.progress_bar = ttk.Progressbar(status_frame, orient='horizontal',
                                            mode='determinate', variable=self.progress_var)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, style='Dark.TLabel')
        self.status_label.pack(side=tk.LEFT, padx=5)
    
    def bind_shortcuts(self):
        """Bind common keyboard shortcuts."""
        self.root.bind("<Control-o>", lambda event: self.select_image())
        self.root.bind("<Control-s>", lambda event: self.save_ascii())
        self.root.bind("<Control-e>", lambda event: self.export_as_image())
    
    def select_image(self):
        """Open a file dialog to select an image and update preview."""
        filetypes = (
            ('Image files', '*.jpg *.jpeg *.png *.bmp *.gif'),
            ('All files', '*.*')
        )
        self.image_path = filedialog.askopenfilename(filetypes=filetypes)
        if self.image_path:
            try:
                self.original_image = Image.open(self.image_path)
                self.update_preview()
                self.status_var.set("Image loaded.")
            except Exception as e:
                messagebox.showerror("Error", f"Could not open image: {str(e)}")
    
    def update_preview(self):
        """Update the image preview area with a resized version of the loaded image."""
        if self.original_image:
            preview_size = (300, 300)
            preview_image = self.original_image.copy()
            preview_image.thumbnail(preview_size, Image.Resampling.LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(preview_image)
            self.preview_label.configure(image=self.preview_photo)
    
    def start_conversion_thread(self):
        """Start the conversion in a background thread."""
        if not self.original_image:
            messagebox.showwarning("Warning", "Please select an image first!")
            return
        
        # Disable buttons during conversion
        self.disable_buttons()
        self.status_var.set("Converting...")
        self.progress_var.set(0)
        
        thread = threading.Thread(target=self.convert_image_worker, daemon=True)
        thread.start()
    
    def convert_image_worker(self):
        """Worker function to convert image to ASCII art with progress updates."""
        try:
            image = self.original_image.copy()
            width = self.width_var.get()
            aspect_ratio = image.size[1] / image.size[0]
            height = int(width * aspect_ratio * 0.55)
            image = image.resize((width, height))
            image = image.convert('L')  # Convert to grayscale
            
            # Apply brightness and contrast adjustments
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(self.brightness_var.get())
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(self.contrast_var.get())
            
            pixels = np.array(image)
            if self.invert_var.get():
                pixels = 255 - pixels
            
            # Update ASCII set based on user selection
            self.ASCII_CHARS = self.ascii_char_sets[self.ascii_set_var.get()]
            
            ascii_art = []
            total_rows = pixels.shape[0]
            for i, row in enumerate(pixels):
                ascii_row = ''.join(self._pixel_to_ascii(pixel) for pixel in row)
                ascii_art.append(ascii_row)
                # Update progress every 10 rows
                if i % 10 == 0 or i == total_rows - 1:
                    progress = int((i + 1) / total_rows * 100)
                    self.root.after(0, self.progress_var.set, progress)
            
            ascii_str = '\n'.join(ascii_art)
            # Update the output text in the main thread
            self.root.after(0, self.update_ascii_output, ascii_str)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Conversion error: {str(e)}"))
        finally:
            self.root.after(0, self.enable_buttons)
            self.root.after(0, self.status_var.set, "Conversion complete.")
    
    def update_ascii_output(self, ascii_str):
        """Update the ASCII art output widget."""
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, ascii_str)
    
    def _pixel_to_ascii(self, pixel_value):
        """Map a pixel value (0-255) to an ASCII character based on the current set."""
        index = int(pixel_value / 255 * (len(self.ASCII_CHARS) - 1))
        return self.ASCII_CHARS[index]
    
    def copy_to_clipboard(self):
        """Copy the generated ASCII art to the clipboard."""
        ascii_text = self.output_text.get(1.0, tk.END).strip()
        if not ascii_text:
            messagebox.showwarning("Warning", "No ASCII art to copy!")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(ascii_text)
        messagebox.showinfo("Copied", "ASCII art copied to clipboard!")
    
    def save_ascii(self):
        """Save the ASCII art as a text file."""
        ascii_text = self.output_text.get(1.0, tk.END).strip()
        if not ascii_text:
            messagebox.showwarning("Warning", "No ASCII art to save!")
            return
        
        file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                                 filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(ascii_text)
                messagebox.showinfo("Success", "ASCII art saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {str(e)}")
    
    def export_as_image(self):
        """Export the ASCII art as an image file by rendering text onto a canvas."""
        ascii_text = self.output_text.get(1.0, tk.END).strip()
        if not ascii_text:
            messagebox.showwarning("Warning", "No ASCII art to export!")
            return
        
        # Use a monospaced font (default font)
        font = ImageFont.load_default()
        lines = ascii_text.splitlines()
        if not lines:
            return
        
        # Determine image size from text
        max_width = max(font.getsize(line)[0] for line in lines)
        total_height = font.getsize(ascii_text)[1] * len(lines)
        img = Image.new("RGB", (max_width, total_height), color="black")
        draw = ImageDraw.Draw(img)
        
        y = 0
        for line in lines:
            draw.text((0, y), line, font=font, fill="white")
            y += font.getsize(line)[1]
        
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if file_path:
            try:
                img.save(file_path)
                messagebox.showinfo("Success", "ASCII art image exported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Could not export image: {str(e)}")
    
    def reset_settings(self):
        """Reset all settings to default values."""
        self.width_var.set(100)
        self.brightness_var.set(1.0)
        self.contrast_var.set(1.0)
        self.invert_var.set(False)
        self.live_preview_var.set(False)
        self.ascii_set_var.set("Default")
        self.ASCII_CHARS = self.ascii_char_sets["Default"]
        self.brightness_scale.set(1.0)
        self.contrast_scale.set(1.0)
        self.status_var.set("Settings reset.")
        messagebox.showinfo("Reset", "Settings have been reset.")
    
    def on_parameter_change(self, event=None):
        """Handle changes in parameters; if live preview is enabled, reconvert the image."""
        if self.live_preview_var.get() and self.original_image:
            self.start_conversion_thread()
    
    def update_ascii_char_set(self, event=None):
        """Update the ASCII character set based on combobox selection."""
        self.ASCII_CHARS = self.ascii_char_sets[self.ascii_set_var.get()]
        if self.live_preview_var.get() and self.original_image:
            self.start_conversion_thread()
    
    def disable_buttons(self):
        """Disable control buttons during conversion."""
        for widget in self.root.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button):
                    child.config(state=tk.DISABLED)
    
    def enable_buttons(self):
        """Re-enable control buttons after conversion."""
        for widget in self.root.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button):
                    child.config(state=tk.NORMAL)

def main():
    root = tk.Tk()
    app = ASCIIArtConverterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
