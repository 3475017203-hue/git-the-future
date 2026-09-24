# 🎯 AI英语面试突击队

> 基于中国国际大学生创新大赛获奖项目（AI口语陪练 TalkMate + AI写作助手）灵感实现
>
> **创意类别：** AI+教育 / AI口语陪练 / SaaS平台

---

## ✨ 功能亮点

| 模块 | 功能 | 说明 |
|------|------|------|
| 🤖 **AI模拟面试** | 输入简历+岗位，生成针对性问题 | 支持自我介绍/技术题/行为题 |
| 🎤 **口语陪练** | 场景化英语对话练习 | 面试/商务/日常/演讲 4种场景 |
| 📝 **答案优化** | AI评分+语法改进+参考答案 | 从内容/语法/逻辑多维度反馈 |
| 📊 **面试报告** | 生成综合能力评估报告 | 优势/薄弱点/改进建议 |
| 💬 **即时对话** | 实时英语对话练习 | AI扮演面试官进行追问 |

---

## 🏆 灵感来源

| 获奖项目 | 启发点 |
|---------|--------|
| **口语星球 TalkMate**（北京大学，金奖） | AI口语陪练 + 场景化对话 |
| **笔灵AI写作**（清华大学，金奖） | AI内容优化 + 多场景模板 |

**核心创新：** AI场景化口语陪练 + 智能答案反馈系统

---

## 🚀 快速启动

### 1. 克隆/进入目录

```bash
cd /mnt/d/mycode/ai-interview-commando
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 AI API（推荐 SiliconFlow，免费额度）

**Linux/macOS/WSL:**
```bash
export SILICONFLOW_API_KEY="your_key_here"
```

**Windows PowerShell:**
```powershell
$env:SILICONFLOW_API_KEY = "your_key_here"
```

> 📍 **注册地址：** https://cloud.siliconflow.cn  
> 💰 每月大量免费额度，Qwen2.5-7B 模型完全免费！

### 4. 运行

```bash
python app.py
```

### 5. 打开浏览器

```
http://localhost:5188
```

---

## 📖 使用流程

```
第1步：输入目标岗位 + 简历（如有）
第2步：生成自我介绍建议
第3步：选择面试话题（自我介绍/技术/行为/综合）
第4步：AI生成3个面试问题
第5步：用英语回答问题
第6步：AI即时反馈 + 评分 + 改进建议
第7步：生成完整面试报告
```

---

## 🛠️ 技术架构

```
用户端（浏览器/HTML）
    │
    ▼
Flask 后端（Python）
    │
    ├── 会话管理（SQLite）
    ├── AI对话引擎
    │   └── SiliconFlow API
    │       └── Qwen2.5-7B-Instruct
    └── 面试反馈引擎
        ├── 问题生成
        ├── 答案评分
        └── 报告生成
```

**技术栈：** Python + Flask + SQLite + SiliconFlow API（Qwen2.5）

---

## 📁 项目结构

```
ai-interview-commando/
├── app.py              # 主应用
├── requirements.txt    # 依赖
├── README.md           # 说明文档
├── templates/
│   └── index.html     # 前端页面
├── static/
│   └── style.css      # 样式（可选）
└── data/
    └── interviews.db  # SQLite数据库（自动创建）
```

---

## 🎓 参赛亮点

| 维度 | 描述 |
|------|------|
| **痛点真实** | 大学生英语面试准备缺乏练习环境 |
| **技术创新** | AI场景化陪练 + 多维度反馈系统 |
| **商业模式** | SaaS订阅制 + B端（猎头/培训机构）|
| **市场规模** | 亿级英语学习 + 求职面试市场 |

---

✨ *项目开发：俞 | 2026-08-31 | 基于创新大赛获奖项目研究*
