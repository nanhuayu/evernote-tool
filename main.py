from converter import Converter

if __name__ == '__main__':
    # Convert ENEX to Markdown
    file_list = [
        '读书讲座电影音乐.enex', '国科大课程笔记.enex', '经验机会笔记.enex', '课堂笔记.enex', '理化所科研笔记.enex', 
        '数学笔记.enex', '项目规划笔记.enex', '娱乐.enex', '杂记.enex', '杂录.enex', 
    ]
    for enex_file in file_list:
        output_dir = 'output/' + enex_file.split('.')[0] + '/'
        Converter.enex_to_markdown(enex_file, output_dir)
    
    # # Convert Markdown to ENEX
    # markdown_dir = 'output/'
    # output_file = 'output/notes.enex'
    # Converter.markdown_to_enex(markdown_dir, output_file)
