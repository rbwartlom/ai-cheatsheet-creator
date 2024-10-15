import asyncio
import os

from dotenv import load_dotenv
import re
from typing import TypedDict

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import chain
from langchain_openai import ChatOpenAI
from openai import RateLimitError
import json

class Status(TypedDict):
    status: str

# Load openai api key
load_dotenv()
if os.getenv("OPENAI_API_KEY") is None:
    raise Exception("The openai api key was not provided!")
smart_model = ChatOpenAI(model="gpt-4o-mini")
cheap_model = ChatOpenAI(model="gpt-4o")


def load_prompts_json():
    prompts_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "./prompts.json")

    if not os.path.exists(prompts_json_path):
        raise Exception("Please add a prompts.json file in the root folder")

    with open(prompts_json_path, "r") as p_json:
        return json.load(p_json)


prompts_json = load_prompts_json()

async def get_suitable_title() -> str:
    messages = [
        SystemMessage("The user will provide a prompt, in which they are looking to create some sort of document. Please output a suitable title for this document. You reply with only the title"),
        HumanMessage(prompts_json["summarizer_prompt"])
    ]

    response = await smart_model.ainvoke(messages)
    return response.content



async def process_pages(page_text: list[str], status: Status):
    status["status"] = "invoking"
    
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
                    status["status"] = f"{status.get('status', '')} RateLimitError: Retrying in {delay / 60} minutes... ({retries}/{max_retries})"
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
        
        status["status"] = "formatting math"

        response = await _invoke_with_retries(smart_model, messages)
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
        
        status["status"] = "summarizing"

        response = await _invoke_with_retries(cheap_model, messages)

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


    main_chain = format_math | summarize_cheatsheet
    
    result = await main_chain.ainvoke(page_text)
    
    status["status"] = "done"
    return result


