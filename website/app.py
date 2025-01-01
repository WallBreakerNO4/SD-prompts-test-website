from flask import Flask, render_template
import sqlite3
from datetime import datetime
import shutil
from pathlib import Path

app = Flask(__name__)

def ensure_directory_exists(path):
    """确保目录存在，如果不存在则创建"""
    Path(path).mkdir(parents=True, exist_ok=True)

def sync_images():
    """同步图片文件到static目录"""
    source_dir = Path('..') / 'generate_images' / 'batch'
    target_dir = Path('static') / 'generate_images' / 'batch'
    
    # 如果源目录不存在，返回False
    if not source_dir.exists():
        return False
        
    # 确保目标目录存在
    ensure_directory_exists(target_dir.parent)
    ensure_directory_exists(target_dir)
    
    # 复制所有批次文件夹
    for batch in source_dir.iterdir():
        if batch.is_dir():
            target_batch_dir = target_dir / batch.name
            if not target_batch_dir.exists():
                shutil.copytree(batch, target_batch_dir)
    
    return True

def get_latest_batch():
    """获取最新的批次文件夹"""
    # 首先同步图片
    sync_images()
    
    batch_dir = Path('static') / 'generate_images' / 'batch'
    if not batch_dir.exists():
        return None
    
    folders = [f for f in batch_dir.iterdir() if f.is_dir()]
    if not folders:
        return None
    
    return max(f.name for f in folders)

def get_matrix_data():
    """获取矩阵式组织的图片数据"""
    latest_batch = get_latest_batch()
    if not latest_batch:
        return None, None, None
    
    batch_path = Path('static') / 'generate_images' / 'batch' / latest_batch
    db_path = batch_path / 'image_generation.db'
    
    if not db_path.exists():
        return None, None, None
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 获取所有不同的艺术家和提示词
    cursor.execute('SELECT DISTINCT artist_prompt FROM image_records ORDER BY artist_prompt')
    artists = [row[0] for row in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT prompt_text FROM image_records ORDER BY prompt_text')
    prompts = [row[0] for row in cursor.fetchall()]
    
    # 创建图片矩阵
    matrix = {}
    for artist in artists:
        matrix[artist] = {}
        for prompt in prompts:
            cursor.execute('''
                SELECT image_path 
                FROM image_records 
                WHERE artist_prompt = ? AND prompt_text = ?
            ''', (artist, prompt))
            result = cursor.fetchone()
            if result:
                # 使用正斜杠构建URL路径
                url_path = '/'.join(['generate_images', 'batch', latest_batch, result[0]])
                matrix[artist][prompt] = url_path
            else:
                matrix[artist][prompt] = None
    
    conn.close()
    return matrix, artists, prompts

@app.route('/')
def index():
    matrix, artists, prompts = get_matrix_data()
    if not matrix:
        return "No images found", 404
    
    batch_name = get_latest_batch()
    return render_template('index.html', matrix=matrix, artists=artists, prompts=prompts, batch_name=batch_name)

if __name__ == '__main__':
    app.run(debug=True) 