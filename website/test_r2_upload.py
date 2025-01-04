import os
import boto3
from pathlib import Path
import mimetypes
import sqlite3
import json

# Cloudflare R2配置
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_ENDPOINT = os.getenv('R2_ENDPOINT')
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME')
R2_CUSTOM_DOMAIN = "noobai-images.wall-breaker-no4.xyz"  # 自定义域名

# 测试配置
TEST_BATCH_NAME = "20250102-014551"  # 替换为您要测试的批次名称
TEST_IMAGE_COUNT = 3  # 每个批次测试的图片数量

def get_mime_type(file_path):
    """获取文件的MIME类型"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or 'application/octet-stream'

def upload_file_to_r2(file_path, bucket, key):
    """上传文件到R2并返回URL"""
    try:
        content_type = get_mime_type(file_path)
        print(f"Uploading {file_path} with content type {content_type}")
        bucket.upload_file(
            file_path,
            key,
            ExtraArgs={'ContentType': content_type}
        )
        url = f"https://{R2_CUSTOM_DOMAIN}/{key}"
        print(f"Successfully uploaded to {url}")
        return url
    except Exception as e:
        print(f"Error uploading {file_path}: {e}")
        return None

def test_upload():
    """测试上传少量图片"""
    if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT, R2_BUCKET_NAME]):
        print("请设置所有必需的环境变量：")
        print("R2_ACCESS_KEY_ID")
        print("R2_SECRET_ACCESS_KEY")
        print("R2_ENDPOINT")
        print("R2_BUCKET_NAME")
        return

    print(f"开始测试上传到 {R2_BUCKET_NAME}")
    print(f"使用端点: {R2_ENDPOINT}")
    
    # 创建S3客户端（用于R2）
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name='auto'  # R2建议使用auto作为region
        )
        print("已创建S3客户端")
    except Exception as e:
        print(f"创建S3客户端失败: {e}")
        return

    # 获取bucket
    try:
        bucket = boto3.resource(
            's3',
            endpoint_url=R2_ENDPOINT,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name='auto'
        ).Bucket(R2_BUCKET_NAME)
        print("已获取bucket对象")
    except Exception as e:
        print(f"获取bucket失败: {e}")
        return

    # 处理测试批次
    batch_path = Path('static/generate_images/batch') / TEST_BATCH_NAME
    if not batch_path.exists():
        print(f"找不到测试批次: {batch_path}")
        return

    db_path = batch_path / 'image_generation.db'
    if not db_path.exists():
        print(f"找不到数据库: {db_path}")
        return

    print(f"找到批次目录: {batch_path}")
    print(f"找到数据库: {db_path}")

    # 连接数据库
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 获取前几张图片进行测试
    cursor.execute('SELECT image_path FROM image_records LIMIT ?', (TEST_IMAGE_COUNT,))
    image_paths = cursor.fetchall()

    if not image_paths:
        print("没有找到图片记录")
        conn.close()
        return

    # 创建URL映射文件
    url_mapping = {}
    
    print(f"\n准备上传 {len(image_paths)} 张图片进行测试...")
    
    for (image_path,) in image_paths:
        full_path = batch_path / image_path
        if not full_path.exists():
            print(f"找不到图片文件: {full_path}")
            continue

        print(f"\n处理图片: {image_path}")
        print(f"完整路径: {full_path}")
        
        # 在R2中使用相同的路径结构
        r2_key = f"{TEST_BATCH_NAME}/{image_path}"
        print(f"目标R2路径: {r2_key}")
        
        # 上传文件
        r2_url = upload_file_to_r2(str(full_path), bucket, r2_key)
        if r2_url:
            url_mapping[image_path] = r2_url

    if url_mapping:
        # 保存测试URL映射
        mapping_file = batch_path / 'r2_url_mapping_test.json'
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(url_mapping, f, ensure_ascii=False, indent=2)
        print(f"\n成功上传 {len(url_mapping)} 张图片")
        print(f"URL映射已保存到: {mapping_file}")
    else:
        print("\n没有成功上传任何图片")

    conn.close()

if __name__ == '__main__':
    test_upload() 