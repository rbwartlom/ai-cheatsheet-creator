import os
from typing import Literal

import streamlit as st
import asyncio
import PyPDF2

from llms import process_blocks

st.set_page_config(page_title="PDF to Markdown Summarizer")


# Helper function to extract the text from the PDF
def extract_text_from_pdf(pdf_file) -> list[str]:
    """
    Takes a file-like object (pdf_file) and extracts text from each page.
    Returns a list where each item is the text of a page.
    """
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    pages_text = []
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        page_text = page.extract_text()
        pages_text.append(page_text)
    return pages_text


async def process_pdf_to_md(
        pdf_pages: list[str],
        page_extraction_prompt: str,
        summarizer_prompt: str,
        batch_size: int,
        openai_api_key: str | None
) -> str:
    """
    Uses the llms.process_blocks() function to process the PDF pages
    in batches, returning a single Markdown string that includes a suitable title.
    """
    # Build an in-memory "prompts_json" from the user-provided prompts
    prompts_json = {
        "page_extraction_prompt": page_extraction_prompt,
        "summarizer_prompt": summarizer_prompt
    }

    pages: tuple[list[str], Literal["text"]] = (pdf_pages, "text")

    title, promises = await process_blocks(
        prompts_json=prompts_json,
        pages=pages,
        batch_size=batch_size,
        openai_api_key=openai_api_key
    )

    # Gather all results (each is a chunk/batch of processed text)
    results = []
    for promise, status_dict in promises:
        result = await promise
        results.append(result)

    joined_md = f"# {title}\n\n" + "\n\n".join(results)

    return joined_md


def md_view(md: str):
    c1, c2 = st.columns([8, 2])

    with c1:
        st.subheader("Final Markdown Output")

    with c2:
        # Provide a download button
        st.download_button(
            label="Download",
            data=md,
            file_name="result.md",
            mime="text/markdown"
        )

    view = st.selectbox("Select view type", ["Preview", "Code"])

    if view == "Preview":
        st.markdown(md)
    else:
        st.code(md, language="markdown")


def main():
    st.title("PDF to Markdown Summarizer")

    # Side prompts input
    with st.sidebar:
        st.markdown("## Setup")
        page_extraction_prompt = st.text_area(
            "Page Extraction Prompt",
            value="Please format these lecture slides nicely. Do not exclude any content and write down everything you see."
        )
        summarizer_prompt = st.text_area(
            "Summarizer Prompt",
            placeholder="Input your summarizer prompt here... (e.g. 'Generate questions and answers for the provided slides', 'Extract only formulas')",
        )
        openai_api_key = st.text_input("OpenAI API Key", )

        st.text(
            "Explanation: The app first uses the extraction prompt to format the pages nicely, also parsing mathematical formulas. It then uses the summarizer prompt to summarize the content.")

    uploaded_file = st.file_uploader("Upload your PDF file", type=["pdf"], on_change=lambda: st.session_state.pop("final_md", None))
    batch_size = st.number_input(
        "Batch size (number of pages to process per block)", min_value=1, value=15
    )

    if uploaded_file is not None:
        if summarizer_prompt is None or summarizer_prompt.strip() == "":
            st.warning("Please provide a summarizer prompt before proceeding.")
            return

        if (openai_api_key is None or openai_api_key == "") and os.getenv("OPENAI_API_KEY") is None:
            st.warning("Please provide an OpenAI API key before proceeding. https://platform.openai.com/settings/organization/api-keys. The API key is not stored.")
            return

        # Show a button to process
        if st.button("Generate Markdown"):
            with st.spinner("Processing..."):
                # Extract text from the uploaded PDF
                pdf_pages = extract_text_from_pdf(uploaded_file)

                # Process the pages in an async loop
                try:
                    final_md = asyncio.run(
                        process_pdf_to_md(
                            pdf_pages=pdf_pages,
                            page_extraction_prompt=page_extraction_prompt,
                            summarizer_prompt=summarizer_prompt,
                            batch_size=batch_size,
                            openai_api_key=openai_api_key
                        )
                    )
                    st.session_state["final_md"] = final_md
                except Exception as e:
                    st.error(f"Error processing your PDF: {e}")
                    return

                st.success("Markdown generation complete!")

        if "final_md" in st.session_state:
            md_view(st.session_state["final_md"])


if __name__ == "__main__":
    main()
