import asyncio
import os
from typing import List

import PyPDF2
from llms import process_pages
import sys

# adjust this if needed
PDF_SRC = 'file.pdf'
MD_DESTINATION = 'file.md'

script_dir = os.path.dirname(os.path.abspath(__file__))
BATCH_SIZE = 5


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
    
def move_cursor_up(n):
    sys.stdout.write(f'\033[{n}A')


async def extract(file_src_path: str, resultfile_name: str):
    text_from_pages: list[str] = extract_text_from_pdf(extractor_pdf_path=file_src_path)
    
    print(f"Extracted {len(text_from_pages)} pages from the PDF file.")

    promises = []

    # Process in batches of size `batch_size`
    for i in range(0, len(text_from_pages), BATCH_SIZE):
        batch = text_from_pages[i:i + BATCH_SIZE]
        status_dict = {"status": "invoking"}
        promises.append((asyncio.create_task(process_pages(batch, status_dict)), status_dict))

    results = []
    for promise, status_dict in promises:
        statuses = [f"Batch {i}: {status_dict['status']}" for i, (_, status_dict) in enumerate(promises)]
        terminal_width = os.get_terminal_size().columns
        padded_statuses = [status.ljust(terminal_width) for status in statuses]
        sys.stdout.write("\n".join(padded_statuses))
        sys.stdout.flush()
        move_cursor_up(len(promises) - 1) # move cursor up to overwrite the statuses in the next iteration
        sys.stdout.write("\r")
        while not promise.done():
            await asyncio.sleep(1)
        result = await promise
        results.append(result)

    # output result
    if not resultfile_name.endswith(".md"):
        resultfile_name = resultfile_name + ".md"
    result_path = os.path.join(script_dir, resultfile_name)

    with open(result_path, "w") as file:
        file.write("\n\n".join(results))
        print(f"Success: Results written to {result_path}")

    return results


if __name__ == "__main__":
    src_path = os.path.join(script_dir, PDF_SRC)
    result_folder = os.path.join(script_dir, "results/")
    if not os.path.exists(result_folder):
        os.mkdir(result_folder)
    destination_path = os.path.join(result_folder, f"{MD_DESTINATION}")
    if os.path.exists(destination_path):
        raise Exception("File already exists, please delete before overwriting")
    asyncio.run(extract(src_path, destination_path))
