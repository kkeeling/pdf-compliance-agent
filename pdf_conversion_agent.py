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
from routellm.routellm import RouteLLM

init(autoreset=True)  # Initialize colorama with autoreset

def extract_pdf_content(pdf_path):
    """
    Extract raw binary content and metadata from a PDF file.
    
    :param pdf_path: Path to the PDF file
    :return: A dictionary containing extracted raw binary content and metadata
    """
    logger = logging.getLogger('pdf_conversion_agent')
    try:
        with open(pdf_path, 'rb') as file:
            binary_content = file.read()
        
        doc = fitz.open(pdf_path)
        content = {
            "raw_binary": binary_content,
            "metadata": doc.metadata,
        }
        
        # Extract additional metadata
        content["metadata"]["page_count"] = len(doc)
        content["metadata"]["file_size"] = os.path.getsize(pdf_path)
        content["metadata"]["permissions"] = doc.permissions
        
        logger.info(f"{Fore.GREEN}Successfully extracted raw binary content from PDF: {pdf_path}")
        return content
    except Exception as e:
        logger.error(f"{Fore.RED}Error extracting content from PDF: {pdf_path}. Reason: {str(e)}")
        return None


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
    Send raw PDF content to RouteLLM for processing.
    
    :param pdf_content: Dictionary containing raw binary content and metadata extracted from the PDF file
    :return: API response containing recommendations and content for PDF generation
    """
    logger = logging.getLogger('pdf_conversion_agent')
    try:
        # Initialize RouteLLM
        routellm = RouteLLM(
            router="mf",
            strong_model="gemini-pro",
            weak_model="gpt-4o-mini",
        )
        
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

        with Halo(text='Executing Agent...', spinner='dots'):
            response = routellm.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=4096,
            )
        
        logger.info(f"{Fore.GREEN}Successfully received response from RouteLLM")

        return response
    except Exception as e:
        logger.error(f"{Fore.RED}Error calling RouteLLM. Reason: {str(e)}")
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
