import re

def extract_images(content):
    """提取markdown文件中的图片路径"""
    # pattern = r'!\[.*?\]\((.*?)\)'
    pattern = r'!\[\[(.*?)\]\]'
    return re.findall(pattern, content)

def replace_images(source_content, target_content):
    """替换目标文档中的图片路径"""
    source_images = extract_images(source_content)
    
    def replace_func(match):
        if source_images:
            # 保持原始的alt文本，只替换图片路径
            return f'![{match.group(1)}]({source_images.pop(0)})'
        return match.group(0)
    
    # 使用正则表达式替换图片路径
    pattern = r'!\[(.*?)\]\(.*?\)'
    return re.sub(pattern, replace_func, target_content)

def main(source_file, target_file):
    # 读取源文件
    with open(source_file, 'r', encoding='utf-8') as f:
        source_content = f.read()
    
    # 读取目标文件
    with open(target_file, 'r', encoding='utf-8') as f:
        target_content = f.read()
    
    # 替换图片
    new_content = replace_images(source_content, target_content)
    
    # 保存更新后的文件
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

if __name__ == '__main__':
    source_file = r'docA.md'  # A文档路径
    target_file = r'docB.md'  # B文档路径
    main(source_file, target_file)
