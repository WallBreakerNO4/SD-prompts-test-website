import os
import pandas as pd
import sqlite3
from datetime import datetime
from tqdm import tqdm
from config import *
from generate_image import generate_images_batch

def get_batch_dir():
    """获取当前批次的目录路径"""
    current_date = datetime.now().strftime("%Y%m%d")
    current_time = datetime.now().strftime("%H%M%S")
    batch_dir = os.path.join("website", "static", "generate_images", "batch", f"{current_date}-{current_time}")
    if not os.path.exists(batch_dir):
        os.makedirs(batch_dir)
    return batch_dir

def init_database(batch_dir):
    """初始化SQLite数据库"""
    db_path = os.path.join(batch_dir, 'image_generation.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建图片生成记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS image_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_path TEXT NOT NULL,
        artist_file TEXT NOT NULL,
        artist_prompt TEXT NOT NULL,
        prompt_file TEXT NOT NULL,
        prompt_text TEXT NOT NULL,
        combined_prompt TEXT NOT NULL,
        generation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    return conn

def list_csv_files(directory):
    """列出指定目录下的所有CSV文件"""
    files = [f for f in os.listdir(directory) if f.endswith('.csv')]
    return files

def select_file(files, folder_name):
    """让用户从文件列表中选择一个文件"""
    print(f"\n{folder_name}中的CSV文件：")
    for i, file in enumerate(files, 1):
        print(f"{i}. {file}")
    
    while True:
        try:
            choice = int(input(f"\n请选择一个{folder_name}中的文件 (输入数字): "))
            if 1 <= choice <= len(files):
                return files[choice - 1]
            print("无效的选择，请重试")
        except ValueError:
            print("请输入有效的数字")

def read_csv_content(file_path):
    """读取CSV文件内容"""
    # 使用正确的参数读取CSV文件
    df = pd.read_csv(file_path, header=None, skip_blank_lines=True)
    # 删除空行和只包含空白字符的行
    df = df.dropna()
    df = df[df[0].str.strip().astype(bool)]
    return df[0].tolist()

def save_generation_record(conn, image_path, artist_file, artist_prompt, prompt_file, prompt_text, combined_prompt):
    """保存图片生成记录到数据库"""
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO image_records (image_path, artist_file, artist_prompt, prompt_file, prompt_text, combined_prompt)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (image_path, artist_file, artist_prompt, prompt_file, prompt_text, combined_prompt))
    conn.commit()

def generate_and_save_with_record(prompt, artist_file, artist_prompt, prompt_file, prompt_text, conn, batch_dir):
    """生成图片并保存记录"""
    # 生成时间戳
    timestamp = datetime.now().strftime("%H%M%S")
    
    # 生成图片
    images = generate_images_batch([prompt])
    
    # 生成文件名
    image_filename = f"image_{timestamp}_0.{IMAGE_SAVE_FORMAT}"
    image_path = os.path.join(batch_dir, image_filename)
    
    # 保存图片
    images[0].save(image_path, format=IMAGE_SAVE_FORMAT, quality=IMAGE_QUALITY)
    
    # 保存记录到数据库
    save_generation_record(
        conn,
        image_filename,  # 只保存相对路径
        artist_file,
        artist_prompt,
        prompt_file,
        prompt_text,
        prompt
    )

def main():
    # 定义文件夹路径
    artists_folder = "prompts/aritsts_folder"
    prompts_folder = "prompts/prompts_folder"
    
    # 列出并选择文件
    artists_files = list_csv_files(artists_folder)
    prompts_files = list_csv_files(prompts_folder)
    
    if not artists_files or not prompts_files:
        print("错误：文件夹中没有找到CSV文件")
        return
    
    selected_artist_file = select_file(artists_files, "artists文件夹")
    selected_prompt_file = select_file(prompts_files, "prompts文件夹")
    
    # 读取文件内容
    artists = read_csv_content(os.path.join(artists_folder, selected_artist_file))
    prompts = read_csv_content(os.path.join(prompts_folder, selected_prompt_file))
    
    # 打印读取到的内容数量
    print(f"\n从 {selected_artist_file} 中读取到 {len(artists)} 个艺术家风格")
    print(f"从 {selected_prompt_file} 中读取到 {len(prompts)} 个提示词")
    
    # 计算总组合数
    total_combinations = len(artists) * len(prompts)
    print(f"\n将生成 {total_combinations} 张图片...")
    
    # 创建批次目录
    batch_dir = get_batch_dir()
    print(f"本次生成的文件将保存在: {batch_dir}")
    
    # 初始化数据库
    conn = init_database(batch_dir)
    
    # 使用tqdm创建进度条
    progress_bar = tqdm(total=total_combinations, desc="生成进度")
    
    try:
        # 生成图片并记录信息
        for artist in artists:
            for prompt in prompts:
                combined_prompt = f"{DEFAULT_QUALITY_PROMPT}{artist},{prompt}"
                generate_and_save_with_record(
                    combined_prompt,
                    selected_artist_file,
                    artist,
                    selected_prompt_file,
                    prompt,
                    conn,
                    batch_dir
                )
                # 更新进度条
                progress_bar.update(1)
                # 显示当前正在处理的组合
                progress_bar.set_postfix_str(f"当前: {artist[:20]}... + {prompt[:20]}...")
    except Exception as e:
        print(f"\n生成过程中出现错误: {str(e)}")
    finally:
        # 关闭进度条
        progress_bar.close()
        # 关闭数据库连接
        conn.close()
        print(f"\n所有图片生成完成，信息已保存到数据库: {os.path.join(batch_dir, 'image_generation.db')}")

if __name__ == "__main__":
    main() 