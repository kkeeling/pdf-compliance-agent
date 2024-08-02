# User Prompt

Please analyze the uploaded PDF document for 508 compliance and provide recommendations to ensure it meets accessibility standards.

Then, generate content for a 508 compliant PDF based on the original document and your recommendations. Include all necessary elements such as headings, paragraphs, lists, image descriptions, and any other relevant content to create a fully accessible document.

Uploaded file: {uploaded_file}

Please provide your analysis and the generated content for the compliant PDF in your response. Format your response as a JSON object with the following structure:

{
  "analysis": "Your detailed analysis of the document's 508 compliance",
  "recommendations": "Your recommendations for improving accessibility",
  "compliant_content": "The generated content for the 508 compliant PDF"
}
