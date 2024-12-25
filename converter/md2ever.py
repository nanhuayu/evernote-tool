import os
import sys
import time
import logging
import argparse
import markdown2
import base64
import mimetypes
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup, CData

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class MarkdownToENEXConverter:
    def __init__(self, markdown_file, output_file, assets_dir='assets', author="Your Name", source_url=""):
        self.markdown_file = markdown_file
        self.output_file = output_file
        self.assets_dir = assets_dir
        self.author = author
        self.source_url = source_url
        os.makedirs(self.assets_dir, exist_ok=True)
        logging.info(f"附件目录: {self.assets_dir}")

    def sanitize_filename(self, name):
        """移除文件名中的非法字符"""
        return ''.join(c for c in name if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()

    def convert_markdown_to_html(self, markdown_content):
        """将 Markdown 转换为 HTML"""
        html = markdown2.markdown(markdown_content, extras=["fenced-code-blocks", "tables"])
        logging.debug("Markdown 转换为 HTML 成功")
        return html

    def embed_resources(self, html_content):
        """处理 HTML 中的图片和附件，编码为 ENEX 所需的格式"""
        soup = BeautifulSoup(html_content, 'html.parser')
        resources = []

        # 处理图片
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue
            resource, new_src = self.create_resource(src)
            if resource:
                resources.append(resource)
                img['hash'] = resource['hash']
                del img['src']
            else:
                logging.warning(f"无法处理图片：{src}")

        # 转换表格样式（可选，根据需要调整）
        # 可以在此添加对表格的特殊处理

        return str(soup), resources

    def create_resource(self, src):
        """创建资源（图片或附件）并返回资源信息和新的引用"""
        if src.startswith('http://') or src.startswith('https://'):
            # 下载图片或附件
            try:
                import requests
                response = requests.get(src)
                response.raise_for_status()
                data = response.content
                mime_type = response.headers.get('Content-Type', 'application/octet-stream')
                file_extension = mimetypes.guess_extension(mime_type) or '.bin'
                filename = self.sanitize_filename(os.path.basename(src)) or f"image_{int(time.time())}{file_extension}"
            except Exception as e:
                logging.error(f"下载资源失败：{src} - {e}")
                return None, src
        else:
            # 本地文件
            file_path = os.path.join(os.path.dirname(self.markdown_file), src)
            if not os.path.exists(file_path):
                logging.error(f"本地资源文件不存在：{file_path}")
                return None, src
            with open(file_path, 'rb') as f:
                data = f.read()
            mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            filename = self.sanitize_filename(os.path.basename(file_path))

        # 计算 MD5 哈希值
        md5_hash = hashlib.md5(data).hexdigest()

        # 创建资源字典
        resource = {
            'data': base64.b64encode(data).decode('utf-8'),
            'mime': mime_type,
            'hash': md5_hash,
            'file_name': filename
        }

        logging.info(f"创建资源：{filename}，类型：{mime_type}")

        # 保存附件到 assets 目录（可选）
        attachment_path = os.path.join(self.assets_dir, filename)
        with open(attachment_path, 'wb') as f:
            f.write(data)
        logging.debug(f"保存资源文件：{attachment_path}")

        return resource, f"hash::{md5_hash}"

    def create_enex_note(self, title, html_content, resources, created, updated):
        """创建 ENEX 格式的笔记，包括资源信息"""
        en_note = BeautifulSoup(features='xml')
        en_note.append(BeautifulSoup(
            '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">', 'xml'))

        # 添加笔记内容
        en_note_body = BeautifulSoup(html_content, 'html.parser')
        en_note.append(en_note_body)

        # 构建资源列表
        resource_elements = []
        for res in resources:
            resource_element = self.build_resource_element(res)
            resource_elements.append(resource_element)

        # 构建笔记
        note = f"""
<note>
    <title>{title}</title>
    <content><![CDATA[{str(en_note)}]]></content>
    {''.join(resource_elements)}
    <created>{created}</created>
    <updated>{updated}</updated>
    <note-attributes>
        <author>{self.author}</author>
        <source>{self.source_url or 'markdown_to_enex'}</source>
    </note-attributes>
</note>
"""
        logging.debug(f"创建 ENEX 笔记：{title}")
        return note

    def build_resource_element(self, resource):
        """构建资源（图片、附件）的 XML 元素"""
        resource_xml = f"""
    <resource>
        <data encoding="base64">{resource['data']}</data>
        <mime>{resource['mime']}</mime>
        <resource-attributes>
            <file-name>{resource['file_name']}</file-name>
        </resource-attributes>
    </resource>
"""
        return resource_xml

    def generate_enex(self):
        """生成 ENEX 文件"""
        with open(self.markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        title = os.path.splitext(os.path.basename(self.markdown_file))[0]
        html_content = self.convert_markdown_to_html(markdown_content)

        # 处理资源，获取更新后的 HTML 内容和资源列表
        html_content, resources = self.embed_resources(html_content)

        # 提取创建和修改时间（可自行修改获取方式）
        created = updated = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

        # 创建 ENEX 笔记
        note = self.create_enex_note(title, html_content, resources, created, updated)

        # 构建 ENEX 文件
        enex_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE en-export SYSTEM "http://xml.evernote.com/pub/evernote-export2.dtd">
<en-export export-date="{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}" application="MarkdownToENEX" version="1.0">
{note}
</en-export>
"""

        # 保存 ENEX 文件
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(enex_content)
        logging.info(f"ENEX 文件已生成：{self.output_file}")


def main():
    parser = argparse.ArgumentParser(description="将 Markdown 文件转换为 Evernote ENEX 格式。")
    parser.add_argument('markdown_file', help='Markdown 文件路径')
    parser.add_argument('output_file', help='输出的 ENEX 文件路径')
    parser.add_argument('--assets_dir', default='assets', help='附件保存目录')
    parser.add_argument('--author', default='Your Name', help='笔记作者名称')
    parser.add_argument('--source_url', default='', help='笔记来源 URL')
    args = parser.parse_args()

    converter = MarkdownToENEXConverter(
        markdown_file=args.markdown_file,
        output_file=args.output_file,
        assets_dir=args.assets_dir,
        author=args.author,
        source_url=args.source_url
    )
    converter.generate_enex()


if __name__ == '__main__':
    main()
