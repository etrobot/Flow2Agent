# Flowchart2Agent
This is an example of creating an AI agent with flowchart
## Installation
1. make a .env file from .env.example with your credentials:
```
LLM API KEY="YOUR LLM API KEY"
LLM MODEL="llama3-70b-8192"
API BASE URL="https://api.groq.com/openai/v1"
NOTION TOKEN="NOTION INTEGRATION TOKEN"
NOTION DB ID="YOUR NOTION DATABASE ID"
```
2. install poetry from https://python-poetry.org/
3. run poetry install to install the dependencies
## Usage
poetry run python app.py