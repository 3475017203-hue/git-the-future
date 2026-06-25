# 📚 AI学习伙伴

基于 **中国国际大学生创新大赛** 获奖项目「慧语科技 — AI智能教育领航者」灵感实现的智能学习助手。

## ✨ 功能特性

- **💬 AI智能问答** — 基于大模型的各学科问题解答（数学/物理/化学/英语/编程等）
- **📝 学习笔记管理** — 创建、编辑、分类学习笔记，支持标签管理
- **🍅 番茄钟专注计时** — 内置番茄工作法，统计学习数据
- **📊 学习数据可视化** — 本周学习趋势图表，实时统计

## 🎯 项目灵感

本项目参考了2024年中国国际大学生创新大赛金奖项目「慧语科技 — AI智能教育领航者」（中国地质大学）的教育AI理念，将AI大模型技术应用于学习场景，帮助学生个性化学习。

## 🛠️ 技术栈

- **后端**: Flask (Python Web框架)
- **前端**: 原生 HTML/CSS/JavaScript（无框架依赖）
- **数据库**: SQLite（轻量级，无需配置）
- **AI**: 支持多后端（硅基流动/DeepSeek/OpenAI）

## 📦 安装

```bash
# 1. 进入项目目录
cd ai-learning-companion

# 2. 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 3. 安装依赖
pip install -r requirements.txt
```

## 🚀 运行

```bash
# 设置AI API密钥（可选，推荐使用免费的硅基流动）
export SILICONFLOW_API_KEY="your-api-key"    # Linux/Mac
set SILICONFLOW_API_KEY=your-api-key          # Windows CMD
$env:SILICONFLOW_API_KEY="your-api-key"       # Windows PowerShell

# 启动应用
python app.py
```

然后打开浏览器访问 **http://localhost:5050**

## 🔑 API密钥获取

### 推荐：硅基流动（免费额度）
1. 访问 https://cloud.siliconflow.cn 注册账号
2. 进入控制台 → API Keys → 创建新密钥
3. 复制密钥并设置为环境变量

### 其他选项
- **DeepSeek**: https://platform.deepseek.com/
- **OpenAI**: https://platform.openai.com/

## 📁 项目结构

```
ai-learning-companion/
├── app.py              # Flask 主应用
├── requirements.txt    # 依赖列表
├── README.md           # 说明文档
├── learning_companion.db  # SQLite数据库（自动创建）
├── templates/          # HTML模板
│   ├── index.html     # 主页（AI问答 + 统计）
│   ├── notes.html     # 笔记管理页面
│   └── pomodoro.html  # 番茄钟页面
└── static/
    └── style.css      # 全局样式
```

## 🎨 界面预览

| 页面 | 功能 |
|------|------|
| 首页 | AI问答入口 + 本周学习统计图表 + 最近笔记/问答 |
| 笔记 | 左侧笔记列表 + 右侧编辑器，支持创建/编辑/删除 |
| 番茄钟 | 25分钟专注计时器 + 今日完成统计 |

## 💡 使用技巧

1. **AI问答**: 选择科目后输入问题，AI会结合上下文给出解答
2. **笔记管理**: 为笔记添加科目和标签，方便复习时快速查找
3. **番茄钟**: 选择学习科目后开始计时，完成后自动记录统计
4. **统计图表**: 每周学习数据自动汇总，坚持使用效果更佳

## 🎯 适用场景

- 学生日常学习答疑
- 考前知识点复习整理
- 编程题目解答和代码Debug
- 英语语法和作文辅导
- 番茄工作法学习专注

---

_✨ Made with ❤️ by 俞 (AI学习伙伴 v1.0)_
