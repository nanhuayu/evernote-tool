import mimetypes
import os
import sys
import time
import argparse
import logging
import base64
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup, NavigableString

# 配置日志，输出到控制台和文件
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("parser.log", mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def parse_enex(file_path, output_dir):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        logging.info(f"解析ENEX文件: {file_path}")
    except ET.ParseError as e:
        logging.error(f"解析ENEX文件失败: {e}")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    assets_dir = os.path.join(output_dir, 'assets')
    os.makedirs(assets_dir, exist_ok=True)
    logging.info(f"输出目录: {output_dir}")
    logging.info(f"附件目录: {assets_dir}")

    for note in root.findall('note'):
        parse_note_data(note, output_dir, assets_dir)

def parse_note_data(note, output_dir, assets_dir):
    try:
        note_data = extract_note_data(note)
        debug_flag = any(i in note_data['title'] for i in ['Vue笔记', 'Vuex笔记', 'GMM高斯混合', 'Transformer笔记', 'EM'])
        print(f"检查条件: {debug_flag}")
        markdown_content = process_attachments(note, note_data, assets_dir)
        markdown_content = convert_enml_to_markdown(markdown_content)
        save_markdown_file(note_data['title'], note_data, markdown_content, output_dir)
        logging.info(f"已处理笔记: {note_data['title']}")
    except Exception as e:
        logging.error(f"处理笔记失败: {e}")

def extract_note_data(note):
    title = note.find('title')
    content = note.find('content')
    created = note.find('created')
    updated = note.find('updated')
    source_url = note.find('note-attributes/source-url')
    return {
        'title': title.text if title is not None else '无标题',
        'content': content.text if content is not None else '',
        'created': created.text if created is not None else '',
        'updated': updated.text if updated is not None else '',
        'source_url': source_url.text if source_url is not None else None
    }

def process_attachments(note, note_data, assets_dir):
    soup = BeautifulSoup(note_data['content'], 'html.parser')
    en_note = soup.find('en-note')

    # 处理资源（附件）
    resources = note.findall('resource')
    for resource in resources:
        data = resource.find('data').text
        mime = resource.find('mime').text
        resource_attr = resource.find('resource-attributes')
        file_name = None
        # if resource_attr:
        #     file_name_tag = resource_attr.find('file-name')
        #     if file_name_tag is not None:
        #         file_name = file_name_tag.text.split('#')[0]

        hex_hash = resource.find('data').get('hash')
        if not hex_hash:
            md5_hash = calculate_md5_hash(data)
        else:
            md5_hash = hex_hash
        if not file_name:
            file_name = md5_hash

        # 保存附件
        attachment_path = save_attachment(data, mime, note_data['title'], assets_dir, file_name)
        if attachment_path:
            # 在内容中替换对应的 <en-media> 标签为 Markdown 图片链接

            en_media = en_note.find('en-media', {'hash': md5_hash})
            if en_media:
                img_tag = f"![{file_name}]({os.path.join('assets', os.path.basename(attachment_path))})"
                en_media.replace_with(img_tag.replace('\\', '/'))
                logging.debug(f"替换内容中的附件链接: {img_tag}")
        else:
            logging.warning("附件保存失败，跳过替换内容中的附件链接。")

    return str(en_note)

def save_attachment(data, mime, title, assets_dir, file_name=None):
    try:
        # extension = mime.split('/')[-1]
        extension = mimetypes.guess_extension(mime)
        # if not file_name:
        #     file_name = f"{title}_{int(time.time())}{extension}"
        if not '.' in file_name:
            file_name = f"{file_name}{extension}"
        file_name = sanitize_filename(file_name)
        attachment_data = base64.b64decode(data)
        attachment_path = os.path.join(assets_dir, file_name)

        # # 如果文件已存在，添加序号
        # file_index = 1
        # while os.path.exists(attachment_path):
        #     file_name = f"{os.path.splitext(file_name)[0]}_{file_index}{os.path.splitext(file_name)[1]}"
        #     attachment_path = os.path.join(assets_dir, file_name)
        #     file_index += 1

        with open(attachment_path, 'wb') as attachment_file:
            attachment_file.write(attachment_data)
        logging.debug(f"保存附件: {attachment_path}")
        return attachment_path
    except Exception as e:
        logging.error(f"保存附件失败: {e}")
        return None

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

# def convert_enml_to_markdown(enml_content):
#     markdown = enml_content
#     # 这里可以根据需要添加更多的转换规则
#     replacements = {
#         r'<en-note>': '',
#         r'</en-note>': '',
#         r'<br/>': '\n',
#         r'<br />': '\n',
#         r'<div>': '\n\n',
#         r'</div>': '',
#         r'<span.*?>': '',
#         r'</span>': '',
#         r'&nbsp;': ' '
#     }
#     for pattern, repl in replacements.items():
#         markdown = re.sub(pattern, repl, markdown, flags=re.IGNORECASE)
#     # 移除所有HTML标签
#     markdown = re.sub(r'<[^>]+>', '', markdown)
#     logging.debug("转换ENML到Markdown")
#     return markdown.strip()

def convert_enml_to_markdown(enml_content):
    soup = BeautifulSoup(enml_content, 'html.parser')
    markdown = process_enml_elements(soup)
    logging.debug("转换 ENML 到 Markdown")
    return markdown.strip()

def process_enml_elements(soup):
    # 遍历所有子节点，根据节点类型进行处理
    markdown_lines = []
    for element in soup.contents:
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                markdown_lines.append(text)
        elif element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            content = process_enml_elements(element)
            # 添加 Markdown 标题符号
            level = int(element.name[1])
            markdown_lines.append(f"\n{'#' * level} {content}\n\n")
        elif element.name == 'div' or element.name == 'p':
            content = process_enml_elements(element)
            markdown_lines.append(content + '\n')
        elif element.name == 'br':
            markdown_lines.append('\n')
        elif element.name == 'span':
            content = process_enml_elements(element)
            markdown_lines.append(content)
        elif element.name == 'table':
            table_md = convert_table_to_markdown(element)
            markdown_lines.append(table_md + '\n')
        elif element.name == 'img':
            img_src = element.get('src', '')
            markdown_lines.append(f"![image]({img_src})\n")
        elif element.name in ['ol', 'ul']:
            list_items = element.find_all(['li'])
            for i, li in enumerate(list_items):
                content = process_enml_elements(li)
                # 添加 Markdown 列表符号
                if element.name == 'ol':
                    markdown_lines.append(f"{i + 1}. {content}\n")
                else:
                    markdown_lines.append(f"* {content}\n")
        # 处理注释 <!-- -->
        elif element.name == 'comment':
            continue
        else:
            # 处理其他标签
            content = process_enml_elements(element)
            markdown_lines.append(content)
    return ''.join(markdown_lines)

def convert_table_to_markdown(table_tag):
    rows = table_tag.find_all('tr')
    table_data = []
    for row in rows:
        cols = row.find_all(['td', 'th'])
        row_data = []
        for col in cols:
            cell_text = ''.join(col.stripped_strings)
            row_data.append(cell_text)
        table_data.append(row_data)

    # 确定列数
    col_count = max(len(row) for row in table_data)

    # 生成 Markdown 表格
    md_table = []
    header = table_data[0]
    md_table.append('| ' + ' | '.join(header) + ' |')
    md_table.append('|' + ' --- |' * col_count)
    for row in table_data[1:]:
        # 如果某行列数不足，填充空字符串
        if len(row) < col_count:
            row.extend([''] * (col_count - len(row)))
        md_table.append('| ' + ' | '.join(row) + ' |')
    return '\n'.join(md_table)


def save_markdown_file(title, note_data, markdown_content, output_dir):
    try:
        md_filename = f"{sanitize_filename(title)}.md"
        md_filepath = os.path.join(output_dir, md_filename)        
        file_index = 1
        while os.path.exists(md_filepath):
            md_filename = f"{sanitize_filename(title)}_{file_index}.md"
            md_filepath = os.path.join(output_dir, md_filename)
            file_index += 1

        with open(md_filepath, 'w', encoding='utf-8') as md_file:
            md_file.write(f"---\n")
            md_file.write(f"title: {title}\n")
            md_file.write(f"created: {note_data['created']}\n")
            md_file.write(f"updated: {note_data['updated']}\n")
            if note_data['source_url']:
                md_file.write(f"source: {note_data['source_url']}\n")
            md_file.write(f"---\n\n")
            md_file.write(markdown_content)
        logging.info(f"保存Markdown文件: {md_filepath}")
    except Exception as e:
        logging.error(f"保存{title}.md失败: {e}")

def calculate_md5_hash(data):
    import hashlib
    md5 = hashlib.md5()
    md5.update(base64.b64decode(data))
    return md5.hexdigest()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.argv.append("test.enex")
        sys.argv.append("output_1")

    parser = argparse.ArgumentParser(description="解析Evernote ENEX文件并生成Markdown文件。")
    parser.add_argument('enex_file', help='ENEX文件路径')
    parser.add_argument('output_dir', nargs='?', default='output', help='输出目录')
    args = parser.parse_args()

    parse_enex(args.enex_file, args.output_dir)
