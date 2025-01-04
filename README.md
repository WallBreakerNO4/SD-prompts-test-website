# NoobAI-XL 画风对比项目

这是一个用于展示和对比 NoobAI-XL 模型不同画风生成效果的项目。项目分为图片生成和网站展示两个主要部分。

## 项目结构

```
.
├── website/                # 网站展示部分
│   ├── static/            # 静态资源
│   │   ├── css/          # 样式文件
│   │   ├── js/           # JavaScript文件
│   │   ├── img/          # 图片资源
│   │   └── favicon/      # 网站图标
│   ├── templates/        # HTML模板
│   ├── app.py           # Flask应用主程序
│   └── web_config.py    # 网站配置文件
└── generate_images/      # 图片生成部分（由.gitignore排除）
    └── batch/           # 批次图片存储目录
```

## 一、图片生成部分

### 功能特点

- 支持批量生成图片
- 使用 SQLite 数据库记录生成信息
- 按批次组织和管理生成的图片
- 支持多种画风和提示词组合

### 数据组织

- 每个批次都有独立的目录和数据库
- 图片按照画风和提示词矩阵式组织
- 支持记录模型来源（Civitai、HuggingFace）

## 二、网站展示部分

### 功能特点

1. **首页功能**
   - 展示所有可用的批次列表
   - 提供模型链接（Civitai、HuggingFace）
   - 简洁的卡片式布局

2. **批次展示页**
   - 矩阵式布局展示图片
   - 支持图片放大预览
   - 行号导航功能
   - 响应式设计，适配多种设备

3. **性能优化**
   - 图片懒加载
   - 智能预加载
   - 浏览器缓存优化
   - 支持大规模图片展示

### 技术栈

- 后端：Python Flask
- 前端：HTML5 + CSS3 + JavaScript
- UI框架：Bootstrap 5
- 数据存储：SQLite

## 部署说明

1. 安装依赖：
```bash
cd website
pip install -r requirements.txt
```

2. 配置批次：
   - 在 `web_config.py` 中配置要显示的批次
   - 设置批次的显示名称和URL路径
   - 配置模型链接（可选）

3. 启动服务：
```bash
python app.py
```

## 注意事项

- 生成的图片需要放在 `website/static/generate_images/batch/` 目录下
- 每个批次需要有对应的 SQLite 数据库文件
- 确保服务器有足够的存储空间和内存
- 建议使用反向代理（如Nginx）进行部署 