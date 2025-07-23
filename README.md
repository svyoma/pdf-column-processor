# PDF Column Processor

A Python application for processing two-column PDF documents. Available in both web (Flask) and desktop (Tkinter) versions.

## Features

- Split two-column PDFs into single-column pages
- Mask left/right columns individually
- Automatic column detection
- Built-in PDF compression
- Preview of processed pages
- Progress tracking (in desktop version)

## Available Versions

### 1. Desktop Application (`pdf_processor.py`)
- Standalone GUI application
- No web server required
- Real-time progress tracking
- Direct file selection
- Saves output in the same directory as input

### 2. Web Application (`app.py`)
- Flask-based web interface
- Preview functionality
- Upload and download capability
- Multiple file processing

## Installation

1. Clone the repository:
```bash
git clone https://github.com/svyoma/pdf-column-processor.git
cd pdf-column-processor
```

2. Install requirements:
```bash
pip install -r requirements.txt
```

## Usage

### Desktop Version
1. Run the desktop application:
```bash
python pdf_processor.py
```
2. Click "Browse" to select a PDF file
3. Choose processing mode (Split or Mask)
4. Click "Process PDF"
5. The processed file will be saved in the same directory as the input file

### Web Version
1. Start the Flask server:
```bash
python app.py
```
2. Open browser and go to `http://localhost:5000`
3. Upload PDF file
4. Select processing mode
5. Click "Process PDF"
6. Download the processed file

## Technical Details

- PDF processing: PyMuPDF (fitz)
- Image processing: OpenCV and Pillow
- Column detection: Vertical whitespace analysis
- Compression: JPEG optimization + PDF deflate
- GUI: Tkinter (desktop) / HTML+CSS (web)

## Requirements

- Python 3.7+
- PyMuPDF (fitz)
- NumPy
- OpenCV
- Pillow
- Flask (for web version)

## Building Executable (Windows)

To create a standalone executable for the desktop version:

1. Install PyInstaller:
```bash
pip install pyinstaller
```

2. Create the executable:
```bash
pyinstaller --onefile --noconsole --name PDFColumnProcessor pdf_processor.py
```

The executable will be created in the `dist` folder.

## License

MIT License

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
