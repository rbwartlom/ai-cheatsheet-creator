import asyncio
import os

from dotenv import load_dotenv
import re

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import chain
from langchain_openai import ChatOpenAI
from openai import RateLimitError
import json

# Load openai api key
load_dotenv()
if os.getenv("OPENAI_API_KEY") is None:
    raise Exception("The openai api key was not provided!")
format_model = ChatOpenAI(model="gpt-4o-mini")
parse_model = ChatOpenAI(model="gpt-4o")


def load_prompts_json():
    prompts_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "./prompts.json")

    if not os.path.exists(prompts_json_path):
        raise Exception("Please add a prompts.json file in the root folder")

    with open(prompts_json_path, "r") as p_json:
        return json.load(p_json)


prompts_json = load_prompts_json()


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

    response = await _invoke_with_retries(format_model, messages)
    return str(response.content)


@chain
async def summarize_cheatsheet(page_text: str) -> str:
    empty_signal = "NEIN_LEER"
    messages = [
        SystemMessage(prompts_json["summarizer_prompt"]),
        SystemMessage(f"Falls auf de gegebenen Seiten nichts wichtiges steht, gebe `{empty_signal}` aus"),
        HumanMessage(page_text)
    ]

    response = await _invoke_with_retries(parse_model, messages)

    content = response.content
    if not isinstance(content, str):
        # This should not happen / is unexpected behavior, so the bug should be addressed if it occurs and not ignored
        raise Exception(f"Illegal response from openai: {content}")

    # Convert inline LaTeX expressions from \( ... \) to $ ... $
    content = re.sub(r'\\\((.*?)\\\)', r'$\1$', content)
    # Convert block LaTeX expressions from \[ ... \] to $$ ... $$
    content = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', content, flags=re.DOTALL)

    if content.startswith("```markdown"):
        content = content.replace("```markdown", "").replace("```", "").strip()

    return "" if empty_signal in content else content


chain = format_math | summarize_cheatsheet


async def process_pages(page_text: list[str]):
    return await chain.ainvoke(page_text)


