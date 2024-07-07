import os,json
import random
import re

from notion_client import Client
import requests
import markdown
from bs4 import BeautifulSoup
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
notion = Client(auth=os.environ["NOTION_TOKEN"])
# Convert Markdown to Notion blocks
def markdown_to_notion_blocks(md_text):
    html_text = markdown.markdown(md_text)
    soup = BeautifulSoup(html_text, 'html.parser')
    blocks = []

    for element in soup:
        if element.name == 'h1':
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": element.get_text()}
                    }]
                }
            })
        elif element.name == 'h2':
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": element.get_text()}
                    }]
                }
            })
        elif element.name == 'p':
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": element.get_text()}
                    }]
                }
            })
        # Add more conversion logic to support more Markdown elements if needed

    return blocks



# Insert Markdown article into Notion database
def insert_markdown_to_notion(md_text):
    blocks = markdown_to_notion_blocks(md_text)
    response = notion.pages.create(
        parent={"database_id":  os.environ["NOTION_DB_ID"]},
        properties={
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": blocks[0]['heading_1']['rich_text'][0]['text']['content']
                        }
                    }
                ]
            }
        },
        children=blocks
    )
    return response

# Read article by ID
def update_article_by_id(page_id, md_text):
    blocks = markdown_to_notion_blocks(md_text)
    response = notion.pages.update(
        page_id=page_id,
        properties={
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": blocks[0]['heading_1']['rich_text'][0]['text']['content']
                        }
                    }
                ]
            }
        },
        children=blocks
    )
    return response


def getLLMKey():
    keys = os.getenv("LLM_KEY").split(",")
    return random.choice(keys)

def searchReActAgent(prompt:str):
    markdownResult = requests.get('https://s.jina.ai/'+prompt).text
    # 使用正则表达式分割文本
    pattern = r'\[\d+\]\s*Title:'
    sections = re.split(pattern, markdownResult)

    # 移除第一个空元素(如果存在)
    if sections[0] == '':
        sections = sections[1:]

    # 重新添加标题
    titles = re.findall(pattern, markdownResult)
    result = [f"{titles[i]}{sections[i].strip()}" for i in range(len(sections))]

    longText=''
    for r in result:
        longText+=llm(r+'summary and list ref with links like [ref title](link)')

    return longText

def makeMarkdownArtile(data:str):
    instruct = '\n\nmake a wiki like articles ,every part should ends with links like [ref title](link)'
    return llm(data+instruct)

def llm(prompt:str):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {getLLMKey()}'
    }
    data = {
        "model": os.getenv("LLM_BAK_MODEL"),
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user",
             "content": prompt}
        ],
        "stream": False
    }
    response = requests.post(
        f'{os.getenv("API_BASE_URL")}/chat/completions',
        headers=headers,
        data=json.dumps(data)
    )
    result = response.json()
    content = result['choices'][0]['message']['content'].strip()
    return content

def read_article_markdown_by_id(page_id):
    blocks = []
    block_children = notion.blocks.children.list(block_id=page_id)
    blocks.extend(block_children['results'])

    # Check if there are more pages of children
    while block_children['has_more']:
        block_children = notion.blocks.children.list(block_id=page_id, start_cursor=block_children['next_cursor'])
        blocks.extend(block_children['results'])
    md_text = ""
    for block in blocks:
        if block['type'] == 'heading_1':
            md_text += f"# {block['heading_1']['rich_text'][0]['text']['content']}\n\n"
        elif block['type'] == 'heading_2':
            md_text += f"## {block['heading_2']['rich_text'][0]['text']['content']}\n\n"
        elif block['type'] == 'paragraph':
            md_text += f"{block['paragraph']['rich_text'][0]['text']['content']}\n\n"
        # Add more conversion logic to support more Notion block types if needed

    return md_text
def run(prompt:str,noteId:str=None):
        if noteId is None:
            noteId = insert_markdown_to_notion(prompt)
        result = searchReActAgent(read_article_markdown_by_id(noteId)+prompt)
        final = makeMarkdownArtile(result)
        update_article_by_id(noteId, final)
