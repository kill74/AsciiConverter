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
        
        # ASCII characters from darkest to lightest
        self.ASCII_CHARS = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", "."]
        
        # Initialize variables
        self.image_path = None
        self.original_image = None
        self.preview_photo = None
        
        self.setup_variables()
        self.create_gui()
        self.setup_styles()
        
    def setup_variables(self):
        """Initialize tkinter variables"""
        self.width_var = tk.IntVar(value=100)
        self.brightness_var = tk.DoubleVar(value=1.0)
        self.contrast_var = tk.DoubleVar(value=1.0)
        
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.configure('Primary.TButton', padding=5)
        style.configure('Settings.TLabelframe', padding=10)
        
    def create_gui(self):
        """Create the main GUI layout"""
        # Create main containers
        self.create_top_frame()
        self.create_content_frame()
        
    def create_top_frame(self):
        """Create the top frame with main controls"""
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Select Image Button
        select_btn = ttk.Button(
            top_frame, 
            text="Select Image", 
            command=self.select_image,
            style='Primary.TButton'
        )
        select_btn.pack(side=tk.LEFT, padx=5)
        
        # Convert Button
        convert_btn = ttk.Button(
            top_frame, 
            text="Convert to ASCII", 
            command=self.convert_image,
            style='Primary.TButton'
        )
        convert_btn.pack(side=tk.LEFT, padx=5)
        
        # Save Button
        save_btn = ttk.Button(
            top_frame, 
            text="Save ASCII Art", 
            command=self.save_ascii,
            style='Primary.TButton'
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
    def create_content_frame(self):
        """Create the main content area"""
        content_frame = ttk.Frame(self.root, padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left side - Settings and Preview
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Settings
        settings_frame = ttk.LabelFrame(
            left_frame, 
            text="Settings", 
            style='Settings.TLabelframe'
        )
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Width setting
        ttk.Label(settings_frame, text="Width (characters):").grid(row=0, column=0, padx=5, pady=5)
        width_spin = ttk.Spinbox(
            settings_frame, 
            from_=20, 
            to=200, 
            textvariable=self.width_var,
            width=10
        )
        width_spin.grid(row=0, column=1, padx=5, pady=5)
        
        # Brightness setting
        ttk.Label(settings_frame, text="Brightness:").grid(row=1, column=0, padx=5, pady=5)
        brightness_spin = ttk.Spinbox(
            settings_frame, 
            from_=0.1, 
            to=2.0, 
            increment=0.1,
            textvariable=self.brightness_var,
            width=10
        )
        brightness_spin.grid(row=1, column=1, padx=5, pady=5)
        
        # Contrast setting
        ttk.Label(settings_frame, text="Contrast:").grid(row=2, column=0, padx=5, pady=5)
        contrast_spin = ttk.Spinbox(
            settings_frame, 
            from_=0.1, 
            to=2.0, 
            increment=0.1,
            textvariable=self.contrast_var,
            width=10
        )
        contrast_spin.grid(row=2, column=1, padx=5, pady=5)
        
        # Preview
        preview_frame = ttk.LabelFrame(left_frame, text="Image Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Right side - ASCII Output
        right_frame = ttk.LabelFrame(content_frame, text="ASCII Output")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.output_text = scrolledtext.ScrolledText(
            right_frame, 
            wrap=tk.NONE,
            font=('Courier', 10)
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