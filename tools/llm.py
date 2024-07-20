import os,json
import random
import re
from urllib.parse import quote
import requests

def extractJson(text:str):
    match = re.search(r'\{.*\}', text, re.DOTALL)
    json_str = re.sub(r',\s*}', '}', match.group(0))
    return json.loads(json_str)
def getLLMKey():
    keys = os.getenv("LLM_API_KEY").split(",")
    return random.choice(keys)

def search(prompt:str):
    print('https://s.jina.ai/'+quote(prompt))
    # headers = {
    #     "Authorization": f"Bearer {os.environ['JINA_API_KEY']}"
    # }
    markdownResult = requests.get('https://s.jina.ai/'+quote(prompt)).text
    # 使用正则表达式分割文本
    result = re.split('] title:', markdownResult)

    longText=''
    for r in result:
        longText+=llm(r+'summary to keypoints and list ref with links like [ref title](link)')

    return longText

def llm(prompt:str):
    print(f'llm:{prompt}')
    llmkey = getLLMKey()
    url = f'{os.getenv("API_BASE_URL")}/v1/chat/completions'
    payload = {
        "model":os.getenv("LLM_MODEL"),
        "messages": [
            {
                "role": "user",
                "content": prompt[-min(len(prompt),16000):]
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

def judge(text):
    judgePrompt =  text+'''
read the text above and think,do you need to search for references before answering the last question? output search neccessary analysis in json format:
{
"analyis":ANALYSIS,
"needSearch":"Y"/"N",
"keywords":KEYWORDS_ARRAY
}
must output in English.
    '''
    needSearch = llm(judgePrompt)
    result = extractJson(needSearch)
    return result

def makeMarkdownArtile(data:str):
    instruct = f'\n\n instruct:base on the data above make an English articles for the topic ,every part should ends with links like [ref title](link)'
    return llm(data+instruct)
