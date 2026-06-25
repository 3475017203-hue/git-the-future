# AI知识问答助手 (RAG Q&A System)

> 基于检索增强生成（RAG）技术的智能知识库问答系统  
> 灵感来源：中国国际大学生创新大赛 AI软件类获奖项目技术方案

## 🎯 项目简介

一个基于 RAG（Retrieval-Augmented Generation）技术的知识库问答系统，用户可上传文档，AI根据文档内容回答问题，并标注答案来源。

**解决的问题：** 面对大量文档/资料时，快速找到答案并知道出处

**应用场景：** 
- 企业内部知识库问答
- 学习资料整理与答疑
- 文档快速检索与理解
- 团队知识沉淀与共享

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 📄 文档上传 | 支持 PDF、Word (.docx)、TXT、Markdown |
| 🔍 智能分块 | 自动将文档分割成语义完整的chunk |
| 💬 问答交互 | 基于文档内容进行RAG问答 |
| 📚 溯源引用 | 答案标注来源文档和页码 |
| 📊 文档管理 | 查看已上传文档列表和状态 |
| 🧠 多模态对话 | 支持多轮上下文对话 |

## 🏗️ 技术架构

```
用户上传文档
    ↓
文档解析 (PyPDF2 / python-docx)
    ↓
文本分块 (RecursiveCharacterTextSplitter)
    ↓
向量化 (SiliconFlow免费Embedding API)
    ↓
向量存储 (FAISS 相似度检索)
    ↓
用户提问
    ↓
检索相关Chunk → 构建Prompt → LLM生成答案
    ↓
返回答案 + 来源引用
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd ai-knowledge-qa
pip install -r requirements.txt
```

### 2. 配置API密钥（免费额度）

```bash
# 复制环境变量模板
cp env.template .env

# 编辑 .env，填入API密钥（推荐使用硅基流动，免费）
# 访问 https://cloud.siliconflow.cn 注册获取API Key
```

### 3. 启动应用

```bash
python app.py
```

### 4. 访问使用

打开浏览器访问：**http://localhost:5002**

## 📁 项目结构

```
ai-knowledge-qa/
├── app.py              # 主应用
├── requirements.txt    # 依赖
├── env.template        # 环境变量模板
├── README.md           # 本文件
├── templates/          # HTML模板
│   └── index.html      # 主页面
├── static/             # 静态资源
└── data/               # 数据存储
    ├── docs/           # 上传的文档
    └── vectorstore/    # 向量数据库
```

## 🛠️ 技术栈

| 层级 | 技术选型 |
|------|----------|
| Web框架 | Flask |
| 文档解析 | PyPDF2, python-docx |
| 向量数据库 | FAISS |
| Embedding | SiliconFlow API (免费) / OpenAI |
| LLM | SiliconFlow / DeepSeek / OpenAI |
| 前端 | HTML + JavaScript (无框架) |

## 💡 创新点（参赛亮点）

1. **垂直领域RAG应用** - 非通用问答，而是针对"文档知识库"场景优化
2. **完整RAG pipeline** - 文档解析→分块→向量化→检索→生成，流程完整
3. **溯源能力** - 答案直接标注来源，提升可信度
4. **低门槛可复现** - 使用免费API，学生团队可独立完成

## 📝 使用说明

### 上传文档
1. 点击"上传文档"按钮
2. 选择 PDF、Word、TXT 或 Markdown 文件
3. 等待解析完成（显示进度）
4. 文档自动加入知识库

### 提问
1. 在对话框输入问题
2. 点击发送或按 Enter
3. AI 基于已上传文档回答问题
4. 可追问获取更详细信息

## ⚙️ 环境变量说明

| 变量 | 必填 | 说明 |
|------|------|------|
| `SILICONFLOW_API_KEY` | 选填 | 硅基流动API密钥（免费）|
| `OPENAI_API_KEY` | 选填 | OpenAI API密钥 |
| `DEEPSEEK_API_KEY` | 选填 | DeepSeek API密钥 |
| `FLASK_SECRET_KEY` | 选填 | Flask会话密钥 |
| `PORT` | 选填 | 服务端口，默认5002 |

**优先级：** SiliconFlow > DeepSeek > OpenAI（按免费程度和使用难度综合推荐）

---

_Made with ❤️ by 俞 ✨  
基于中国国际大学生创新大赛获奖项目技术方案灵感_