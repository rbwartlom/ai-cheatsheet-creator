import argparse
import asyncio
import json
import os
import sys
from typing import List, Tuple, Any

import PyPDF2
from llms import process_block, get_suitable_title, Status, process_blocks

# Default values
PDF_SRC = 'file.pdf'
MD_DESTINATION = 'file.md'
BATCH_SIZE = 15

script_dir = os.path.dirname(os.path.abspath(__file__))


def load_prompts_json():
    prompts_json_path = os.path.join(script_dir, "prompts.json")

    if not os.path.exists(prompts_json_path):
        raise Exception("Please add a prompts.json file in the root folder")

    with open(prompts_json_path, "r") as p_json:
        return json.load(p_json)


def extract_text_from_pdf(extractor_pdf_path: str):
    if not os.path.exists(extractor_pdf_path):
        print(f"The file {extractor_pdf_path} does not exist.")
        return []

    with open(extractor_pdf_path, 'rb') as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        pages_text: List[str] = []

        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            page_text = page.extract_text()
            pages_text.append(page_text)

        return pages_text


def move_cursor_up(n):
    if n > 0:
        sys.stdout.write(f'\033[{n}A')


def print_status(statuses: List[Tuple[Any, Status]]):
    statuses = [f"Batch {i}: {status_dict['status']}" for i, (_, status_dict) in enumerate(statuses)]
    try:
        terminal_width = os.get_terminal_size().columns
    except OSError:
        print("Processing...")
        return
    padded_statuses = [status.ljust(terminal_width) for status in statuses]
    sys.stdout.write("\n".join(padded_statuses))
    sys.stdout.flush()
    move_cursor_up(len(statuses) - 1)
    sys.stdout.write("\r")


def join_results(title, results):
    return f"# {title}\n\n" + "\n\n".join(results)


async def extract(file_src_path: str, resultfile_name: str, batch_size: int):
    prompts_json = load_prompts_json()
    text_from_pages: List[str] = extract_text_from_pdf(file_src_path)

    print(f"Extracted {len(text_from_pages)} pages from the PDF file.")

    title, promises = await process_blocks(prompts_json=prompts_json, pages=text_from_pages, batch_size=batch_size)

    results = []
    for promise, status_dict in promises:
        while not promise.done():
            print_status(promises)
            await asyncio.sleep(1)
        result = await promise
        results.append(result)

    print_status(promises)

    if not resultfile_name.endswith(".md") and not resultfile_name.endswith(".txt"):
        resultfile_name += ".md"
    result_path = os.path.join(script_dir, resultfile_name)

    with open(result_path, "w") as file:
        file.write(join_results(title, results))
        print(f"Success: Results written to {result_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Extract text from a PDF and process it into a Markdown file.")
    parser.add_argument("--pdf", default=PDF_SRC, help="Path to the source PDF file (default: file.pdf).")
    parser.add_argument("--output", default=MD_DESTINATION, help="Path to the destination Markdown file (default: file.md).")
    parser.add_argument("--batch_size", type=int, default=BATCH_SIZE, help="Batch size for processing blocks (default: 15).")

    args = parser.parse_args()

    src_path = str(os.path.join(script_dir, args.pdf))
    if not os.path.exists(src_path):
        raise Exception(f"The PDF file at `{src_path}` does not exist.")

    result_folder = os.path.join(script_dir, "results")

    if not os.path.exists(result_folder):
        os.mkdir(result_folder)

    destination_path = os.path.join(result_folder, args.output)

    if os.path.exists(destination_path):
        raise Exception("File already exists, please delete it before overwriting.")

    asyncio.run(extract(src_path, destination_path, args.batch_size))


if __name__ == "__main__":
    main()
