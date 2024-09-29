
### Creating a venv and running the project:
cd into the root directory, then
```bash
touch .env
```
^ fill in environment variables here
```bash
python3 -m venv .venv
```
```bash
source .venv/bin/activate
```
```bash
pip install -r requirements.txt
```
```bash
python3 ./main.py
```

### Environment Variables
- `OPENAI_API_KEY`: The API key from your openai account. ([link](https://platform.openai.com/api-keys))

