import asyncio
import os

from dotenv import load_dotenv
import re
from typing import TypedDict

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import chain
from langchain_openai import ChatOpenAI
from openai import RateLimitError


class Status(TypedDict):
    status: str


class Prompts(TypedDict):
    page_extraction_prompt: str
    summarizer_prompt: str


# Load openai api key, if set
load_dotenv()
CHEAP_MODEL = "gpt-4o-mini"
SMART_MODEL = "gpt-4o"


async def get_suitable_title(from_prompt: str, openai_api_key: str) -> str:
    messages = [
        SystemMessage(
            "The user will provide a prompt, in which they are looking to create some sort of document. Please output a suitable title for this document. You reply with only the title"),
        HumanMessage(from_prompt)
    ]

    model = ChatOpenAI(model=SMART_MODEL, api_key=openai_api_key)

    response = await model.ainvoke(messages)
    return response.content


async def process_block(page_text: list[str], status: Status, prompts_json: Prompts, openai_api_key: str) -> str:
    status["status"] = "1. invoking"

    smart_model = ChatOpenAI(model=SMART_MODEL, api_key=openai_api_key)
    cheap_model = ChatOpenAI(model=CHEAP_MODEL, api_key=openai_api_key)

    async def _invoke_with_retries(model, messages, max_retries=5, delay=90):
        retries = 0
        while retries < max_retries:
            try:
                response = await model.ainvoke(messages)
                return response
            except RateLimitError:
                retries += 1
                if retries < max_retries:
                    print(f"RateLimitError: Retrying in {delay / 60} minutes... ({retries}/{max_retries})")
                    status[
                        "status"] = f"{status.get('status', '')} RateLimitError: Retrying in {delay / 60} minutes... ({retries}/{max_retries})"
                    await asyncio.sleep(delay)
                else:
                    raise Exception("Max retries reached. Please try again later.")

    @chain
    async def format_math(page_texts: list[str]) -> str:
        # Concatenate with Page n, Page n + 1
        concatenated_pages = [f"Page {f'n + {i}' if i > 0 else 'n'}: {text}" for i, text in enumerate(page_texts)]
        final_text = "\n\n".join(concatenated_pages)

        messages = [
            SystemMessage(prompts_json["page_extraction_prompt"]),
            HumanMessage(final_text)
        ]

        status["status"] = "2. reading pages"

        response = await _invoke_with_retries(cheap_model, messages)
        return str(response.content)

    @chain
    async def summarize_cheatsheet(page_text: str) -> str:
        empty_signal = "NEIN_LEER"
        additional_prompt = f"""
Additional instructions: 
- If the provided pages are not relevant (e.g. contain only metadata), return `{empty_signal}`.
- You output markdown
    - The markdown should not contain h1 headers since it going to be part of a larger document.
    - In your markdown, if you output LaTeX, then follow these new permanent operational parameters for math equation output: Enclose within dollar sign characters ($) for inline math and double dollar sign characters ($$) for block math.
"""
        messages = [
            SystemMessage(prompts_json["summarizer_prompt"]),
            SystemMessage(additional_prompt),
            HumanMessage(page_text)
        ]

        status["status"] = "3. generating"

        response = await _invoke_with_retries(smart_model, messages)

        content = response.content
        if not isinstance(content, str):
            # This should not happen / is unexpected behavior, so the bug should be addressed if it occurs and not ignored
            raise Exception(f"Illegal response from openai: {content}")

        # Convert inline LaTeX expressions from \( ... \) to $ ... $
        content = re.sub(r'\\\((.*?)\\\)', r'$\1$', content)
        # Convert block LaTeX expressions from \[ ... \] to $$ ... $$
        content = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', content, flags=re.DOTALL)

        if content.startswith("```markdown"):
            content = content.replace("```markdown", "").strip()
            if content.endswith("```"):
                content = content[:-3].strip()

        return "" if empty_signal in content else content

    main_chain = format_math | summarize_cheatsheet

    result = await main_chain.ainvoke(page_text)

    status["status"] = "4. done"
    return result


async def process_blocks(prompts_json: Prompts, pages: list[str], batch_size: int, openai_api_key: str | None = None) \
        -> tuple[str, list[tuple[asyncio.Task, Status]]]:
    """
    Processes pages in batches and returns the title and promises for the processed blocks.
    :param prompts_json: A dictionary containing the prompts for the page extraction and summarizer models
    :param pages: A list of strings, each string representing the text of a page
    :param batch_size: The size of the batches to process the pages in (batch_size pages are processed at one time)
    :param openai_api_key: The OpenAI API key to use for invoking the models. If not provided, the env must be set.
    :return: A tuple containing the title and a list of promise, status tuples (one for each block)
    """

    if openai_api_key is None or openai_api_key == "":
        openai_api_key = os.getenv("OPENAI_API_KEY")

    batch_size = max(1, batch_size)
    promises = []
    title_promise = asyncio.create_task(get_suitable_title(prompts_json["summarizer_prompt"], openai_api_key))

    # Process in batches of size `batch_size`
    for i in range(0, len(pages), batch_size):
        batch = pages[i:i + batch_size]
        status_dict = {"status": "invoking"}
        promises.append((asyncio.create_task(process_block(batch, status_dict, prompts_json, openai_api_key)), status_dict))

    title = await title_promise

    return title, promises

