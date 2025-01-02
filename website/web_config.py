"""
批次显示配置文件
"""

# 批次显示配置
# key: 原始批次路径
# value: 字典，包含显示名称(display_name)和自定义URL(url_path)
BATCH_DISPLAY_CONFIG = {
    "batch/20250102-014551": {
        "display_name": "NoobAI-XL V-Pred 1.0 Version 画风对比",
        "url_path": "noobai-xl-vpred-1",
        "enabled": True,  # 是否在首页显示
        "civitai_url": "https://civitai.com/models/833294/noobai-xl-nai-xl",  # Civitai模型链接
        "huggingface_url": "https://huggingface.co/Laxhar/noobai-XL-Vpred-1.0"   # HuggingFace模型链接
    },
    # 可以添加更多批次配置
}

def get_batch_config(batch_path):
    """获取批次的显示配置"""
    return BATCH_DISPLAY_CONFIG.get(batch_path, {
        "display_name": batch_path,
        "url_path": batch_path,
        "enabled": False,
        "civitai_url": "",
        "huggingface_url": ""
    })

def get_enabled_batches():
    """获取所有启用的批次配置"""
    return {k: v for k, v in BATCH_DISPLAY_CONFIG.items() if v.get("enabled", False)} 