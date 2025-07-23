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

# --- Utility: Convert PIL image to in-memory PNG bytes ---
def pil_image_to_bytes(img):
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# --- Auto-detect column split using vertical whitespace ---
def detect_split_point(image: Image.Image) -> int:
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

# --- Compress PDF ---
def compress_pdf(input_path, output_path):
    try:
        doc = fitz.open(input_path)
        out = fitz.open()

        for page in doc:
            # Reduce DPI and use JPEG compression for images
            pix = page.get_pixmap(dpi=120, alpha=False)  # Lower DPI and remove alpha channel
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Convert to JPEG with compression
            img_buf = BytesIO()
            img.save(img_buf, format="JPEG", quality=85, optimize=True)
            img_buf.seek(0)
            
            # Create new page
            temp_page = out.new_page(width=page.rect.width, height=page.rect.height)
            temp_page.insert_image(temp_page.rect, stream=img_buf)
            
            # Clean up
            pix = None
            img = None
            img_buf = None

        # Save with compression
        out.save(output_path,
                deflate=True,  # Enable deflate compression
                garbage=3,     # Enable garbage collection
                clean=True)    # Clean unused elements
    finally:
        # Ensure documents are properly closed
        if 'doc' in locals():
            doc.close()
        if 'out' in locals():
            out.close()

# --- Main processor: Split or Mask mode ---
def process_pdf(pdf_path, mode='split'):
    temp_output = os.path.join(UPLOAD_FOLDER, f"temp_{mode}_output.pdf")
    final_output = os.path.join(UPLOAD_FOLDER, f"{mode}_output.pdf")
    doc = None
    out = None
    preview_images = []

    try:
        # Open PDF files
        doc = fitz.open(pdf_path)
        out = fitz.open()

        for i, page in enumerate(doc):
            # Use lower DPI for better performance
            pix = page.get_pixmap(dpi=200)  # Reduced from 300 to 200 for better performance
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            w, h = img.size
            split_col = detect_split_point(img)

            if mode == 'split':
                left = img.crop((0, 0, split_col, h))
                right = img.crop((split_col, 0, w, h))

                for j, part in enumerate((left, right)):
                    if i == 0:
                        preview_path = os.path.join(UPLOAD_FOLDER, f"preview_{j}.png")
                        part.save(preview_path)
                        preview_images.append(f"/{preview_path}")

                    part_rgb = part.convert("RGB")
                    temp_page = out.new_page(width=part.width, height=part.height)
                    img_buf = pil_image_to_bytes(part_rgb)
                    temp_page.insert_image(temp_page.rect, stream=img_buf)

            elif mode == 'mask':
                left_masked = img.copy()
                right_masked = img.copy()

                left_masked.paste((255, 255, 255), box=(split_col, 0, w, h))
                right_masked.paste((255, 255, 255), box=(0, 0, split_col, h))

                for j, masked in enumerate((left_masked, right_masked)):
                    if i == 0:
                        preview_path = os.path.join(UPLOAD_FOLDER, f"preview_{j}.png")
                        masked.save(preview_path)
                        preview_images.append(f"/{preview_path}")

                    masked_rgb = masked.convert("RGB")
                    temp_page = out.new_page(width=w, height=h)
                    img_buf = pil_image_to_bytes(masked_rgb)
                    temp_page.insert_image(temp_page.rect, stream=img_buf)

            # Clean up page resources
            pix = None
            img = None

        # Save the initial output
        out.save(temp_output)
        
        # Compress the output
        compress_pdf(temp_output, final_output)
        
        # Clean up temporary file
        try:
            os.remove(temp_output)
        except:
            pass

        return final_output, preview_images

    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        raise

    finally:
        # Clean up and close PDF files
        if doc:
            doc.close()
        if out:
            out.close()

# --- Flask routes ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        mode = request.form['mode']
        file = request.files['pdf_file']

        if file and file.filename.endswith('.pdf'):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)

            # Process the PDF
            output_pdf_path, preview_images = process_pdf(path, mode)
            
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