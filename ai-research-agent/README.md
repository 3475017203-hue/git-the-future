# 🤖 AI多智能体研究助手

基于中国国际大学生创新大赛获奖项目架构灵感实现的多Agent协作研究平台。

## ✨ 功能亮点

- **🎭 多Agent协作架构** — 协调员+研究员+分析师+写作师+审核师，5个AI角色分工明确
- **🔍 智能搜索** — 自动从多源收集信息，整合去重
- **🧠 深度分析** — 识别趋势、机会与风险，给出洞察
- **📝 报告生成** — 一键生成结构化研究报告
- **📊 多维评分** — 从完整性、准确性、逻辑性、创新性多维度评估报告

## 🏆 灵感来源

本项目受以下获奖项目架构启发：
- **"妙聊" AI多模态社交平台** — 2023年金奖，多Agent协作框架
- **"法信AI" 智能法律咨询平台** — 2024年银奖，RAG检索增强架构

核心创新：**多Agent分工协作 + RAG增强生成**

## 🚀 快速启动

### 1. 安装依赖

```bash
cd /mnt/d/mycode/ai-research-agent
pip install -r requirements.txt
```

### 2. 配置AI API（推荐使用免费额度）

**方案一：硅基流动（推荐）**
```bash
export SILICONFLOW_API_KEY=your_key_here
```

**方案二：DeepSeek**
```bash
export DEEPSEEK_API_KEY=your_key_here
```

**方案三：OpenAI**
```bash
export OPENAI_API_KEY=your_key_here
```

### 3. 运行

```bash
python app.py
```

然后访问：**http://localhost:5080**

## 🤖 Agent团队架构

| Agent | 职责 | 核心能力 |
|-------|------|---------|
| 🎯 协调员 | 任务分配与流程控制 | 统筹调度 |
| 📚 研究员 | 信息检索与收集 | Web搜索 + 内容抓取 |
| 🧠 分析师 | 深度分析与趋势判断 | 洞察识别 + 风险评估 |
| ✍️ 写作师 | 报告撰写与整合 | 结构化输出 |
| ✅ 审核师 | 质量检查与评分 | 多维评估 |

## 🎯 使用流程

1. **输入研究主题** — 例如："人工智能对大学生就业的影响"
2. **启动研究** — 点击"启动多Agent研究"
3. **观看Agent协作** — 实时显示各Agent工作状态
4. **获取报告** — 自动生成完整研究报告
5. **查看评分** — 了解报告质量评分

## 📂 项目结构

```
ai-research-agent/
├── app.py              # 主程序（包含所有Agent逻辑）
├── templates/
│   └── index.html      # Web界面
├── static/             # 静态资源
├── data/               # 数据存储
│   ├── research.db     # SQLite数据库
│   └── research/       # 研究报告存储
├── requirements.txt    # 依赖
└── README.md           # 说明文档
```

## 🔧 技术栈

- **后端**：Python + Flask
- **前端**：原生 HTML/CSS/JS（无框架依赖）
- **Agent框架**：LangChain风格的自定义多Agent实现
- **数据库**：SQLite（内置，无需安装）
- **API调用**：直接使用requests（无需SDK）

## 📌 适用场景

- 学术研究文献综述
- 行业趋势分析报告
- 竞品分析研究
- 市场调研报告
- 任何需要多角度深度研究的任务

---

*Created by 俞 ✨ · 2026-08-31*
*灵感：中国国际大学生创新大赛 AI软件类获奖项目*
