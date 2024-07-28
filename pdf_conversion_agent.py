import fitz  # PyMuPDF
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams, LTTextBox, LTImage
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
import openai
import argparse
import os
import io
import re

def extract_pdf_text(pdf_path):
    """
    Extract text from a PDF file.
    
    :param pdf_path: Path to the PDF file
    :return: Extracted text as a string
    """
    try:
        text = extract_text(pdf_path)
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

def analyze_pdf_accessibility(pdf_path):
    """
    Analyze the accessibility of a PDF document.
    
    :param pdf_path: Path to the PDF file
    :return: A dictionary containing accessibility issues
    """
    issues = {
        "missing_alt_text": 0,
        "low_contrast_text": 0,
        "improper_reading_order": False,
        "no_document_structure": True
    }
    
    try:
        resource_manager = PDFResourceManager()
        fake_file_handle = io.StringIO()
        laparams = LAParams()
        device = PDFPageAggregator(resource_manager, laparams=laparams)
        interpreter = PDFPageInterpreter(resource_manager, device)
        
        with open(pdf_path, 'rb') as file:
            for page in PDFPage.get_pages(file):
                interpreter.process_page(page)
                layout = device.get_result()
                
                for element in layout:
                    if isinstance(element, LTImage):
                        issues["missing_alt_text"] += 1
                    elif isinstance(element, LTTextBox):
                        # This is a simplification. In a real scenario, you'd need more 
                        # sophisticated analysis for contrast and reading order.
                        if len(element.get_text().strip()) < 5:  # Arbitrary threshold
                            issues["low_contrast_text"] += 1
                
                # If we find any structure, update the flag
                if hasattr(page, 'get_contents'):
                    issues["no_document_structure"] = False
        
        return issues
    except Exception as e:
        print(f"Error analyzing PDF accessibility: {e}")
        return None

def convert_pdf_to_accessible(input_path, output_path):
    """
    Convert a PDF to a more accessible format.
    
    :param input_path: Path to the input PDF file
    :param output_path: Path to save the converted PDF file
    :return: True if conversion was successful, False otherwise
    """
    try:
        doc = fitz.open(input_path)
        for page in doc:
            # Add basic structure: convert text to spans and add to a block
            page.clean_contents()
            page.wrap_contents()
            
            # Improve text contrast (simplified approach)
            for block in page.get_text("dict")["blocks"]:
                if block["type"] == 0:  # text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            span["color"] = (0, 0, 0)  # Set text color to black
            
            # TODO: Add more accessibility improvements here
        
        doc.save(output_path)
        doc.close()
        return True
    except Exception as e:
        print(f"Error converting PDF to accessible format: {e}")
        return False

def prepare_content_for_gpt(pdf_path):
    """
    Prepare PDF content for processing by GPT-4o-mini.
    
    :param pdf_path: Path to the PDF file
    :return: Formatted content as a string
    """
    try:
        doc = fitz.open(pdf_path)
        content = []
        
        # Extract metadata
        metadata = doc.metadata
        title = metadata.get('title', 'Untitled')
        author = metadata.get('author', 'Unknown')
        language = metadata.get('language', 'Unknown')
        
        # Add document overview
        content.append(f"Document Title: {title}")
        content.append(f"Author: {author}")
        content.append(f"Language: {language}")
        content.append("\nDocument Overview:")
        
        # Extract and format content
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block["type"] == 0:  # text block
                    for line in block["lines"]:
                        text = " ".join([span["text"] for span in line["spans"]])
                        # Identify and format headings (simplified approach)
                        if re.match(r'^[A-Z0-9\s]{1,50}$', text) and len(text) > 3:
                            content.append(f"\n## {text}")
                        else:
                            content.append(text)
                elif block["type"] == 1:  # image block
                    content.append("[Image]")
        
        # Construct the prompt
        prompt = "Please analyze the following document for 508 compliance and provide recommendations to ensure it meets accessibility standards. Focus on text alternatives for non-text content, correct tagging, and logical reading order.\n\nDocument content:\n\n"
        formatted_content = "\n".join(content)
        
        return prompt + formatted_content
    except Exception as e:
        print(f"Error preparing content for GPT: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="508 Compliant PDF Conversion Agent")
    parser.add_argument("input", help="Path to the input PDF file")
    parser.add_argument("output", help="Path to save the compliant PDF file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    # Extract text from the input PDF
    extracted_text = extract_pdf_text(args.input)
    if extracted_text:
        print("Text extracted successfully.")
        if args.verbose:
            print(f"Extracted text preview: {extracted_text[:200]}...")
    else:
        print("Failed to extract text from the PDF.")

    # Analyze PDF accessibility
    accessibility_issues = analyze_pdf_accessibility(args.input)
    if accessibility_issues:
        print("\nAccessibility Analysis Results:")
        for issue, count in accessibility_issues.items():
            if args.verbose or (isinstance(count, (int, bool)) and count > 0):
                print(f"{issue.replace('_', ' ').capitalize()}: {count}")
    else:
        print("Failed to analyze PDF accessibility.")

    # Prepare content for GPT-3.5-turbo
    print("\nPreparing content for GPT-3.5-turbo...")
    gpt_content = prepare_content_for_gpt(args.input)
    if gpt_content:
        print("Content prepared successfully.")
        if args.verbose:
            print(f"Prepared content preview: {gpt_content[:200]}...")
        
        # Call OpenAI API
        print("\nCalling OpenAI API...")
        try:
            openai.api_key = os.environ.get("OPENAI_API_KEY")
            if not openai.api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an AI assistant specialized in analyzing documents for 508 compliance."},
                    {"role": "user", "content": gpt_content}
                ]
            )
            api_response = response.choices[0].message.content
            print("GPT-3.5-turbo analysis completed successfully.")
            if args.verbose:
                print(f"API response preview: {api_response[:200]}...")
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
    else:
        print("Failed to prepare content for GPT-3.5-turbo.")

    # Convert PDF to a more accessible format
    print("\nConverting PDF to a more accessible format...")
    if convert_pdf_to_accessible(args.input, args.output):
        print(f"Conversion successful. Accessible PDF saved to: {args.output}")
    else:
        print("Failed to convert PDF to accessible format.")

if __name__ == "__main__":
    main()
