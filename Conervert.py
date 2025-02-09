import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from PIL import Image, ImageTk, ImageEnhance
import numpy as np
import os

class ASCIIArtConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ASCII Art Converter")
        self.root.geometry("1200x800")
        
        # Configure dark theme colors
        self.colors = {
            'bg': '#1e1e1e',
            'fg': '#ffffff',
            'button': '#2d2d2d',
            'frame': '#252526',
            'highlight': '#007acc'
        }
        
        # ASCII characters from darkest to lightest (reversed for dark theme)
        self.ASCII_CHARS = [".", ",", ":", ";", "+", "*", "?", "%", "S", "#", "@"]
        
        # Initialize variables
        self.image_path = None
        self.original_image = None
        self.preview_photo = None
        
        # Apply dark theme
        self.root.configure(bg=self.colors['bg'])
        self.style = ttk.Style()
        self.setup_dark_theme()
        self.setup_variables()
        self.create_gui()
        
    def setup_dark_theme(self):
        """Configure dark theme styles"""
        self.style.configure('Dark.TFrame', background=self.colors['bg'])
        self.style.configure('Dark.TButton',
            background=self.colors['button'],
            foreground=self.colors['fg'],
            padding=5
        )
        self.style.configure('Dark.TLabelframe',
            background=self.colors['frame'],
            foreground=self.colors['fg'],
            padding=10
        )
        self.style.configure('Dark.TLabelframe.Label',
            background=self.colors['frame'],
            foreground=self.colors['fg']
        )
        self.style.configure('Dark.TLabel',
            background=self.colors['frame'],
            foreground=self.colors['fg']
        )
        self.style.configure('Dark.TSpinbox',
            background=self.colors['button'],
            foreground=self.colors['fg'],
            fieldbackground=self.colors['button']
        )
        
    def setup_variables(self):
        """Initialize tkinter variables"""
        self.width_var = tk.IntVar(value=100)
        self.brightness_var = tk.DoubleVar(value=1.0)
        self.contrast_var = tk.DoubleVar(value=1.0)
        self.invert_var = tk.BooleanVar(value=False)
        
    def create_gui(self):
        """Create the main GUI layout"""
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create main containers
        self.create_top_frame(main_frame)
        self.create_content_frame(main_frame)
        
    def create_top_frame(self, parent):
        """Create the top frame with main controls"""
        top_frame = ttk.Frame(parent, style='Dark.TFrame')
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        buttons = [
            ("Select Image", self.select_image),
            ("Convert to ASCII", self.convert_image),
            ("Save ASCII Art", self.save_ascii)
        ]
        
        for text, command in buttons:
            btn = ttk.Button(
                top_frame,
                text=text,
                command=command,
                style='Dark.TButton'
            )
            btn.pack(side=tk.LEFT, padx=5)
        
    def create_content_frame(self, parent):
        """Create the main content area"""
        content_frame = ttk.Frame(parent, style='Dark.TFrame')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Settings and Preview
        left_frame = ttk.Frame(content_frame, style='Dark.TFrame')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Settings
        settings_frame = ttk.LabelFrame(
            left_frame,
            text="Settings",
            style='Dark.TLabelframe'
        )
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        settings = [
            ("Width (characters):", self.width_var, 20, 200, 1),
            ("Brightness:", self.brightness_var, 0.1, 2.0, 0.1),
            ("Contrast:", self.contrast_var, 0.1, 2.0, 0.1)
        ]
        
        for row, (text, var, min_val, max_val, increment) in enumerate(settings):
            ttk.Label(
                settings_frame,
                text=text,
                style='Dark.TLabel'
            ).grid(row=row, column=0, padx=5, pady=5)
            
            spinbox = ttk.Spinbox(
                settings_frame,
                from_=min_val,
                to=max_val,
                increment=increment,
                textvariable=var,
                width=10,
                style='Dark.TSpinbox'
            )
            spinbox.grid(row=row, column=1, padx=5, pady=5)
        
        # Invert colors checkbox
        ttk.Checkbutton(
            settings_frame,
            text="Invert Colors",
            variable=self.invert_var,
            style='Dark.TCheckbutton'
        ).grid(row=len(settings), column=0, columnspan=2, pady=5)
        
        # Preview
        preview_frame = ttk.LabelFrame(
            left_frame,
            text="Image Preview",
            style='Dark.TLabelframe'
        )
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.preview_label = ttk.Label(preview_frame, style='Dark.TLabel')
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Right side - ASCII Output
        right_frame = ttk.LabelFrame(
            content_frame,
            text="ASCII Output",
            style='Dark.TLabelframe'
        )
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.output_text = scrolledtext.ScrolledText(
            right_frame,
            wrap=tk.NONE,
            font=('Courier', 10),
            bg=self.colors['bg'],
            fg=self.colors['fg'],
            insertbackground=self.colors['fg']
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def select_image(self):
        """Open file dialog to select an image"""
        filetypes = (
            ('Image files', '*.jpg *.jpeg *.png *.bmp *.gif'),
            ('All files', '*.*')
        )
        
        self.image_path = filedialog.askopenfilename(filetypes=filetypes)
        if self.image_path:
            try:
                self.original_image = Image.open(self.image_path)
                self.update_preview()
            except Exception as e:
                messagebox.showerror("Error", f"Could not open image: {str(e)}")
                
    def update_preview(self):
        """Update the image preview"""
        if self.original_image:
            # Resize image to fit preview
            preview_size = (300, 300)
            preview_image = self.original_image.copy()
            preview_image.thumbnail(preview_size, Image.Resampling.LANCZOS)
            
            self.preview_photo = ImageTk.PhotoImage(preview_image)
            self.preview_label.configure(image=self.preview_photo)
            
    def convert_image(self):
        """Convert the image to ASCII art"""
        if not self.original_image:
            messagebox.showwarning("Warning", "Please select an image first!")
            return
            
        try:
            # Process image
            image = self.original_image.copy()
            width = self.width_var.get()
            aspect_ratio = image.size[1] / image.size[0]
            height = int(width * aspect_ratio * 0.55)
            image = image.resize((width, height))
            image = image.convert('L')  # Convert to grayscale
            
            # Apply adjustments
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(self.brightness_var.get())
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(self.contrast_var.get())
            
            # Convert to ASCII
            pixels = np.array(image)
            if self.invert_var.get():
                pixels = 255 - pixels
                
            ascii_art = []
            for row in pixels:
                ascii_row = ''.join(self._pixel_to_ascii(pixel) for pixel in row)
                ascii_art.append(ascii_row)
                
            ascii_str = '\n'.join(ascii_art)
            
            # Update output
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, ascii_str)
            
        except Exception as e:
            messagebox.showerror("Error", f"Conversion error: {str(e)}")
            
    def _pixel_to_ascii(self, pixel_value):
        """Convert a pixel value to an ASCII character"""
        ascii_index = int(pixel_value / 255 * (len(self.ASCII_CHARS) - 1))
        return self.ASCII_CHARS[ascii_index]
        
    def save_ascii(self):
        """Save the ASCII art to a text file"""
        if not self.output_text.get(1.0, tk.END).strip():
            messagebox.showwarning("Warning", "No ASCII art to save!")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.output_text.get(1.0, tk.END))
                messagebox.showinfo("Success", "ASCII art saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {str(e)}")

def main():
    root = tk.Tk()
    app = ASCIIArtConverterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()