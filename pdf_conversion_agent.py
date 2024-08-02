import fitz  # PyMuPDF
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams, LTTextBox, LTImage, LTFigure
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from openai import OpenAI
import argparse
import io
import re
from PIL import Image
import os
import logging
from logging.handlers import RotatingFileHandler
from colorama import Fore, init
from fpdf import FPDF
import json
from halo import Halo
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import mimetypes

init(autoreset=True)  # Initialize colorama with autoreset

def upload_pdf_to_gemini(pdf_path):
    """
    Upload a PDF file to the Gemini API.
    
    :param pdf_path: Path to the PDF file
    :return: A File object containing the uploaded file's metadata
    """
    logger = logging.getLogger('pdf_conversion_agent')
    try:
        mime_type, _ = mimetypes.guess_type(pdf_path)
        if mime_type != 'application/pdf':
            raise ValueError("The file is not a PDF.")
        
        with open(pdf_path, 'rb') as f:
            file_content = f.read()
        
        file = genai.upload_file(file_content, mime_type=mime_type)
        logger.info(f"{Fore.GREEN}Successfully uploaded PDF: {pdf_path}")
        return file
    except Exception as e:
        logger.error(f"{Fore.RED}Error uploading PDF: {pdf_path}. Reason: {str(e)}")
        return None

def extract_pdf_content(pdf_path):
    """
    Extract content from a PDF file by uploading it to the Gemini API.
    
    :param pdf_path: Path to the PDF file
    :return: A File object containing the uploaded file's metadata
    """
    return upload_pdf_to_gemini(pdf_path)


def generate_pdf(content, output_path):
    """
    Generate a 508 compliant PDF file based on the provided content.
    
    :param content: The content to be included in the PDF
    :param output_path: Path to save the generated PDF file
    """
    logger = logging.getLogger('pdf_conversion_agent')
    try:
        # Create a new PDF document
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', '', 12)
        
        # Add the content to the PDF
        pdf.multi_cell(0, 5, content)
        
        # Save the PDF file
        pdf.output(output_path, 'F')
        logger.info(f"{Fore.GREEN}PDF generated at {output_path}")
    except Exception as e:
        logger.error(f"{Fore.RED}Error generating PDF: {output_path}. Reason: {str(e)}")

def read_system_prompt():
    """
    Read the system prompt from the system_prompt.md file.
    
    :return: The content of the system prompt file as a string
    """
    logger = logging.getLogger('pdf_conversion_agent')
    try:
        with open('system_prompt.md', 'r') as file:
            return file.read().strip()
    except Exception as e:
        logger.error(f"{Fore.RED}Error reading system prompt file. Reason: {str(e)}")
        return None

def read_user_prompt():
    """
    Read the user prompt from the user_prompt.md file.
    
    :return: The content of the user prompt file as a string
    """
    logger = logging.getLogger('pdf_conversion_agent')
    try:
        with open('user_prompt.md', 'r') as file:
            return file.read().strip()
    except Exception as e:
        logger.error(f"{Fore.RED}Error reading user prompt file. Reason: {str(e)}")
        return None

def execute_agent(pdf_content):
    """
    Send raw PDF content to Gemini API for processing.
    
    :param pdf_content: Dictionary containing raw binary content and metadata extracted from the PDF file
    :return: API response containing recommendations and content for PDF generation
    """
    logger = logging.getLogger('pdf_conversion_agent')
    try:
        # Get the API key from environment variable
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.error("GOOGLE_API_KEY environment variable is not set.")
            return None

        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Initialize the Gemini model
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        system_prompt = read_system_prompt()
        if system_prompt is None:
            logger.error("Failed to read system prompt.")
            return None
        
        user_prompt = read_user_prompt()
        if user_prompt is None:
            logger.error("Failed to read user prompt.")
            return None
        
        # Convert binary content to base64 for safe transmission
        import base64
        base64_content = base64.b64encode(pdf_content["raw_binary"]).decode('utf-8')
        
        # Include metadata in the user prompt
        metadata_str = json.dumps(pdf_content["metadata"], indent=2)
        user_prompt = user_prompt.format(content=base64_content, metadata=metadata_str)

        safety_settings = [
            {
                "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            },
            {
                "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            },
        ]

        with Halo(text='Executing Agent...', spinner='dots'):
            response = model.generate_content(
                prompt=system_prompt + user_prompt,
                safety_settings=safety_settings,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    top_p=1,
                    top_k=32,
                    max_output_tokens=2048,
                )
            )
            response = model.generate_content(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                generation_config=genai.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=4096
                )
            )
        
        logger.info(f"{Fore.GREEN}Successfully received response from Gemini API")

        return response.text
    except Exception as e:
        logger.error(f"{Fore.RED}Error calling Gemini API. Reason: {str(e)}")
        return None

def setup_logging(verbose):
    logger = logging.getLogger('pdf_conversion_agent')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    # File handler
    file_handler = RotatingFileHandler('pdf_conversion.log', maxBytes=1024*1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

def main():
    parser = argparse.ArgumentParser(description=f"{Fore.YELLOW}508 Compliant PDF Conversion Agent")
    parser.add_argument("--input", help=f"{Fore.YELLOW}Path to the input PDF file")
    parser.add_argument("--output", help=f"{Fore.YELLOW}Path to save the compliant PDF")
    parser.add_argument("--verbose", action="store_true", help=f"{Fore.YELLOW}Enable verbose output")
    args = parser.parse_args()

    logger = setup_logging(args.verbose)

    try:
        # Extract PDF content
        logger.info(f"{Fore.GREEN}Extracting PDF content...")
        pdf_content = extract_pdf_content(args.input)
        if pdf_content:
            logger.info(f"{Fore.GREEN}Content extracted successfully.")
            
            # Execute Agent with PDF content dictionary
            logger.info(f"{Fore.GREEN}Executing Agent...")
            api_response = execute_agent(pdf_content)
            if api_response:
                logger.info(f"{Fore.GREEN}GPT-4o-mini analysis completed successfully.")
            
                try:
                    parsed_response = json.loads(api_response)
                    compliant_content = parsed_response.get('compliant_content')
                
                    # Generate compliant PDF
                    if args.output and compliant_content:
                        logger.info(f"{Fore.GREEN}Generating compliant PDF: {args.output}")
                        generate_pdf(compliant_content, args.output)
                    else:
                        logger.error("Failed to generate PDF: Missing output path or compliant content.")
                except json.JSONDecodeError:
                    logger.error("Failed to parse API response as JSON.")
            else:
                logger.error("Failed to get response from GPT-4o-mini API.")
        else:
            logger.error("Failed to extract content from PDF.")
    except Exception as e:
        logger.error(f"{Fore.RED}An error occurred during PDF conversion: {str(e)}")

if __name__ == "__main__":
    main()
