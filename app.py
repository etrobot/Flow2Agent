from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from tools.llm import *
from tools.notion import *
from dotenv import load_dotenv, find_dotenv
import os
import logging

load_dotenv(find_dotenv())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
current_node = None
log_messages = []
base_mermaid_chart = """
flowchart TD
A[init] --> B{judge}
B -->|1| C[search]
B -->|2| D[makeMarkdownArtile]
C -->|back| B
D --> E[update_notion_by_id]
{highlighted_node}
"""

def run_background_task(prompt: str, page_id: str = None):
    global log_messages, current_node
    log_messages = []

    def log(message):
        log_messages.append(message)
        logger.info(message)

    try:
        update_chart("A")
        log("Task started")
        notion_manager = NotionMarkdownManager(os.environ["NOTION_TOKEN"], os.environ["NOTION_DB_ID"])
        if page_id is None:
            page_id = notion_manager.insert_markdown_to_notion(prompt.replace('\n', '')[:100])
        log(f"Page ID: {page_id}")
        prevArticle = notion_manager.read_article_markdown_by_id(page_id)
        result = 'data:\n```' + prevArticle + '```\n\ntopic:\n' + prompt

        needSearch = 'Y'
        while needSearch == 'Y':
            update_chart("B")
            judgeResult = judge(result)
            log(f"Judge result: {judgeResult}")
            needSearch = judgeResult['needSearch']
            if needSearch == 'Y':
                update_chart("C")
                searchResult = search(' '.join(judgeResult['keywords']))
                result = 'data:\n```' + searchResult + '```\n\ntopic:\n' + prompt
                log(f"Search results count: {len(result)}")

        update_chart("D")
        final = makeMarkdownArtile(result)
        log(f"Final markdown: {final}")
        update_chart("E")
        notion_manager.update_notion_by_id(page_id, final)
        log("Task completed")
    finally:
        update_chart(None)

def update_chart(node):
    global current_node
    current_node = node

class PromptRequest(BaseModel):
    prompt: str
    page_id: str = None

@app.post("/start")
async def start(prompt_request: PromptRequest, background_tasks: BackgroundTasks):
    if current_node is not None:
        raise HTTPException(status_code=400, detail="A task is already in progress. Please wait until it completes.")
    background_tasks.add_task(run_background_task, prompt_request.prompt, prompt_request.page_id)
    return {"message": "Background task started"}

@app.get("/chart")
async def get_chart():
    if current_node is None:
        highlighted_node = ""
    else:
        highlighted_node = f"style {current_node} stroke:#23b883,stroke-width:8px"
    chart_data = base_mermaid_chart.replace("{highlighted_node}", highlighted_node)
    return JSONResponse(content={"chart": chart_data, "logs": log_messages})

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("static/index.html", "r") as f:
        return f.read()

# Mount the static files directory
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
