import webuiapi
import logging
from config import *

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def generate_image(prompt, negative_prompt=DEFAULT_NEGATIVE_PROMPT):
    """
    生成图片并返回
    
    Args:
        prompt (str): 正向提示词
        negative_prompt (str, optional): 负向提示词，默认使用配置文件中的设置
    
    Returns:
        PIL.Image: 生成的图片对象
    """
    logger.info(f"开始生成图片，API地址: {API_HOST}:{API_PORT}")
    logger.info(f"使用提示词: {prompt}")
    logger.info(f"使用反向提示词: {negative_prompt}")
    
    try:
        # 初始化API
        logger.info("正在初始化API连接...")
        api = webuiapi.WebUIApi(host=API_HOST, port=API_PORT)
        
        # 生成图片
        logger.info(f"开始生成图片，参数: steps={DEFAULT_STEPS}, cfg_scale={DEFAULT_CFG_SCALE}, "
                   f"size={DEFAULT_WIDTH}x{DEFAULT_HEIGHT}, sampler={DEFAULT_SAMPLER}")
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
        logger.info("图片生成成功")
        
        # 返回生成的第一张图片
        return result.images[0]
    except Exception as e:
        logger.error(f"生成图片时发生错误: {str(e)}", exc_info=True)
        raise

def generate_images_batch(prompts, negative_prompt=DEFAULT_NEGATIVE_PROMPT):
    """
    批量生成图片
    
    Args:
        prompts (list): 提示词列表
        negative_prompt (str, optional): 负向提示词，默认使用配置文件中的设置
    
    Returns:
        list: 生成的图片对象列表
    """
    logger.info(f"开始批量生成图片，共 {len(prompts)} 张")
    results = []
    for i, prompt in enumerate(prompts, 1):
        logger.info(f"正在生成第 {i}/{len(prompts)} 张图片")
        try:
            image = generate_image(prompt, negative_prompt)
            results.append(image)
        except Exception as e:
            logger.error(f"生成第 {i} 张图片时失败: {str(e)}")
            raise
    logger.info("批量生成完成")
    return results

if __name__ == "__main__":
    # 测试示例
    prompt = "very awa,masterpiece,best quality,year 2024,newest,highres,absurdres,chyoel,solar,[kuzuvine],[[dino \(dinoartforame\)]],[[[ciloranko]]],1girl,__arknights_characters__,arknights,solo,"
    logger.info("开始运行测试")
    image = generate_image(prompt)
    # 测试时可以保存图片
    image.save("test_image.png")
    logger.info("测试完成，图片已保存为 test_image.png") 