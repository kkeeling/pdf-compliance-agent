# 508 Compliant PDF Conversion Agent

This project provides a tool for analyzing and converting PDF files to ensure they meet Section 508 compliance standards for accessibility.

## Features

- Extract text from PDF files
- Analyze PDF accessibility, including:
  - Missing alt text for images
  - Low-contrast text
  - Improper reading order
  - Lack of document structure
- Convert PDFs to a more accessible format:
  - Add basic structure
  - Improve text contrast

## Requirements

- Python 3.8 or higher
- See `requirements.txt` for a list of required Python packages.

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd <project-directory>
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Verify the installation:
   ```
   python -c "import fitz, pdfminer, openai, reportlab; print('All dependencies installed successfully!')"
   ```

If you encounter any issues during setup, please refer to the individual library documentation or contact the project maintainer.

## Usage

Run the script from the command line:

```
python pdf_conversion_agent.py input_file.pdf output_file.pdf [--verbose]
```

- `input_file.pdf`: Path to the input PDF file
- `output_file.pdf`: Path to save the compliant PDF file
- `--verbose`: (Optional) Enable verbose output

## Contributing

Contributions to improve the 508 Compliant PDF Conversion Agent are welcome. Please feel free to submit a Pull Request.

## License

[MIT License](https://opensource.org/licenses/MIT)
