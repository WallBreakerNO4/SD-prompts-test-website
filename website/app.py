from flask import Flask, render_template, send_from_directory, abort, url_for
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
        print("缓存文件不存在")
        return False
    
    # 检查缓存文件的修改时间是否晚于数据库的修改时间
    db_path = Path('static') / 'generate_images' / 'batch' / batch_name / 'image_generation.db'
    r2_mapping_path = Path('static') / 'generate_images' / 'batch' / batch_name / 'r2_url_mapping.json'
    r2_mapping_test_path = Path('static') / 'generate_images' / 'batch' / batch_name / 'r2_url_mapping_test.json'
    
    if not db_path.exists():
        print("数据库文件不存在")
        return False
    
    # 检查缓存的内容是否都是http URL
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
            matrix = cache_data.get('matrix', {})
            
            # 检查是否有任何有效的URL
            has_valid_url = False
            for artist in matrix:
                for prompt in matrix[artist]:
                    url = matrix[artist][prompt]
                    if url and url.startswith('http'):
                        has_valid_url = True
                        break
                if has_valid_url:
                    break
            
            if not has_valid_url:
                print("缓存中没有有效的URL")
                return False
            
    except Exception as e:
        print(f"读取缓存文件出错: {e}")
        return False
    
    # 检查缓存是否需要更新
    cache_time = os.path.getmtime(cache_path)
    db_time = os.path.getmtime(db_path)
    
    # 如果存在任一映射文件，检查其修改时间
    if r2_mapping_path.exists():
        r2_time = os.path.getmtime(r2_mapping_path)
        if cache_time < r2_time:
            print("正式版映射文件已更新")
            return False
            
    if r2_mapping_test_path.exists():
        r2_test_time = os.path.getmtime(r2_mapping_test_path)
        if cache_time < r2_test_time:
            print("测试版映射文件已更新")
            return False
    
    # 如果没有任何映射文件存在，强制重新生成
    if not r2_mapping_path.exists() and not r2_mapping_test_path.exists():
        print("没有找到任何映射文件")
        return False
    
    if cache_time <= db_time:
        print("缓存早于数据库")
        return False
        
    print("缓存验证通过")
    return True

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
                    "path": str(batch_path),
                    "civitai_url": config.get("civitai_url", ""),
                    "huggingface_url": config.get("huggingface_url", "")
                })
    
    return sorted(batches, key=lambda x: x["name"], reverse=True)

def get_matrix_data(batch_name):
    """获取指定批次的矩阵式组织的图片数据"""
    print(f"\n开始处理批次: {batch_name}")
    
    # 检查是否有有效的缓存
    if is_cache_valid(batch_name):
        print("使用缓存数据")
        return load_matrix_cache(batch_name)
    else:
        print("缓存无效，重新生成数据")
    
    batch_path = Path('static') / 'generate_images' / 'batch' / batch_name
    db_path = batch_path / 'image_generation.db'
    r2_mapping_path = batch_path / 'r2_url_mapping.json'
    r2_mapping_test_path = batch_path / 'r2_url_mapping_test.json'
    
    print(f"数据库路径: {db_path}")
    print(f"R2映射文件路径: {r2_mapping_path}")
    print(f"R2测试映射文件路径: {r2_mapping_test_path}")
    
    if not db_path.exists():
        print("数据库文件不存在")
        return None, None, None
    
    # 加载R2 URL映射，优先使用测试版映射文件
    r2_mapping = {}
    if r2_mapping_test_path.exists():
        print("使用测试版映射文件")
        with open(r2_mapping_test_path, 'r', encoding='utf-8') as f:
            r2_mapping = json.load(f)
    elif r2_mapping_path.exists():
        print("使用正式版映射文件")
        with open(r2_mapping_path, 'r', encoding='utf-8') as f:
            r2_mapping = json.load(f)
    
    print(f"加载到的R2映射数据: {json.dumps(r2_mapping, indent=2)}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 获取所有不同的艺术家和提示词
    cursor.execute('SELECT DISTINCT artist_prompt FROM image_records ORDER BY artist_prompt DESC')
    artists = [row[0] for row in cursor.fetchall()]
    
    cursor.execute('SELECT DISTINCT prompt_text FROM image_records ORDER BY prompt_text DESC')
    prompts = [row[0] for row in cursor.fetchall()]
    
    print(f"找到 {len(artists)} 个艺术家, {len(prompts)} 个提示词")
    
    # 创建图片矩阵
    matrix = {}
    match_count = 0
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
                # 获取相对路径，与upload_to_r2.py中的处理方式保持一致
                image_path = result[0]
                print(f"检查图片: {image_path}")
                if image_path in r2_mapping:
                    print(f"找到R2 URL: {r2_mapping[image_path]}")
                    matrix[artist][prompt] = r2_mapping[image_path]
                    match_count += 1
                else:
                    # 尝试不同的路径格式
                    alt_path = str(Path(image_path).name)
                    if alt_path in r2_mapping:
                        print(f"使用替代路径找到R2 URL: {r2_mapping[alt_path]}")
                        matrix[artist][prompt] = r2_mapping[alt_path]
                        match_count += 1
                    else:
                        print(f"未找到对应的R2 URL，尝试过的路径: {image_path}, {alt_path}")
                        matrix[artist][prompt] = None
            else:
                matrix[artist][prompt] = None
    
    print(f"总共找到 {match_count} 个匹配的图片URL")
    
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