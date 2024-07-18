from tools.llm import *
from tools.notion import *
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

def run(prompt:str,page_id:str=None):
    notion_manager = NotionMarkdownManager(os.environ["NOTION_TOKEN"], os.environ["NOTION_DB_ID"])
    if page_id is None:
        page_id = notion_manager.insert_markdown_to_notion(prompt.replace('\n', '')[:100])
    print(page_id)
    prevArticle = notion_manager.read_article_markdown_by_id(page_id)
    judgeResult = judge(prevArticle+prompt)
    print(judgeResult)

    if judgeResult['needSearch'] == 'Y':
        result = search(' '.join(judgeResult['keywords']))
        print(len(result))
    else:
        result = 'data:\n```'+prevArticle+'```\n\ntopic:\n'+prompt
    final = makeMarkdownArtile(result)
    print(final)
    notion_manager.update_notion_by_id(page_id, final)

if __name__ == '__main__':
    run('Crpto will boom if Trump wins the election')