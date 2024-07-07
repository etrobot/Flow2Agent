import logging
import asyncio
import time
import threading
import random
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
import networkx as nx

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 全局变量
stop_event = threading.Event()
current_task = None
base_mermaid_chart = """flowchart TD
A[初始节点] --> B{Let me think}
B -->|1| C[搜索节点]
B -->|2| D[回答节点]
C -->|返回| B
D --> E[结束节点]
"""


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

    # 如果有正在运行的任务，停止它
    if current_task:
        stop_event.set()
        await current_task
        stop_event.clear()

    # 创建新任务
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


current_mermaid_chart = ""


def run_graph(initial_command, task_id):
    global current_mermaid_chart
    try:
        # 创建网络图
        G = nx.DiGraph()
        G.add_edges_from([
            ("A", "B"),
            ("B", "C"),
            ("B", "D"),
            ("C", "B"),
            ("D", "E")
        ])

        # 初始节点
        current_node = "A"
        visited_nodes = []

        while current_node != "E":
            if stop_event.is_set():
                current_mermaid_chart = base_mermaid_chart
                break

            visited_nodes.append(current_node)

            # 更新当前图表
            highlighted_chart = base_mermaid_chart
            for node in visited_nodes:
                highlighted_chart = base_mermaid_chart + f"\nstyle {node} stroke:#23b883,stroke-width:8px"
            current_mermaid_chart = highlighted_chart

            time.sleep(2)  # 模拟节点执行时长

            # 确定下一个节点
            if current_node == "B":
                current_node = random.choice(["C", "D"])
            else:
                successors = list(G.successors(current_node))
                current_node = successors[0] if successors else "E"

        stop_event.set()
        logger.info(f"Graph generated successfully for task {task_id}")
    except Exception as e:
        logger.error(f"Error generating graph for task {task_id}: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
