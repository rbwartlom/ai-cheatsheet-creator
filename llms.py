import asyncio
import os

from dotenv import load_dotenv
import re

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import chain
from langchain_openai import ChatOpenAI
from openai import RateLimitError

# Load openai api key
load_dotenv()
if os.getenv("OPENAI_API_KEY") is None:
    raise Exception("The openai api key was not provided!")
format_model = ChatOpenAI(model="gpt-4o-mini")
parse_model = ChatOpenAI(model="gpt-4o")


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
    # TODO: if generalizing this to not only math scripts, change this prompt
    # Concatenate with Page n, Page n + 1
    concatenated_pages = [f"Page {i + 1}: {text}" for i, text in enumerate(page_texts)]

    # Join them together into a single string (if desired)
    final_text = "\n\n".join(concatenated_pages)

    messages = [
        SystemMessage("Please parse these pages from this pdf word-for-word and format it nicely."
                      "Some mathematical formulas may be messed up in the input"),
        HumanMessage(final_text)
    ]

    response = await _invoke_with_retries(format_model, messages)
    return str(response.content)


@chain
async def parse_cheatsheet_formulas_linalg(page_text: str) -> str:
    empty_signal = "NEIN_LEER"
    # TODO: if generalizing this to not only math scripts, change this prompt
    messages = [
        SystemMessage("Du bist Experte in linearer Algebra und hilfst mir heute dabei, ein Cheatsheet zu erstellen."
                      "Du bekommst einige Seiten aus meinem LinAlg-Skript und findest darin wichtige "
                      "Lemmata / Korollare / Definitionen. NUR diese gibst du dann aus. "
                      "Selbstverständliche Sachen können ausgelassen werden, ich habe 2 Seiten für mein Cheatsheet und das Skript ist 100 Seiten lang."
                      f"Falls auf der gegebenen Seite nichts wichtiges steht, gebe {empty_signal} aus"
                      ),
        SystemMessage("""You output markdown with new permanent operational parameters for math equation output: 
Enclose within dollar sign characters ($): LaTeX formatting code for any formulas."""),
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


chain = format_math | parse_cheatsheet_formulas_linalg


async def process_pages(page_text: list[str]):
    return await chain.ainvoke(page_text)


