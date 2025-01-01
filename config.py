# SD WebUI API配置
# API_HOST = '100.71.15.9'
# API_PORT = 7860
API_HOST = '127.0.0.1'
API_PORT = 6006

# 图片生成配置
DEFAULT_STEPS = 20
DEFAULT_CFG_SCALE = 4.5
DEFAULT_WIDTH = 832
DEFAULT_HEIGHT = 1216
DEFAULT_SAMPLER = "Euler"
DEFAULT_NEGATIVE_PROMPT = r"text,watermark,bad anatomy,bad proportions,extra limbs,extra digit,extra legs,extra legs and arms,disfigured,missing arms,too many fingers,fused fingers,missing fingers,unclear eyes,watermark,username,logo,artist logo,patreon logo,weibo logo,arknights logo,"
DEFAULT_QUALITY_PROMPT = r"very awa,masterpiece,best quality,year 2024,newest,highres,absurdres,"

# 图片保存配置
IMAGE_SAVE_FORMAT = "webp"
IMAGE_QUALITY = 90
SAVE_DIR = "generate_images"

# 文件命名配置
DATE_FORMAT = "%Y%m%d"
TIME_FORMAT = "%H%M%S"
FILENAME_TEMPLATE = "image_{timestamp}_{index}.{format}" 