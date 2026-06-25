# AI合同风险审查助手 📋

> 基于中国国际大学生创新大赛获奖项目灵感实现的AI法律助手
> 用AI大模型智能分析合同风险、识别不公平条款、给出通俗易懂的法律建议

## ✨ 功能特点

- 📋 **多类型合同支持**：劳动合同、房屋租赁、商品买卖、服务合同、借贷合同等
- ⚖️ **智能风险识别**：自动识别合同中的高、中、低风险点
- 💡 **通俗易懂**：用简单语言解释法律术语，不用担心看不懂
- ✍️ **修改建议**：提供具体的条款修改建议
- 📊 **风险评级**：给出综合风险等级评估

## 🚀 快速开始

### 1. 安装依赖

```bash
cd ai-contract-reviewer
pip install -r requirements.txt
```

### 2. 配置AI API（推荐使用免费的硅基流动）

```bash
# 方式一：使用硅基流动（免费，推荐）
export SILICONFLOW_API_KEY=your-key-here

# 方式二：使用 DeepSeek
export DEEPSEEK_API_KEY=your-key-here

# 方式三：使用智谱AI
export ZHIPU_API_KEY=your-key-here

# 方式四：使用 OpenAI
export OPENAI_API_KEY=your-key-here
```

> 📌 推荐使用 **硅基流动**，注册即送免费额度，稳定快速
> 官网：https://www.siliconflow.cn

### 3. 启动服务

```bash
python app.py
```

### 4. 访问使用

打开浏览器访问：**http://localhost:5002**

## 📖 使用方法

1. **选择合同类型**：劳动合同/房屋租赁/商品买卖等
2. **输入合同内容**：粘贴文本或上传文件
3. **设置关注点**（可选）：告诉AI你特别担心什么
4. **点击审查**：AI将分析合同并生成报告

## 🎯 适合人群

- 📄 即将入职需要审查劳动合同的求职者
- 🏠 租房需要检查租赁合同条款的租客
- 🛒 网购遇到售后条款争议的消费者
- 🤝 需要审查商务合同的小微企业主
- 📝 对合同法律风险有疑问的任何人

## ⚠️ 免责声明

本工具分析结果仅供参考，不能替代专业法律意见。
如有重大合同或法律问题，建议咨询专业律师。

## 🛠️ 技术栈

- Python 3.8+
- Flask Web框架
- AI大模型（支持 SiliconFlow / DeepSeek / 智谱AI / OpenAI）

## 📁 项目结构

```
ai-contract-reviewer/
├── app.py              # Flask主应用
├── requirements.txt    # 依赖列表
├── README.md          # 说明文档
├── templates/         # HTML模板
│   ├── index.html     # 首页
│   └── result.html    # 结果页
└── static/            # 静态文件（备用）
```

## 🎓 灵感来源

- 第八届中国国际大学生创新大赛金奖项目"AI慧眼——医疗影像智能诊断平台"
- 银奖项目"智能简历优化SaaS平台"
- 核心思路：用AI大模型API快速实现有社会价值的SaaS应用

---

_Made with ❤️ by 俞 ✨_  
_基于中国国际大学生创新大赛获奖项目灵感 | 2026_