from flask import Flask, render_template, send_from_directory, abort
import sqlite3
from datetime import datetime, timedelta
import shutil
from pathlib import Path
import json
import os
from web_config import get_batch_config, get_enabled_batches

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
    """获取所有批次信息"""
    batch_dir = Path('static/generate_images/batch')
    if not batch_dir.exists():
        return []
    
    batches = []
    for batch_path in batch_dir.iterdir():
        if batch_path.is_dir():
            batch_name = batch_path.name
            full_path = f"batch/{batch_name}"
            config = get_batch_config(full_path)
            if config.get("enabled", False):
                batches.append({
                    "name": batch_name,
                    "display_name": config["display_name"],
                    "url_path": config["url_path"],
                    "path": str(batch_path)
                })
    
    return sorted(batches, key=lambda x: x["name"], reverse=True)

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
    batches = get_all_batches()
    return render_template('index.html', batches=batches)

@app.route('/batch/<url_path>')
def show_batch(url_path):
    # 查找对应的原始批次路径
    for batch_path, config in get_enabled_batches().items():
        if config["url_path"] == url_path:
            batch_name = batch_path.split("/")[-1]
            matrix, artists, prompts = get_matrix_data(batch_name)
            return render_template('batch.html', 
                                matrix=matrix, 
                                artists=artists, 
                                prompts=prompts, 
                                batch_name=batch_name,
                                display_name=config["display_name"])
    
    abort(404)  # 如果找不到对应的批次，返回404错误

@app.after_request
def add_header(response):
    """为所有响应添加缓存控制头"""
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store'
    return response

@app.route('/static/generate_images/batch/<path:filename>')
def serve_image(filename):
    """专门处理图片文件的路由，添加缓存控制"""
    response = send_from_directory('static/generate_images/batch', filename)
    # 设置缓存时间为30天
    response.headers['Cache-Control'] = 'public, max-age=2592000'
    response.headers['Expires'] = (datetime.utcnow() + timedelta(days=30)).strftime('%a, %d %b %Y %H:%M:%S GMT')
    return response

if __name__ == '__main__':
    app.run(debug=True) 