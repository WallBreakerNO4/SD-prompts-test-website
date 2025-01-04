from flask import Flask, render_template, send_from_directory, abort, url_for
import sqlite3
from datetime import datetime, timedelta
import shutil
from pathlib import Path
import json
import os
from web_config import get_batch_config, get_enabled_batches
from functools import lru_cache
from contextlib import contextmanager
from typing import Optional, Tuple, Dict, List

# 缓存版本号，当缓存结构发生变化时递增
CACHE_VERSION = 1
# 缓存过期时间（秒）
CACHE_EXPIRE_TIME = 24 * 60 * 60  # 24小时

app = Flask(__name__)

# 创建数据库连接池
class DatabasePool:
    def __init__(self):
        self._connections = {}
        
    @contextmanager
    def get_connection(self, db_path: str):
        if db_path not in self._connections:
            self._connections[db_path] = sqlite3.connect(db_path)
        try:
            yield self._connections[db_path]
        except Exception as e:
            if db_path in self._connections:
                self._connections[db_path].close()
                del self._connections[db_path]
            raise e

db_pool = DatabasePool()

def ensure_directory_exists(path):
    """确保目录存在，如果不存在则创建"""
    Path(path).mkdir(parents=True, exist_ok=True)

def get_cache_path(batch_name):
    """获取缓存文件路径"""
    cache_dir = Path('static') / 'cache'
    ensure_directory_exists(cache_dir)
    return cache_dir / f"{batch_name}_matrix_v{CACHE_VERSION}.json"

@lru_cache(maxsize=32)
def get_file_mtime(file_path: str) -> float:
    """获取文件修改时间，使用LRU缓存优化性能"""
    return os.path.getmtime(file_path)

def is_cache_valid(batch_name):
    """检查缓存是否有效"""
    cache_path = get_cache_path(batch_name)
    if not cache_path.exists():
        return False
    
    # 获取所有相关文件路径
    batch_path = Path('static') / 'generate_images' / 'batch' / batch_name
    db_path = batch_path / 'image_generation.db'
    r2_mapping_path = batch_path / 'r2_url_mapping.json'
    
    # 基本文件检查
    if not db_path.exists() or not r2_mapping_path.exists():
        return False
    
    try:
        # 检查缓存是否过期
        cache_time = get_file_mtime(str(cache_path))
        current_time = datetime.now().timestamp()
        if current_time - cache_time > CACHE_EXPIRE_TIME:
            return False
        
        # 检查源文件是否有更新
        db_time = get_file_mtime(str(db_path))
        r2_time = get_file_mtime(str(r2_mapping_path))
        if cache_time <= max(db_time, r2_time):
            return False
        
        # 验证缓存内容和版本
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            if cache_data.get('version') != CACHE_VERSION:
                return False
            
            matrix = cache_data.get('matrix', {})
            return any(url and url.startswith('http') 
                      for artist in matrix.values() 
                      for url in artist.values() 
                      if url)
            
    except Exception as e:
        print(f"缓存验证出错: {e}")
        return False

def save_matrix_cache(batch_name, matrix, artists, prompts):
    """保存矩阵数据到缓存"""
    cache_data = {
        'version': CACHE_VERSION,
        'timestamp': datetime.now().timestamp(),
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
                    "path": str(batch_path),
                    "civitai_url": config.get("civitai_url", ""),
                    "huggingface_url": config.get("huggingface_url", "")
                })
    
    return sorted(batches, key=lambda x: x["name"], reverse=True)

def get_matrix_data(batch_name):
    """获取指定批次的矩阵式组织的图片数据"""
    if is_cache_valid(batch_name):
        return load_matrix_cache(batch_name)
    
    batch_path = Path('static') / 'generate_images' / 'batch' / batch_name
    db_path = batch_path / 'image_generation.db'
    r2_mapping_path = batch_path / 'r2_url_mapping.json'
    
    if not db_path.exists() or not r2_mapping_path.exists():
        return None, None, None
    
    try:
        # 加载R2 URL映射
        with open(r2_mapping_path, 'r', encoding='utf-8') as f:
            r2_mapping = json.load(f)
        
        # 数据库操作
        with db_pool.get_connection(str(db_path)) as conn:
            cursor = conn.cursor()
            
            # 获取所有不同的艺术家和提示词
            cursor.execute('SELECT DISTINCT artist_prompt FROM image_records ORDER BY artist_prompt DESC')
            artists = [row[0] for row in cursor.fetchall()]
            
            cursor.execute('SELECT DISTINCT prompt_text FROM image_records ORDER BY prompt_text DESC')
            prompts = [row[0] for row in cursor.fetchall()]
            
            # 使用单个SQL查询获取所有数据
            cursor.execute('''
                SELECT artist_prompt, prompt_text, image_path 
                FROM image_records 
                WHERE artist_prompt IN ({}) AND prompt_text IN ({})
            '''.format(
                ','.join('?' * len(artists)),
                ','.join('?' * len(prompts))
            ), artists + prompts)
            
            # 创建矩阵
            matrix = {artist: {prompt: None for prompt in prompts} for artist in artists}
            match_count = 0
            
            # 填充矩阵
            for artist_prompt, prompt_text, image_path in cursor.fetchall():
                url = r2_mapping.get(image_path) or r2_mapping.get(Path(image_path).name)
                if url:
                    matrix[artist_prompt][prompt_text] = url
                    match_count += 1
            
            print(f"总共找到 {match_count} 个匹配的图片URL")
            
            # 保存到缓存
            save_matrix_cache(batch_name, matrix, artists, prompts)
            
            return matrix, artists, prompts
            
    except Exception as e:
        print(f"处理数据时出错: {e}")
        return None, None, None

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
            
            # 如果没有数据，返回错误信息
            if matrix is None or artists is None or prompts is None:
                return render_template('error.html', 
                                    message="此批次的图片尚未上传到图床，请先运行上传脚本。",
                                    back_url=url_for('home'))
            
            return render_template('batch.html', 
                                matrix=matrix, 
                                artists=artists, 
                                prompts=prompts, 
                                batch_name=batch_name,
                                display_name=config["display_name"],
                                config=config)
    
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