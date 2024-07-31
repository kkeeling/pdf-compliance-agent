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
from fpdf import FPDF
import json

def extract_pdf_content(pdf_path):
    """
    Extract text, metadata, and structure from a PDF file.
    
    :param pdf_path: Path to the PDF file
    :return: A dictionary containing extracted content, metadata, and structure
    """
    logger = logging.getLogger('pdf_conversion_agent')
    try:
        doc = fitz.open(pdf_path)
        content = {
            "text": [],
            "metadata": doc.metadata,
            "structure": [],
            "images": [],
            "tables": []
        }
        
        # Extract additional metadata
        content["metadata"]["page_count"] = len(doc)
        content["metadata"]["file_size"] = os.path.getsize(pdf_path)
        content["metadata"]["permissions"] = doc.permissions
        
        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block["type"] == 0:  # text block
                    for line in block["lines"]:
                        text = " ".join([span["text"] for span in line["spans"]])
                        content["text"].append(text)
                        # Identify and format headings, paragraphs, and list items
                        if any(span["size"] > 12 for span in line["spans"]):
                            content["structure"].append(("heading", text))
                        elif text.strip().startswith(('•', '-', '*')) or re.match(r'^\d+\.', text.strip()):
                            content["structure"].append(("list_item", text))
                        else:
                            content["structure"].append(("paragraph", text))
                elif block["type"] == 1:  # image block
                    images = page.get_images()
                    for img_index, img in enumerate(images):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        if base_image:
                            image_bytes = base_image["image"]
                            img_obj = Image.open(io.BytesIO(image_bytes))
                            alt_text = f"Image {img_index + 1} on page {page_num + 1}"
                            image_info = {
                                "page": page_num + 1,
                                "bbox": block["bbox"],
                                "size": img_obj.size,
                                "alt_text": alt_text
                            }
                            content["images"].append(image_info)
                            content["structure"].append(("image", f"[{alt_text}]"))
            
            # Extract tables with content
            tables = page.find_tables()
            if tables:
                for table in tables:
                    table_data = [
                        [cell.text if cell else "" for cell in row]
                        for row in table.cells
                    ]
                    content["tables"].append({
                        "page": page_num + 1,
                        "bbox": table.bbox,
                        "rows": len(table.cells),
                        "cols": len(table.cells[0]) if table.cells else 0,
                        "data": table_data
                    })
                    content["structure"].append(("table", f"[Table on page {page_num + 1}]"))
        
        logger.info(f"Successfully extracted content from PDF: {pdf_path}")
        return content
    except Exception as e:
        logger.exception(f"Error extracting content from PDF: {pdf_path}")
        return None

def prepare_content_for_gpt(content):
    """
    Prepare PDF content for processing by GPT-4o-mini.
    
    :param content: Extracted content from the PDF
    :return: Formatted content as a string
    """
    logger = logging.getLogger('pdf_conversion_agent')
    try:
        formatted_content = []
        
        # Add metadata
        formatted_content.append(f"Document Title: {content['metadata'].get('title', 'Untitled')}")
        formatted_content.append(f"Author: {content['metadata'].get('author', 'Unknown')}")
        formatted_content.append(f"Language: {content['metadata'].get('language', 'Unknown')}")
        formatted_content.append("\nDocument Overview:")
        
        # Add structured content
        for item_type, item_content in content["structure"]:
            if item_type == "heading":
                formatted_content.append(f"\n## {item_content}")
            elif item_type == "paragraph":
                formatted_content.append(item_content)
            elif item_type == "list_item":
                formatted_content.append(f"  • {item_content}")
            elif item_type == "image":
                formatted_content.append("[Image]")
        
        logger.info("Successfully prepared content for GPT-4o-mini")
        return "\n".join(formatted_content)
    except Exception as e:
        logger.exception("Error preparing content for GPT-4o-mini")
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
        logger.info(f"PDF generated at {output_path}")
    except Exception as e:
        logger.exception(f"Error generating PDF: {output_path}")

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
        logger.exception("Error reading system prompt file")
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
        logger.exception("Error reading user prompt file")
        return None

def execute_agent(content):
    """
    Send content to GPT-4o API and receive recommendations.
    
    :param content: Formatted content to send to the API
    :return: API response containing recommendations and content for PDF generation
    """
    logger = logging.getLogger('pdf_conversion_agent')
    try:
        client = OpenAI()
        
        system_prompt = read_system_prompt()
        if system_prompt is None:
            logger.error("Failed to read system prompt.")
            return None
        
        user_prompt = read_user_prompt()
        if user_prompt is None:
            logger.error("Failed to read user prompt.")
            return None
        
        user_prompt = user_prompt.format(content=content)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )
        
        api_response = response.choices[0].message
        logger.info("Successfully received response from GPT-4o-mini API")

        return api_response.content
    except Exception as e:
        logger.exception("Error calling OpenAI API")
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
    parser = argparse.ArgumentParser(description="508 Compliant PDF Conversion Agent")
    parser.add_argument("--input", help="Path to the input PDF file")
    parser.add_argument("--output", help="Path to save the compliant PDF")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    logger = setup_logging(args.verbose)

    try:
        # Extract PDF content
        logger.info("Extracting PDF content...")
        pdf_content = extract_pdf_content(args.input)
        if pdf_content:
            logger.info("Content extracted successfully.")
            
            # Prepare content for GPT-4o-mini
            logger.info("Preparing content for GPT-4o-mini...")
            gpt_content = prepare_content_for_gpt(pdf_content)
            
            # Execute Agent
            logger.info("Executing Agent...")
            api_response = execute_agent(gpt_content)
            if api_response:
                logger.info("GPT-4o-mini analysis completed successfully.")
            
                try:
                    parsed_response = json.loads(api_response)
                    compliant_content = parsed_response.get('compliant_content')
                
                    # Generate compliant PDF
                    if args.output and compliant_content:
                        logger.info(f"Generating compliant PDF: {args.output}")
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
        logger.exception(f"An error occurred during PDF conversion: {str(e)}")

if __name__ == "__main__":
    main()
