# 🎨 AI多模态创意工作室

> 基于中国国际大学生创新大赛 AI软件类获奖项目技术方案灵感打造
> 灵感来源：深言科技「新一代智能信息处理平台」垂直领域AI应用

**状态：** ✅ 可运行 | **作者：** 俞 ✨

---

## 🎯 项目简介

一个**多功能AI创意工具箱**，集成文档处理、图片生成、写作助手等10+ AI能力，一站式解决学习、工作、创作中的AI需求。

灵感来源：2023年中国国际大学生创新大赛亚军项目「深言科技」——新一代智能信息处理平台。

---

## ✨ 功能列表

### 📄 文档工具（7个）
| 功能 | 说明 |
|------|------|
| 📝 文档摘要 | 一键生成文章核心摘要 |
| ❓ 文档问答 | 上传文档，AI基于内容回答问题 |
| 🔑 关键词提取 | 自动识别核心关键词 |
| 🏷️ 实体识别 | 识别人物/地点/机构/时间 |
| 🧠 思维导图 | 内容自动生成结构化导图 |
| 📇 闪卡生成 | 学习材料→问答闪卡，高效记忆 |
| 📋 试题生成 | 自动出选择题测试卷 |

### ✍️ 写作工具（4个）
| 功能 | 说明 |
|------|------|
| ✨ 文本润色 | 4种风格改写（专业/简洁/生动/文学）|
| 🌐 AI翻译 | 中→英/日/韩/法/德等10种语言 |
| 📖 创意写作 | 输入主题，AI写故事/小说/诗歌 |
| 📣 营销文案 | 产品描述→高转化率营销文案 |

### 🎨 图片工具（1个）
| 功能 | 说明 |
|------|------|
| 🖼️ 图片生成 | 文字描述→AI生成精美图片 |

### 💼 职场工具（1个）
| 功能 | 说明 |
|------|------|
| 📊 简历分析 | AI评估简历并给出优化建议 |

---

## 🏗️ 技术架构

```
用户操作（Web界面）
        ↓
   Flask Web服务
        ↓
┌───────────────────────┐
│     AI API 层          │
│  SiliconFlow (免费)    │
│  DeepSeek (备选)       │
└───────────────────────┘
        ↓
┌───────────────────────┐
│     工具模块层          │
│  文档处理 / 写作助手    │
│  图片生成 / 实体识别    │
└───────────────────────┘
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /mnt/d/mycode/ai-creative-studio
pip install -r requirements.txt
```

### 2. 配置API密钥（免费！）

**推荐使用硅基流动（SiliconFlow）— 免费额度**

```bash
# Linux / macOS / WSL
export SILICONFLOW_API_KEY=sk-your-key-here

# Windows CMD
set SILICONFLOW_API_KEY=sk-your-key-here

# Windows PowerShell
$env:SILICONFLOW_API_KEY="sk-your-key-here"
```

📌 **获取免费API Key：** https://cloud.siliconflow.cn/register

### 3. 启动服务

```bash
python app.py
```

### 4. 访问使用

打开浏览器访问：**http://localhost:5003**

---

## 📁 项目结构

```
ai-creative-studio/
├── app.py                  # Flask 主应用
├── requirements.txt        # Python 依赖
├── README.md               # 本文件
├── templates/
│   └── index.html          # 单页应用前端
└── static/
    ├── css/
    │   └── style.css       # 界面样式（暗色主题）
    └── js/
        └── app.js          # 前端交互逻辑
```

---

## 🎓 参赛亮点分析

本项目对标中国国际大学生创新大赛获奖项目的设计思路：

| 获奖项目特征 | 本项目实现 |
|-------------|-----------|
| 垂直领域AI应用 | ✅ 文档处理 + 写作 + 图片生成 |
| RAG检索增强 | ✅ 文档问答功能 |
| 完整pipeline | ✅ 解析→处理→生成→展示 |
| SaaS工具化 | ✅ Web界面，即开即用 |
| 多模型支持 | ✅ SiliconFlow + DeepSeek |
| 低门槛可复现 | ✅ 免费API，pip安装即可运行 |

---

## ⚙️ 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `SILICONFLOW_API_KEY` | 推荐 | 硅基流动API（免费）|
| `DEEPSEEK_API_KEY` | 选填 | DeepSeek API |
| `PORT` | 选填 | 服务端口，默认5003 |
| `SECRET_KEY` | 选填 | Flask会话密钥 |

---

## 🛠️ 依赖说明

```
Flask        - Web框架
requests     - HTTP请求
PyYAML       - 配置文件
PyPDF2       - PDF解析
python-docx  - Word解析
```

---

_Made with ❤️ by 俞 ✨_  
_灵感来源：中国国际大学生创新大赛 AI软件类获奖项目_
