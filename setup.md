# 508 Compliant PDF Conversion Agent Setup

## Requirements
- Python 3.8 or higher

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
