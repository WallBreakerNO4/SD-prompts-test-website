from flask import Flask, render_template
import sqlite3
from datetime import datetime
import shutil
from pathlib import Path
import json
import os

app = Flask(__name__)

def ensure_directory_exists(path):
    """确保目录存在，如果不存在则创建"""
    Path(path).mkdir(parents=True, exist_ok=True)

def get_cache_path(batch_name):
    """获取缓存文件路径"""
    cache_dir = Path('static') / 'cache'
    ensure_directory_exists(cache_dir)
    return cache_dir / f"{batch_name}_matrix.json"

def is_cache_valid(batch_name):
    """检查缓存是否有效"""
    cache_path = get_cache_path(batch_name)
    if not cache_path.exists():
        return False
    
    # 检查缓存文件的修改时间是否晚于数据库的修改时间
    db_path = Path('static') / 'generate_images' / 'batch' / batch_name / 'image_generation.db'
    if not db_path.exists():
        return False
    
    return os.path.getmtime(cache_path) > os.path.getmtime(db_path)

def save_matrix_cache(batch_name, matrix, artists, prompts):
    """保存矩阵数据到缓存"""
    cache_data = {
        'matrix': matrix,
        'artists': artists,
        'prompts': prompts
    }
    cache_path = get_cache_path(batch_name)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False)

def load_matrix_cache(batch_name):
    """从缓存加载矩阵数据"""
    cache_path = get_cache_path(batch_name)
    with open(cache_path, 'r', encoding='utf-8') as f:
        cache_data = json.load(f)
    return cache_data['matrix'], cache_data['artists'], cache_data['prompts']

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

def get_all_batches():
    """获取所有批次及其信息"""
    sync_images()
    batch_dir = Path('static') / 'generate_images' / 'batch'
    if not batch_dir.exists():
        return [], {}
    
    folders = [f for f in batch_dir.iterdir() if f.is_dir()]
    batches = [f.name for f in folders]
    batch_info = {}
    
    for batch in batches:
        db_path = batch_dir / batch / 'image_generation.db'
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM image_records')
            image_count = cursor.fetchone()[0]
            conn.close()
            batch_info[batch] = {
                'image_count': image_count
            }
    
    return sorted(batches, reverse=True), batch_info

def get_matrix_data(batch_name):
    """获取指定批次的矩阵式组织的图片数据"""
    # 检查是否有有效的缓存
    if is_cache_valid(batch_name):
        return load_matrix_cache(batch_name)
    
    batch_path = Path('static') / 'generate_images' / 'batch' / batch_name
    db_path = batch_path / 'image_generation.db'
    
    if not db_path.exists():
        return None, None, None
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 获取所有不同的艺术家和提示词
    cursor.execute('SELECT DISTINCT artist_prompt FROM image_records ORDER BY artist_prompt DESC')
    artists = [row[0] for row in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT prompt_text FROM image_records ORDER BY prompt_text DESC')
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
                url_path = '/'.join(['generate_images', 'batch', batch_name, result[0]])
                matrix[artist][prompt] = url_path
            else:
                matrix[artist][prompt] = None
    
    conn.close()
    
    # 保存到缓存
    save_matrix_cache(batch_name, matrix, artists, prompts)
    
    return matrix, artists, prompts

@app.route('/')
def home():
    batches, batch_info = get_all_batches()
    return render_template('home.html', batches=batches, batch_info=batch_info)

@app.route('/batch/<batch_name>')
def show_batch(batch_name):
    matrix, artists, prompts = get_matrix_data(batch_name)
    if not matrix:
        return "批次不存在或没有图片", 404
    
    return render_template('index.html', matrix=matrix, artists=artists, prompts=prompts, batch_name=batch_name)

if __name__ == '__main__':
    app.run(debug=True) 