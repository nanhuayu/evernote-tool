import os
import shutil

def classify_files(source_dir, target_dir):
    """
    根据target_dir的目录结构来整理source_dir中的文件
    
    Args:
        source_dir: 源文件夹路径
        target_dir: 参考的目标文件夹路径
    """
    # 遍历目标目录结构
    for root, dirs, files in os.walk(target_dir):
        for filename in files:
            if not filename.endswith('.md'):
                continue
                
            # 获取源文件路径
            source_path = os.path.join(source_dir, filename)
            if not os.path.exists(source_path):
                continue
                
            # 构建新的目标路径
            rel_path = os.path.relpath(root, target_dir)
            new_dir = os.path.join(source_dir, rel_path)
            new_path = os.path.join(new_dir, filename)
            
            # 创建目标目录
            os.makedirs(new_dir, exist_ok=True)
            
            # 移动文件
            shutil.move(source_path, new_path)
            print(f"已移动 {filename} 到 {new_path}")

if __name__ == '__main__':
    # 设置源目录和目标目录
    source_dir = 'output'  # 第一个文件夹
    target_dir = 'output_1' # 第二个文件夹
    
    classify_files(source_dir, target_dir)
