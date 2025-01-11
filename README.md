# Cheatsheet creator project
This is a fairly simple cheatsheet creator which can parse the most important information from a (long) lecture handout using an LLM. The generated markdown has LaTeX formulas embedded in `$`s (compatible with the vscode markdown viewer)

View the app at https://ai-cheatsheets.streamlit.app/

The processing is done asynchronously using batches of pages (the batch size can be configured through `main.py`). This slightly favors execution speed over quality, since the llm is not passed context what was on the previous batch of pages.   


## Setup
Ensure you have python 3.12 installed.

cd into the root directory, then
```bash
touch prompts.json .env # create config files. This is only relevant if you want to use the cli.
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
- `OPENAI_API_KEY`: The API key from your openai account. ([link](https://platform.openai.com/api-keys)). 
For the streamlit frontend, this is not mandatory to set.

### Prompt setup (`prompts.json`)
Fill out the  created `prompts.json` file as desired. 

See `prompts.example.json` for an example for parsing a german linear algebra lecture handout.
To write good prompts, note the context in which they are used:
- `page_extraction_prompt`: This prompt is used to format the pdf's text layer into a pretty text using a smaller model
- `summarizer_prompt`: This prompt then summarizes the content of the formatted page


### Running the program
You can choose between two interfaces:
1. Use the CLI (provides nicer status updates, persists your prompts)
```bash
python3 ./cli.py --help
```

2. Use the streamlit frontend (is more user-friendly)
```bash
streamlit run ./streamlit_app.py
```
