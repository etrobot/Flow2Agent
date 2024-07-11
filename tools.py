import os,json
import random
import re
from urllib.parse import quote

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
    h1=h2=content=md_text
    print(h1,h2,content)
    for element in soup:
        if element.name == 'h1':
            h1=element.get_text()
        elif element.name == 'h2':
            h2=element.get_text()
        elif element.name == 'p':
            content = element.get_text()
    blocks=[
        {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": h1}
                }]
            }
        },{
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": h2}
                    }]
                }
            },{
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": content}
                    }]
                }
            }
    ]
    return blocks

# Insert Markdown article into Notion database
def insert_markdown_to_notion(md_text):
    blocks = markdown_to_notion_blocks(md_text)
    response = notion.pages.create(
        parent={"database_id": os.environ["NOTION_DB_ID"]},
        properties={
            "Name": {
                "title": [
                    {
                        "text": {
                            "content":  blocks[0]['heading_1']['rich_text'][0]['text']['content']
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
    print(prompt)
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
    result=json.loads(needSearch)
    print(result)
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