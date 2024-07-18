import logging
import asyncio
import threading
from io import StringIO
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from tools.llm import *
from tools.notion import *
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# 设置日志
log_stream = StringIO()
logging.basicConfig(level=logging.INFO, stream=log_stream)
logger = logging.getLogger(__name__)
notion_manager = NotionMarkdownManager(os.environ["NOTION_TOKEN"], os.environ["NOTION_DB_ID"])

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 全局变量
stop_event = threading.Event()
current_task = None

base_mermaid_chart = """flowchart TD
A[init] --> B{judge}
B -->|1| C[search]
B -->|2| D[makeMarkdownArtile]
C -->|back| B
D --> E[update_notion_by_id]
"""

current_mermaid_chart = base_mermaid_chart

@app.get("/")
async def read_root(request: Request):
    global current_mermaid_chart
    current_mermaid_chart = base_mermaid_chart
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/start")
async def start_graph(request: Request):
    global current_task, stop_event
    data = await request.json()
    initial_command = data.get("initial_command")
    task_id = data.get("task_id", "default_task_id")

    if current_task:
        stop_event.set()
        await current_task
        stop_event.clear()

    current_task = asyncio.create_task(run_graph_async(initial_command, task_id))
    return JSONResponse({"message": "Graph generation started"})

@app.post("/stop")
async def stop_graph():
    global stop_event
    stop_event.set()
    return JSONResponse({"message": "Graph generation stopped"})

@app.get("/graph")
async def get_graph():
    global current_mermaid_chart
    if stop_event.is_set():
        current_mermaid_chart = base_mermaid_chart
    # 获取最新的日志内容
    log_contents = log_stream.getvalue()
    return JSONResponse({"mermaid_chart": current_mermaid_chart, "logs": log_contents})

async def run_graph_async(initial_command, task_id):
    await asyncio.get_event_loop().run_in_executor(None, run_graph, initial_command, task_id)

def run_graph(initial_command, task_id):
    global current_mermaid_chart
    try:
        current_node = "A"
        visited_nodes = []
        page_id = task_id
        keywords = None
        prevArticle = None
        data = None

        while current_node != "E":
            if stop_event.is_set():
                current_mermaid_chart = base_mermaid_chart
                break

            visited_nodes.append(current_node)
            update_mermaid_chart(visited_nodes)
            logger.info(f"Current node: {current_node}")

            if current_node == "A":
                logger.info(f"Node A: Initial command: {initial_command}")
                if page_id is None:
                    page_id = notion_manager.insert_markdown_to_notion(initial_command.replace('\n', '')[:100])
                prevArticle = notion_manager.read_article_markdown_by_id(page_id)
                logger.info(f"Node A: Previous article: {prevArticle}")
                data = 'data:\n```' + prevArticle + '```\n\ntopic:\n' + initial_command
                current_node = "B"
            elif current_node == "B":
                logger.info(f"Node B: Data for judging: {data}")
                judge_result = judge(data)
                logger.info(f"Node B: Judge result: {judge_result}")
                if judge_result['needSearch'] == 'Y':
                    keywords = judge_result['keywords']
                    logger.info(f"Node B: Keywords for search: {keywords}")
                    current_node = "C"
                else:
                    current_node = "D"
            elif current_node == "C":
                logger.info(f"Node C: Searching with keywords: {' '.join(keywords)}")
                search_result = search(' '.join(keywords))
                logger.info(f"Node C: Search result: {search_result}")
                data = 'data:\n```' + prevArticle + search_result + '```\n\ntopic:\n' + initial_command
                current_node = "B"
            elif current_node == "D":
                logger.info(f"Node D: Data for markdown article: {data}")
                final = makeMarkdownArtile(data)
                logger.info(f"Node D: Final markdown article: {final}")
                notion_manager.update_notion_by_id(page_id, final)
                current_node = "E"

        stop_event.set()
        logger.info(f"Graph generated successfully for task {task_id}")
    except Exception as e:
        logger.error(f"Error generating graph for task {task_id}: {str(e)}")

def update_mermaid_chart(visited_nodes):
    global current_mermaid_chart
    highlighted_chart = base_mermaid_chart
    for node in visited_nodes:
        highlighted_chart = base_mermaid_chart + f"\nstyle {node} stroke:#23b883,stroke-width:8px"
    current_mermaid_chart = highlighted_chart

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
