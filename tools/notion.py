from notion_client import Client
import re
class NotionMarkdownManager:
    def __init__(self, api_key, database_id):
        self.notion = Client(auth=api_key)
        self.database_id = database_id

    def markdown_to_notion_blocks(self, md_text):
        def create_heading_1(text):
            return {
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

        def create_heading_2(text):
            return {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

        def create_heading_3(text):
            return {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

        def create_bulleted_list_item(text):
            return {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

        def create_numbered_list_item(text):
            return {
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

        def create_quote(text):
            return {
                "object": "block",
                "type": "quote",
                "quote": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

        def create_paragraph(text):
            return {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }

        def create_link(text, href):
            return {
                "type": "text",
                "text": {
                    "content": text,
                    "link": {"url": href}
                }
            }

        def parse_paragraph(text):
            # 使用正则表达式查找所有的 [text](url) 形式的字符串
            pattern = re.compile(r'\[([^\]]+)\]\((http[^\)]+)\)')

            rich_text = []
            last_end = 0

            for match in pattern.finditer(text):
                start, end = match.span()
                if start > last_end:
                    # 处理普通文本部分
                    rich_text.append({"type": "text", "text": {"content": text[last_end:start]}})
                # 处理超链接部分
                link_text, link_url = match.groups()
                rich_text.append(create_link(link_text, link_url))
                last_end = end

            if last_end < len(text):
                # 处理剩余的普通文本部分
                rich_text.append({"type": "text", "text": {"content": text[last_end:]}})

            return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text}}

        blocks = []
        lines = md_text.split("\n")

        for line in lines:
            if len(line) == 0:
                continue
            if line.startswith("# "):
                blocks.append(create_heading_1(line[2:]))
            elif line.startswith("## "):
                blocks.append(create_heading_2(line[3:]))
            elif line.startswith("### "):
                blocks.append(create_heading_3(line[4:]))
            elif line.startswith("- "):
                blocks.append(create_bulleted_list_item(line[2:]))
            elif line.startswith("1. "):
                blocks.append(create_numbered_list_item(line[3:]))
            elif line.startswith("> "):
                blocks.append(create_quote(line[2:]))
            else:
                blocks.append(parse_paragraph(line))
        return blocks

    def insert_markdown_to_notion(self, md_text):
        blocks = []
        title = md_text[:60]
        if len(md_text) > 100:
            blocks = self.markdown_to_notion_blocks(md_text)
        if len(blocks) > 0:
            title = blocks[0]['heading_1']['rich_text'][0]['text']['content']
        response = self.notion.pages.create(
            parent={"database_id": self.database_id},
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

    def update_notion_by_id(self, page_id, md_text):
        page = self.notion.pages.retrieve(page_id=page_id)
        blocks = self.markdown_to_notion_blocks(md_text)
        print(blocks)
        response = self.notion.pages.update(
            page_id=page_id,
            properties={
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": page['properties']['Name']['title'][0]['text']['content']
                            }
                        }
                    ]
                }
            }
        )
        self.notion.blocks.children.append(block_id=page_id, children=blocks)
        return response

    def read_article_markdown_by_id(self, page_id):
        blocks = []
        block_children = self.notion.blocks.children.list(block_id=page_id)
        blocks.extend(block_children['results'])

        content = []

        for block in blocks:
            block_type = block['type']
            if 'rich_text' in block[block_type]:
                for text in block[block_type]['rich_text']:
                    content.append(text['text']['content'])

        combined_content = ' '.join(content)

        return combined_content


