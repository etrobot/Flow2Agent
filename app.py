import logging
import asyncio
import time
import threading
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates


# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    return JSONResponse({"mermaid_chart": current_mermaid_chart})

async def run_graph_async(initial_command, task_id):
    await asyncio.get_event_loop().run_in_executor(None, run_graph, initial_command, task_id)

def run_graph(initial_command, task_id):
    global current_mermaid_chart
    try:
        current_node = "A"
        visited_nodes = []
        note_id = None

        while current_node != "E":
            if stop_event.is_set():
                current_mermaid_chart = base_mermaid_chart
                break

            visited_nodes.append(current_node)
            update_mermaid_chart(visited_nodes)

            time.sleep(2)  # 模拟节点执行时长

            if current_node == "A":
                current_node = "B"
            elif current_node == "B":
                current_node = "C"
            elif current_node == "C":
                current_node = "B"
            elif current_node == "D":
                current_node = "E"
            else:
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