import os
import sys
import fitz
import numpy as np
import cv2
from PIL import Image
from io import BytesIO
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter.messagebox import showinfo, showerror

class PDFProcessor:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("PDF Column Processor")
        self.window.geometry("600x400")
        self.setup_ui()

    def setup_ui(self):
        # File selection
        frame = ttk.Frame(self.window, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        ttk.Label(frame, text="Select PDF File:").grid(row=0, column=0, sticky=tk.W)
        self.file_path = tk.StringVar()
        ttk.Entry(frame, textvariable=self.file_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="Browse", command=self.browse_file).grid(row=0, column=2)

        # Mode selection
        ttk.Label(frame, text="Processing Mode:").grid(row=1, column=0, sticky=tk.W, pady=10)
        self.mode = tk.StringVar(value="split")
        ttk.Radiobutton(frame, text="Split Columns", variable=self.mode, value="split").grid(row=1, column=1, sticky=tk.W)
        ttk.Radiobutton(frame, text="Mask Columns", variable=self.mode, value="mask").grid(row=2, column=1, sticky=tk.W)

        # Process button
        ttk.Button(frame, text="Process PDF", command=self.process_file).grid(row=3, column=1, pady=20)

        # Progress bar
        self.progress = ttk.Progressbar(frame, length=400, mode='determinate')
        self.progress.grid(row=4, column=0, columnspan=3, pady=10)

    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if filename:
            self.file_path.set(filename)

    def detect_split_point(self, image):
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        vertical_sum = np.sum(thresh, axis=0)
        vertical_sum = cv2.GaussianBlur(vertical_sum.astype(np.float32), (51, 1), 0)
        mid = len(vertical_sum) // 2
        margin = int(len(vertical_sum) * 0.2)
        left = max(0, mid - margin)
        right = min(len(vertical_sum), mid + margin)
        split_col = np.argmin(vertical_sum[left:right]) + left
        return split_col

    def process_file(self):
        if not self.file_path.get():
            showerror("Error", "Please select a PDF file")
            return

        try:
            input_path = self.file_path.get()
            output_dir = os.path.dirname(input_path)
            mode = self.mode.get()
            output_path = os.path.join(output_dir, f"processed_{os.path.basename(input_path)}")

            doc = fitz.open(input_path)
            out = fitz.open()
            total_pages = len(doc)

            for i, page in enumerate(doc):
                # Update progress
                self.progress['value'] = (i + 1) / total_pages * 100
                self.window.update_idletasks()

                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                w, h = img.size
                split_col = self.detect_split_point(img)

                if mode == "split":
                    left = img.crop((0, 0, split_col, h))
                    right = img.crop((split_col, 0, w, h))
                    for part in (left, right):
                        part_rgb = part.convert("RGB")
                        temp_page = out.new_page(width=part.width, height=part.height)
                        img_buf = BytesIO()
                        part_rgb.save(img_buf, format="JPEG", quality=85, optimize=True)
                        img_buf.seek(0)
                        temp_page.insert_image(temp_page.rect, stream=img_buf)
                else:  # mask mode
                    left_masked = img.copy()
                    right_masked = img.copy()
                    left_masked.paste((255, 255, 255), box=(split_col, 0, w, h))
                    right_masked.paste((255, 255, 255), box=(0, 0, split_col, h))
                    for masked in (left_masked, right_masked):
                        masked_rgb = masked.convert("RGB")
                        temp_page = out.new_page(width=w, height=h)
                        img_buf = BytesIO()
                        masked_rgb.save(img_buf, format="JPEG", quality=85, optimize=True)
                        img_buf.seek(0)
                        temp_page.insert_image(temp_page.rect, stream=img_buf)

            # Save with compression
            out.save(output_path,
                    deflate=True,
                    garbage=3,
                    clean=True)

            showinfo("Success", f"PDF processed successfully!\nSaved as: {output_path}")
            self.progress['value'] = 0

        except Exception as e:
            showerror("Error", f"An error occurred: {str(e)}")
            self.progress['value'] = 0

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = PDFProcessor()
    app.run()
