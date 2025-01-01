import webuiapi
import os
from datetime import datetime
from PIL import Image
import io
from config import *

def ensure_directory(path):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(path):
        os.makedirs(path)

def generate_and_save_image(prompt, save_dir=None, negative_prompt=DEFAULT_NEGATIVE_PROMPT):
    """
    生成图片并保存
    
    Args:
        prompt (str): 正向提示词
        save_dir (str, optional): 保存目录，如果不指定则使用默认目录
        negative_prompt (str, optional): 负向提示词，默认使用配置文件中的设置
    """
    # 初始化API
    api = webuiapi.WebUIApi(host=API_HOST, port=API_PORT)
    
    # 生成图片
    result = api.txt2img(
        prompt=prompt,
        negative_prompt=negative_prompt,
        seed=-1,  # -1表示随机种子
        steps=DEFAULT_STEPS,
        cfg_scale=DEFAULT_CFG_SCALE,
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
        sampler_name=DEFAULT_SAMPLER
    )
    
    # 确定保存目录
    if save_dir is None:
        current_date = datetime.now().strftime(DATE_FORMAT)
        save_dir = os.path.join(SAVE_DIR, current_date)
    
    ensure_directory(save_dir)
    
    # 保存图片
    for i, image in enumerate(result.images):
        # 生成文件名
        timestamp = datetime.now().strftime(TIME_FORMAT)
        filename = FILENAME_TEMPLATE.format(
            timestamp=timestamp,
            index=i,
            format=IMAGE_SAVE_FORMAT
        )
        save_path = os.path.join(save_dir, filename)
        
        # 保存图片
        image.save(save_path, format=IMAGE_SAVE_FORMAT, quality=IMAGE_QUALITY)
        print(f"图片已保存到: {save_path}")
        
        # 返回保存的文件名，用于数据库记录
        return filename

def generate_images_batch(prompts, save_dir=None, negative_prompt=DEFAULT_NEGATIVE_PROMPT):
    """
    批量生成图片
    
    Args:
        prompts (list): 提示词列表
        save_dir (str, optional): 保存目录，如果不指定则使用默认目录
        negative_prompt (str, optional): 负向提示词，默认使用配置文件中的设置
    """
    for prompt in prompts:
        generate_and_save_image(prompt, save_dir, negative_prompt)

if __name__ == "__main__":
    # 测试示例
    prompt = "very awa,masterpiece,best quality,year 2024,newest,highres,absurdres,chyoel,solar,[kuzuvine],[[dino \(dinoartforame\)]],[[[ciloranko]]],1girl,__arknights_characters__,arknights,solo,"
    generate_and_save_image(prompt) 