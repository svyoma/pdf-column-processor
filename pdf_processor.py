import os
import fitz
import numpy as np
import cv2
from PIL import Image
from io import BytesIO
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter.messagebox import showinfo, showerror

PROCESS_DPI = 180
JPEG_QUALITY = 80

def detect_split_points(image, num_cols):
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    vertical_sum = np.sum(thresh, axis=0).astype(np.float32)
    vertical_sum = cv2.GaussianBlur(vertical_sum, (51, 1), 0).flatten()

    w = len(vertical_sum)
    points = []
    for k in range(1, num_cols):
        expected = int(w * k / num_cols)
        margin = int(w * 0.08)
        lo = max(0, expected - margin)
        hi = min(w, expected + margin)
        split = int(np.argmin(vertical_sum[lo:hi]) + lo)
        points.append(split)
    return sorted(points)

class PDFProcessor:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("PDF Column Processor")
        self.window.geometry("600x420")
        self.setup_ui()

    def setup_ui(self):
        frame = ttk.Frame(self.window, padding="10")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        ttk.Label(frame, text="Select PDF File:").grid(row=0, column=0, sticky=tk.W)
        self.file_path = tk.StringVar()
        ttk.Entry(frame, textvariable=self.file_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="Browse", command=self.browse_file).grid(row=0, column=2)

        ttk.Label(frame, text="Processing Mode:").grid(row=1, column=0, sticky=tk.W, pady=10)
        self.mode = tk.StringVar(value="split")
        ttk.Radiobutton(frame, text="Split Columns", variable=self.mode, value="split").grid(row=1, column=1, sticky=tk.W)
        ttk.Radiobutton(frame, text="Mask Columns", variable=self.mode, value="mask").grid(row=2, column=1, sticky=tk.W)

        ttk.Label(frame, text="Number of Columns:").grid(row=3, column=0, sticky=tk.W, pady=10)
        self.num_cols = tk.IntVar(value=2)
        col_combo = ttk.Combobox(frame, textvariable=self.num_cols, values=[2, 3, 4, 5], width=5, state="readonly")
        col_combo.grid(row=3, column=1, sticky=tk.W)

        ttk.Button(frame, text="Process PDF", command=self.process_file).grid(row=4, column=1, pady=20)

        self.progress = ttk.Progressbar(frame, length=400, mode='determinate')
        self.progress.grid(row=5, column=0, columnspan=3, pady=10)

    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if filename:
            self.file_path.set(filename)

    def process_file(self):
        if not self.file_path.get():
            showerror("Error", "Please select a PDF file")
            return

        try:
            input_path = self.file_path.get()
            output_dir = os.path.dirname(input_path)
            mode = self.mode.get()
            num_cols = self.num_cols.get()
            output_path = os.path.join(output_dir, f"processed_{os.path.basename(input_path)}")

            doc = fitz.open(input_path)
            out = fitz.open()
            total_pages = len(doc)

            for i, page in enumerate(doc):
                self.progress['value'] = (i + 1) / total_pages * 100
                self.window.update_idletasks()

                pix = page.get_pixmap(dpi=PROCESS_DPI)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                w, h = img.size
                splits = detect_split_points(img, num_cols)
                edges = [0] + splits + [w]

                if mode == "split":
                    for j in range(num_cols):
                        part = img.crop((edges[j], 0, edges[j + 1], h))
                        temp_page = out.new_page(width=part.width, height=part.height)
                        buf = BytesIO()
                        part.convert("RGB").save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
                        buf.seek(0)
                        temp_page.insert_image(temp_page.rect, stream=buf)
                else:  # mask
                    for j in range(num_cols):
                        masked = img.copy()
                        if edges[j] > 0:
                            masked.paste((255, 255, 255), box=(0, 0, edges[j], h))
                        if edges[j + 1] < w:
                            masked.paste((255, 255, 255), box=(edges[j + 1], 0, w, h))
                        temp_page = out.new_page(width=w, height=h)
                        buf = BytesIO()
                        masked.convert("RGB").save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
                        buf.seek(0)
                        temp_page.insert_image(temp_page.rect, stream=buf)

            out.save(output_path, deflate=True, garbage=3, clean=True)
            doc.close()
            out.close()

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
