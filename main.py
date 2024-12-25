from converter import Converter

if __name__ == '__main__':
    # Convert ENEX to Markdown
    enex_file = 'test.enex'
    output_dir = 'output_2/'
    Converter.enex_to_markdown(enex_file, output_dir)
    
    # # Convert Markdown to ENEX
    # markdown_dir = 'output/'
    # output_file = 'output/notes.enex'
    # Converter.markdown_to_enex(markdown_dir, output_file)
