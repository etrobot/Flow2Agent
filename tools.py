import os,json
import random
import re
from urllib.parse import quote
from notion_client import Client
from notional.blocks import Page, Paragraph, Heading1, Heading2, Heading3, BulletedListItem

import requests
import markdown
from bs4 import BeautifulSoup
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
notion = Client(auth=os.environ["NOTION_TOKEN"])
# Convert Markdown to Notion blocks
def markdown_to_notion_blocks(md_text):
    blocks=[]
    lines = md_text.split("\n\n")
    for line in lines:
        if line.startswith("# "):
            blocks.append(Heading1(text=line[2:].strip()))
        elif line.startswith("## "):
            blocks.append(Heading2(text=line[3:].strip()))
        elif line.startswith("### "):
            blocks.append(Heading3(text=line[4:].strip()))
        elif line.startswith("- "):
            blocks.append(BulletedListItem(text=line[2:].strip()))
        else:
            blocks.append(Paragraph(text=line.strip()))
    return blocks

# Insert Markdown article into Notion database
def insert_markdown_to_notion(md_text):
    blocks = markdown_to_notion_blocks(md_text)
    title = md_text[:60]
    if len(blocks) > 0:
        title = blocks[0]['heading_1']['rich_text'][0]['text']['content']
    response = notion.pages.create(
        parent={"database_id": os.environ["NOTION_DB_ID"]},
        properties={
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            }
        },
        children=blocks
    )
    return response['id']

# Read article by ID
def update_notion_by_id(page_id, md_text):
    page=notion.pages.retrieve(page_id=page_id)
    blocks = markdown_to_notion_blocks(md_text)
    prop = {'Category': {'id': '%40%7DEa', 'type': 'rich_text', 'rich_text': []},
                                   'Tags': {'id': 'bxEL', 'type': 'multi_select', 'multi_select': []},
                                   'Created': {'id': 'yzKC', 'type': 'created_time',
                                               'created_time': '2024-07-11T15:03:00.000Z'},
                                   'Name': {'id': 'title', 'type': 'title', 'title': [{'type': 'text', 'text': {
                                       'content': page['properties']['Name']['title'][0]['text']['content'], 'link': None},
                                                                                       'annotations': {'bold': False,
                                                                                                       'italic': False,
                                                                                                       'strikethrough': False,
                                                                                                       'underline': False,
                                                                                                       'code': False,
                                                                                                       'color': 'default'},
                                                                                       'plain_text': page['properties']['Name']['title'][0]['text']['content'],
                                                                                       'href': None}]}}
    response = notion.pages.update(
        page_id=page_id,
        properties = prop,
        children=blocks
    )
    return response


def getLLMKey():
    keys = os.getenv("LLM_API_KEY").split(",")
    return random.choice(keys)

def search(prompt:str):
    print('https://s.jina.ai/'+quote(prompt))
    headers = {
        "Authorization": f"Bearer {os.environ['JINA_API_KEY']}"
    }
    markdownResult = requests.get('https://s.jina.ai/'+quote(prompt), headers=headers).text
    print(markdownResult)
    # 使用正则表达式分割文本
    result = re.split('] title:', markdownResult)

    print(result)
    longText=''
    for r in result:
        longText+=llm(r+'summary and list ref with links like [ref title](link)')

    return longText

def makeMarkdownArtile(data:str):
    instruct = '\n\nmake a wiki like articles ,every part should ends with links like [ref title](link)'
    return llm(data+instruct)

def llm(prompt:str):
    llmkey = getLLMKey()
    url = f'{os.getenv("API_BASE_URL")}/v1/chat/completions'
    payload = {
        "model":os.getenv("LLM_MODEL"),
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {llmkey}"
    }

    response = requests.post(url, json=payload, headers=headers)
    resultJson = response.json()

    return resultJson['choices'][0]['message']['content']


def read_article_markdown_by_id(page_id):
    blocks = []
    block_children = notion.blocks.children.list(block_id=page_id)
    blocks.extend(block_children['results'])

    # 用于存储所有块的内容
    content = []

    for block in blocks:
        block_type = block['type']
        if 'rich_text' in block[block_type]:
            for text in block[block_type]['rich_text']:
                content.append(text['text']['content'])

    # 将所有内容结合成一个字符串
    combined_content = ' '.join(content)

    return combined_content
def judge(text):
    judgePrompt =  text+'''
base on the text above, ,do you need to search for references ? output in json format:
{
"analyis":ANALYSIS,
"needSearch":"Y"/"N",
"keywords":EN_KEYWORDS_ARRAY
}    
    '''
    needSearch = llm(judgePrompt)
    match = re.search(r'\{.*\}', needSearch, re.DOTALL)
    result=json.loads(match.group(0))
    return result
def run(prompt:str,noteId:str=None):
    if noteId is None:
        noteId = insert_markdown_to_notion(prompt)
    print(noteId)
    prevArticle = read_article_markdown_by_id(noteId)
    judgeResult = judge(prevArticle+prompt)
    if judgeResult['needSearch'] == 'Y':
        result = search(' '.join(judgeResult['keywords']))
    else:
        result = prevArticle+prompt
    final = makeMarkdownArtile(result)
    update_notion_by_id(noteId, final)

if __name__ == '__main__':
    run("langgraph这个项目是否毫无意义？",'a23f0a1f-369a-4c22-b212-8be7206a9a74')