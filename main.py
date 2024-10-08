import asyncio
import os
from typing import List

import PyPDF2
from llms import process_pages

# adjust this if needed
PDF_SRC = 'file.pdf'
MD_DESTINATION = 'file.md'

script_dir = os.path.dirname(os.path.abspath(__file__))
BATCH_SIZE = 10


def extract_text_from_pdf(extractor_pdf_path: str):
    if not os.path.exists(extractor_pdf_path):
        print(f"The file {extractor_pdf_path} does not exist.")
        return []

    # Open the PDF file
    with open(extractor_pdf_path, 'rb') as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        pages_text: List[str] = []

        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            page_text = page.extract_text()
            pages_text.append(page_text)

        return pages_text


async def extract(file_src_path: str, resultfile_name: str):
    text_from_pages: list[str] = extract_text_from_pdf(extractor_pdf_path=file_src_path)

    promises = []

    # Process in batches of size `batch_size`
    for i in range(0, len(text_from_pages), BATCH_SIZE):
        batch = text_from_pages[i:i + BATCH_SIZE]
        promises.append(process_pages(batch))

    results = await asyncio.gather(*promises)

    # output result
    if not resultfile_name.endswith(".md"):
        resultfile_name = resultfile_name + ".md"
    result_path = os.path.join(script_dir, resultfile_name)

    with open(result_path, "w") as file:
        file.write("\n\n".join(results))

    return results


if __name__ == "__main__":
    src_path = os.path.join(script_dir, PDF_SRC)
    result_folder = os.path.join(script_dir, "./results/")
    if not os.path.exists(result_folder):
        os.mkdir(result_folder)
    destination_path = os.path.join(result_folder, f"{MD_DESTINATION}")
    if os.path.exists(destination_path):
        raise Exception("File already exists, please delete before overwriting")
    asyncio.run(extract(src_path, destination_path))
