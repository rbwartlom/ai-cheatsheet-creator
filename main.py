import asyncio

import os
import PyPDF2

from llms import process_pages

script_dir = os.path.dirname(os.path.abspath(__file__))

PDF_SRC = 'solution (1).pdf'
MD_DESTINATION = 'result.md'
BATCH_SIZE = 5


def extract_text_from_pdf(extractor_pdf_path: str):
    if not os.path.exists(extractor_pdf_path):
        print(f"The file {extractor_pdf_path} does not exist.")
        return []

    # Open the PDF file
    with open(extractor_pdf_path, 'rb') as pdf_file:
        # Create a PDF reader object
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        # Initialize an array to hold text from each page
        pages_text = []

        # Loop through each page in the PDF
        for page_num in range(len(pdf_reader.pages)):
            # Extract text from the current page
            page = pdf_reader.pages[page_num]
            page_text = page.extract_text()

            # Append the extracted text to the array
            pages_text.append(page_text)

        return pages_text


async def main(file_path):
    # Extract text from the PDF
    text_from_pages: list[str] = extract_text_from_pdf(extractor_pdf_path=file_path)

    promises = []

    # Process in batches of size `batch_size`
    for i in range(0, len(text_from_pages), BATCH_SIZE):
        batch = text_from_pages[i:i + BATCH_SIZE]
        promises.append(process_pages(batch))

    results = await asyncio.gather(*promises)

    result_path = os.path.join(script_dir, MD_DESTINATION)

    with open(result_path, "w") as file:
        file.write("\n\n".join(results))

    return results


if __name__ == "__main__":
    abs_path = os.path.join(script_dir, PDF_SRC)
    asyncio.run(main(abs_path))
