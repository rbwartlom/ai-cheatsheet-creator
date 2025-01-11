# Cheatsheet creator project
This is a fairly simple cheatsheet creator which can parse the most important information from a (long) lecture handout using an LLM. The generated markdown has LaTeX formulas embedded in `$`s (compatible with the vscode viewer)

The processing is done asynchronously using batches of pages (the batch size can be configured through `main.py`). This slightly favors execution speed over quality, since the llm is not passed context what was on the previous batch of pages.   


## Setup
cd into the root directory, then
```bash
touch prompts.json .env # create config files
```
```bash
python3 -m venv .venv # set up venv
```
```bash
source .venv/bin/activate # set venv as source
```
```bash
pip install -r requirements.txt # install requirements
```
Before running the script, please configure the required files:

### Environment Variables (`.env`)
- `OPENAI_API_KEY`: The API key from your openai account. ([link](https://platform.openai.com/api-keys))

### Prompt setup (`prompts.json`)
Fill out the  created `prompts.json` file as desired. 

See `prompts.example.json` for an example for parsing a german linear algebra lecture handout.
To write good prompts, note the context in which they are used:
- `page_extraction_prompt`: This prompt is used to format the pdf's text layer into a pretty text using a smaller model
- `summarizer_prompt`: This prompt then summarizes the content of the formatted page

### Input & Output files
By default, the input file is `file.pdf`, and the result is outputted into `results/file.md`.
If you wish to change this, you can adjust the top 2 lines from main.py

### Running the program
```bash
python3 ./cli.py
```