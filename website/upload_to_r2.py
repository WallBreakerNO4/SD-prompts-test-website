import os
import boto3
from pathlib import Path
import mimetypes
import sqlite3
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm  # 添加进度条支持

# Cloudflare R2配置
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_ENDPOINT = os.getenv('R2_ENDPOINT')
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME')
R2_CUSTOM_DOMAIN = "noobai-images.wall-breaker-no4.xyz"  # 自定义域名

# 全局的 S3 客户端和 bucket 实例
s3_client = None
r2_bucket = None

def init_r2_client():
    """初始化 R2 客户端和 bucket"""
    global s3_client, r2_bucket
    if s3_client is None:
        s3_client = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY
        )
        r2_bucket = boto3.resource(
            's3',
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY
        ).Bucket(R2_BUCKET_NAME)
    return s3_client, r2_bucket

def get_mime_type(file_path):
    """获取文件的MIME类型"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or 'application/octet-stream'

def upload_file_to_r2(file_path, bucket, key):
    """上传文件到R2并返回URL"""
    try:
        content_type = get_mime_type(file_path)
        bucket.upload_file(
            file_path,
            key,
            ExtraArgs={'ContentType': content_type}
        )
        return f"https://{R2_CUSTOM_DOMAIN}/{key}"
    except Exception as e:
        print(f"Error uploading {file_path}: {e}")
        return None

def upload_single_image(args):
    """单个图片上传函数，用于多线程处理"""
    full_path, batch_name, r2_bucket = args
    # 使用原始路径作为键
    image_path = str(full_path.name)  # 只使用文件名
    r2_key = f"{batch_name}/{image_path}"
    
    r2_url = upload_file_to_r2(str(full_path), r2_bucket, r2_key)
    if r2_url:
        return image_path, r2_url
    return None

def process_batch(batch_path):
    """处理单个批次的图片上传"""
    global s3_client, r2_bucket
    if s3_client is None or r2_bucket is None:
        s3_client, r2_bucket = init_r2_client()

    db_path = batch_path / 'image_generation.db'
    if not db_path.exists():
        print(f"Database not found for batch {batch_path}")
        return
    
    # 连接数据库
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 获取所有图片记录
    cursor.execute('SELECT image_path FROM image_records')
    image_paths = cursor.fetchall()
    
    if not image_paths:
        print("No images found in database")
        conn.close()
        return
    
    print(f"\n开始上传 {len(image_paths)} 张图片...")
    
    # 创建URL映射文件
    url_mapping = {}
    
    # 准备上传任务
    upload_tasks = []
    for (image_path,) in image_paths:
        full_path = batch_path / image_path
        if not full_path.exists():
            print(f"Image not found: {full_path}")
            continue
        upload_tasks.append((full_path, batch_path.name, r2_bucket))
    
    # 使用线程池并行上传
    max_workers = min(32, len(upload_tasks))  # 最多32个线程
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务并使用tqdm显示进度
        futures = [executor.submit(upload_single_image, task) for task in upload_tasks]
        
        with tqdm(total=len(futures), desc="上传进度") as pbar:
            for future in as_completed(futures):
                result = future.result()
                if result:
                    image_path, r2_url = result
                    url_mapping[image_path] = r2_url
                pbar.update(1)
    
    # 保存URL映射
    if url_mapping:
        mapping_file = batch_path / 'r2_url_mapping.json'
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(url_mapping, f, ensure_ascii=False, indent=2)
        print(f"\n成功上传 {len(url_mapping)} 张图片")
        print(f"URL映射已保存到: {mapping_file}")
    else:
        print("\n没有成功上传任何图片")
    
    conn.close()

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='上传图片到R2存储')
    parser.add_argument('--batch', type=str, help='指定要上传的批次名称，例如：20250102-014551')
    args = parser.parse_args()

    if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT, R2_BUCKET_NAME]):
        print("Please set all required environment variables")
        return
    
    # 初始化 R2 客户端
    init_r2_client()
    
    # 处理批次
    base_path = Path('static/generate_images/batch')
    if not base_path.exists():
        print(f"Base path not found: {base_path}")
        return

    if args.batch:
        # 处理指定的批次
        batch_path = base_path / args.batch
        if not batch_path.exists() or not batch_path.is_dir():
            print(f"指定的批次不存在: {batch_path}")
            return
        print(f"\nProcessing specified batch: {batch_path}")
        process_batch(batch_path)
    else:
        # 处理所有批次
        print("\n未指定批次，将处理所有批次")
        for batch_path in base_path.iterdir():
            if batch_path.is_dir():
                print(f"\nProcessing batch: {batch_path}")
                process_batch(batch_path)

if __name__ == '__main__':
    main() 