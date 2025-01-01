import webuiapi
from config import *

def generate_image(prompt, negative_prompt=DEFAULT_NEGATIVE_PROMPT):
    """
    生成图片并返回
    
    Args:
        prompt (str): 正向提示词
        negative_prompt (str, optional): 负向提示词，默认使用配置文件中的设置
    
    Returns:
        PIL.Image: 生成的图片对象
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
    
    # 返回生成的第一张图片
    return result.images[0]

def generate_images_batch(prompts, negative_prompt=DEFAULT_NEGATIVE_PROMPT):
    """
    批量生成图片
    
    Args:
        prompts (list): 提示词列表
        negative_prompt (str, optional): 负向提示词，默认使用配置文件中的设置
    
    Returns:
        list: 生成的图片对象列表
    """
    return [generate_image(prompt, negative_prompt) for prompt in prompts]

if __name__ == "__main__":
    # 测试示例
    prompt = "very awa,masterpiece,best quality,year 2024,newest,highres,absurdres,chyoel,solar,[kuzuvine],[[dino \(dinoartforame\)]],[[[ciloranko]]],1girl,__arknights_characters__,arknights,solo,"
    image = generate_image(prompt)
    # 测试时可以保存图片
    image.save("test_image.png") 