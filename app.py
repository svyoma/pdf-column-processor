import os
import fitz  # PyMuPDF
import numpy as np
import cv2
from PIL import Image
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from io import BytesIO

app = Flask(__name__)
UPLOAD_FOLDER = 'static/processed'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

PROCESS_DPI = 150
JPEG_QUALITY = 75

def pil_to_jpeg_bytes(img):
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    buf.seek(0)
    return buf

def detect_split_points(image: Image.Image, num_cols: int) -> list[int]:
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

def compress_pdf(input_path, output_path):
    try:
        doc = fitz.open(input_path)
        out = fitz.open()
        for page in doc:
            pix = page.get_pixmap(dpi=110, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_buf = BytesIO()
            img.save(img_buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            img_buf.seek(0)
            temp_page = out.new_page(width=page.rect.width, height=page.rect.height)
            temp_page.insert_image(temp_page.rect, stream=img_buf)
            pix = None
            img = None
        out.save(output_path, deflate=True, garbage=3, clean=True)
    finally:
        if 'doc' in locals():
            doc.close()
        if 'out' in locals():
            out.close()

def process_pdf(pdf_path, mode='split', num_cols=2):
    final_output = os.path.join(UPLOAD_FOLDER, f"{mode}_output.pdf")
    doc = None
    out = None
    preview_images = []

    try:
        doc = fitz.open(pdf_path)
        out = fitz.open()

        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=PROCESS_DPI)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            w, h = img.size
            splits = detect_split_points(img, num_cols)
            edges = [0] + splits + [w]

            if mode == 'split':
                for j in range(num_cols):
                    part = img.crop((edges[j], 0, edges[j + 1], h))
                    if i == 0:
                        preview_path = os.path.join(UPLOAD_FOLDER, f"preview_{j}.png")
                        part.save(preview_path)
                        preview_images.append(f"/{preview_path}")
                    temp_page = out.new_page(width=part.width, height=part.height)
                    temp_page.insert_image(temp_page.rect, stream=pil_to_jpeg_bytes(part))

            elif mode == 'mask':
                for j in range(num_cols):
                    masked = img.copy()
                    # White out everything except column j
                    if edges[j] > 0:
                        masked.paste((255, 255, 255), box=(0, 0, edges[j], h))
                    if edges[j + 1] < w:
                        masked.paste((255, 255, 255), box=(edges[j + 1], 0, w, h))
                    if i == 0:
                        preview_path = os.path.join(UPLOAD_FOLDER, f"preview_{j}.png")
                        masked.save(preview_path)
                        preview_images.append(f"/{preview_path}")
                    temp_page = out.new_page(width=w, height=h)
                    temp_page.insert_image(temp_page.rect, stream=pil_to_jpeg_bytes(masked))

            pix = None
            img = None

        out.save(final_output, deflate=True, garbage=3, clean=True)

        return final_output, preview_images

    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        raise
    finally:
        if doc:
            doc.close()
        if out:
            out.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        mode = request.form['mode']
        num_cols = int(request.form.get('num_cols', 2))
        file = request.files['pdf_file']

        if file and file.filename.endswith('.pdf'):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)

            if mode == 'compress':
                output_path = os.path.join(UPLOAD_FOLDER, "compressed_output.pdf")
                compress_pdf(path, output_path)
                return render_template('index.html',
                                       download_link='/' + output_path)

            output_pdf_path, preview_images = process_pdf(path, mode, num_cols)
            return render_template('index.html',
                                   preview_images=preview_images,
                                   download_link='/' + output_pdf_path)

        return "Invalid file type. Please upload a PDF."

    return render_template('index.html')

@app.route('/static/processed/<path:filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
