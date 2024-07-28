import fitz  # PyMuPDF
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams, LTTextBox, LTImage
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from openai import OpenAI
import json
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


def call_gpt4o_mini_api(content):
    """
    Send content to GPT-4o-mini API and receive recommendations.
    
    :param content: Formatted content to send to the API
    :return: API response containing recommendations
    """
    try:
        client = OpenAI()
        
        system_prompt = "You are an AI model designed to analyze documents for compliance with accessibility standards. Your task is to review the following document and provide recommendations for 508 compliance."
        user_prompt = f"Please analyze the following document for 508 compliance and provide recommendations to ensure it meets accessibility standards. Document content:\n\n{content}"
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Using GPT-3.5-turbo as a stand-in for GPT-4o-mini
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        api_response = response.choices[0].message.content
        return api_response
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="508 Compliant PDF Analysis Agent")
    parser.add_argument("input", help="Path to the input PDF file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    # Prepare content for GPT-4o-mini
    print("\nPreparing content for GPT-4o-mini...")
    gpt_content = prepare_content_for_gpt(args.input)
    if gpt_content:
        print("Content prepared successfully.")
        if args.verbose:
            print(f"Prepared content preview: {gpt_content[:200]}...")
        
        # Call GPT-4o-mini API
        print("\nCalling GPT-4o-mini API...")
        api_response = call_gpt4o_mini_api(gpt_content)
        if api_response:
            print("GPT-4o-mini analysis completed successfully.")
            if args.verbose:
                print(f"API response preview: {api_response[:200]}...")
            
            print("\nGPT-4o-mini Analysis Results:")
            print(api_response)
        else:
            print("Failed to get response from GPT-4o-mini API.")
    else:
        print("Failed to prepare content for GPT-4o-mini.")

if __name__ == "__main__":
    main()
