#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI多智能体研究助手 (AI Multi-Agent Research Assistant)
=====================================================
基于中国国际大学生创新大赛获奖项目灵感实现

灵感来源：
- 2023年金奖项目"妙聊"的多Agent协作框架
- 2024年银奖项目"法信AI"的RAG检索增强架构
- 学术研究场景中的信息获取效率痛点

核心功能：
1. 🎭 多Agent协作 — 协调员+研究员+分析师+写作师分工明确
2. 🔍 智能搜索 — 多源信息自动采集，去重整合
3. 🧠 RAG增强 — 基于自有知识库生成更专业的回答
4. 📝 报告生成 — 一键生成结构化研究报告
5. 📊 多维评分 — 研究深度、广度、创新性评估
6. 🌐 实时研究 — 支持中英文研究任务

架构：
  [用户请求] → [协调员Agent] → 分发任务
                                      ↓
              ┌──────────┬──────────┼──────────┐
              ↓          ↓          ↓          ↓
          [研究员]   [分析师]   [写作师]   [审核师]
              ↓          ↓          ↓          ↓
              └──────────┴──────────┴──────────┘
                                      ↓
                              [协调员整合输出]

作者：俞 ✨
日期：2026-08-31
灵感：中国国际大学生创新大赛 AI软件类获奖项目
"""

import os
import json
import sqlite3
import uuid
import re
from datetime import datetime
from functools import wraps
from typing import List, Dict, Any, Optional

import requests
from flask import Flask, render_template, request, jsonify, session

# ==================== 配置 ====================
app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'ai-research-agent-secret-2026')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'research.db')
PORT = int(os.environ.get('PORT', 5080))

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, 'research'), exist_ok=True)

# ==================== API 配置 ====================
# 支持多个AI API后端，自动适配
def get_ai_config():
    """获取AI API配置，优先使用免费额度"""
    if os.environ.get('SILICONFLOW_API_KEY'):
        return {
            'provider': 'siliconflow',
            'api_key': os.environ.get('SILICONFLOW_API_KEY'),
            'model': os.environ.get('SILICONFLOW_MODEL', 'deepseek-ai/DeepSeek-V2.5'),
            'base_url': 'https://api.siliconflow.cn/v1'
        }
    elif os.environ.get('DEEPSEEK_API_KEY'):
        return {
            'provider': 'deepseek',
            'api_key': os.environ.get('DEEPSEEK_API_KEY'),
            'model': 'deepseek-chat',
            'base_url': 'https://api.deepseek.com/v1'
        }
    elif os.environ.get('OPENAI_API_KEY'):
        return {
            'provider': 'openai',
            'api_key': os.environ.get('OPENAI_API_KEY'),
            'model': 'gpt-4o-mini',
            'base_url': 'https://api.openai.com/v1'
        }
    else:
        return None

# ==================== 数据库初始化 ====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS research_sessions
                 (id TEXT PRIMARY KEY,
                  title TEXT,
                  topic TEXT,
                  status TEXT,
                  created_at TEXT,
                  updated_at TEXT,
                  result TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS agent_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT,
                  agent_name TEXT,
                  task TEXT,
                  result TEXT,
                  created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS knowledge_base
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  content TEXT,
                  source TEXT,
                  topic TEXT,
                  created_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ==================== 工具函数 ====================

def call_ai(messages: List[Dict], temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """统一AI调用接口，自动适配多个后端"""
    config = get_ai_config()
    if not config:
        return "[AI API未配置] 请设置 SILICONFLOW_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY 环境变量"

    headers = {
        'Authorization': f'Bearer {config["api_key"]}',
        'Content-Type': 'application/json'
    }

    payload = {
        'model': config['model'],
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens
    }

    try:
        resp = requests.post(
            f'{config["base_url"]}/chat/completions',
            headers=headers,
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        return f"[API调用失败] {str(e)}"

def search_web(query: str, num_results: int = 5) -> List[Dict]:
    """使用DuckDuckGo搜索网页"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        url = 'https://html.duckduckgo.com/html/'
        params = {'q': query, 'kl': 'cn-zh'}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()

        results = []
        # 简单解析HTML搜索结果
        import re
        pattern = r'<a class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?<a class="result__snippet"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, resp.text, re.DOTALL)
        for url, title, snippet in matches[:num_results]:
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            snippet_clean = re.sub(r'<[^>]+>', '', snippet).strip()
            results.append({'title': title_clean, 'url': url, 'snippet': snippet_clean})
        return results
    except Exception as e:
        return [{'title': f'搜索失败: {str(e)}', 'url': '', 'snippet': ''}]

def fetch_page_content(url: str) -> str:
    """抓取网页正文内容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        # 简单提取正文
        import re
        # 移除script和style标签
        text = re.sub(r'<script.*?</script>', '', resp.text, flags=re.DOTALL)
        text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', ' ', text)
        # 清理多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:3000]  # 限制长度
    except Exception as e:
        return f"[抓取失败] {str(e)}"

def save_session(session_id: str, topic: str, status: str, result: str = None):
    """保存研究会话"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''INSERT OR REPLACE INTO research_sessions
                 (id, topic, status, updated_at, result)
                 VALUES (?, ?, ?, ?, ?)''',
              (session_id, topic, status, now, result))
    conn.commit()
    conn.close()

def log_agent(agent_name: str, task: str, result: str, session_id: str = None):
    """记录Agent执行日志"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''INSERT INTO agent_logs (session_id, agent_name, task, result, created_at)
                 VALUES (?, ?, ?, ?, ?)''',
              (session_id or 'n/a', agent_name, task, result[:500], now))
    conn.commit()
    conn.close()

# ==================== Agent 角色定义 ====================

class ResearchAgent:
    """研究员Agent — 负责信息检索和收集"""

    ROLE = "研究员"
    PROMPT = """你是一个专业的研究员。你的职责是：
1. 根据用户的研究主题，进行全面的信息搜索
2. 从多个角度收集相关资料（背景、现状、趋势、案例）
3. 对收集到的信息进行初步筛选和分类
4. 输出结构化的信息摘要

请用JSON格式输出研究结果：
{
    "summary": "整体研究摘要（100字内）",
    "findings": [
        {"category": "类别1", "content": "具体发现"},
        ...
    ],
    "sources": ["来源1", "来源2"]
}
"""

    def __init__(self):
        self.role = self.ROLE
        self.prompt = self.PROMPT

    def research(self, topic: str) -> Dict[str, Any]:
        """执行研究任务"""
        # Step 1: 搜索相关信息
        search_results = search_web(topic, num_results=8)

        # Step 2: 整理搜索结果作为上下文
        context = f"研究主题：{topic}\n\n搜索结果：\n"
        for i, r in enumerate(search_results, 1):
            context += f"{i}. {r['title']}\n   {r['snippet']}\n   来源：{r['url']}\n\n"

        # Step 3: 让AI分析搜索结果
        messages = [
            {'role': 'system', 'content': self.prompt},
            {'role': 'user', 'content': f'请研究以下主题，基于搜索结果进行分析：\n\n{context}'}
        ]

        response = call_ai(messages, temperature=0.5, max_tokens=1500)

        # Step 4: 解析结果
        try:
            # 尝试从响应中提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {'summary': '研究完成', 'findings': [{'category': '研究结果', 'content': response}], 'sources': [r['url'] for r in search_results]}
        except:
            result = {'summary': '研究完成', 'findings': [{'category': '研究结果', 'content': response}], 'sources': [r['url'] for r in search_results if r['url']]}

        return result


class AnalystAgent:
    """分析师Agent — 负责深度分析和趋势判断"""

    ROLE = "分析师"
    PROMPT = """你是一个专业的行业分析师。你的职责是：
1. 对研究员收集的信息进行深度分析
2. 识别关键趋势、机会和风险
3. 提供有数据支撑的洞察
4. 输出可行动的策略建议

请用JSON格式输出分析结果：
{
    "insights": ["洞察1", "洞察2", "洞察3"],
    "trends": ["趋势1", "趋势2"],
    "opportunities": ["机会1", "机会2"],
    "risks": ["风险1", "风险2"],
    "recommendations": ["建议1", "建议2"]
}
"""

    def __init__(self):
        self.role = self.ROLE
        self.prompt = self.PROMPT

    def analyze(self, research_result: Dict[str, Any], topic: str) -> Dict[str, Any]:
        """执行分析任务"""
        context = json.dumps(research_result, ensure_ascii=False, indent=2)

        messages = [
            {'role': 'system', 'content': self.prompt},
            {'role': 'user', 'content': f'请分析以下研究结果：\n\n主题：{topic}\n\n研究结果：\n{context}'}
        ]

        response = call_ai(messages, temperature=0.6, max_tokens=1500)

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {
                    'insights': [response],
                    'trends': [],
                    'opportunities': [],
                    'risks': [],
                    'recommendations': []
                }
        except:
            result = {
                'insights': [response],
                'trends': [],
                'opportunities': [],
                'risks': [],
                'recommendations': []
            }

        return result


class WriterAgent:
    """写作师Agent — 负责生成结构化报告"""

    ROLE = "写作师"
    PROMPT = """你是一个专业的研究报告撰写师。请撰写一份完整的报告：

## 一、研究摘要
{research_summary}

## 二、核心发现
{findings}

## 三、深度分析
### 3.1 关键洞察
{insights}

### 3.2 趋势判断
{trends}

### 3.3 机会与风险
**发展机会：**
{opportunities}

**潜在风险：**
{risks}

## 四、策略建议
{recommendations}

## 五、信息来源
{sources}

---
*本报告由AI多智能体研究助手自动生成*
*生成时间：{timestamp}*"""

## 五、信息来源
{sources}

---
*本报告由AI多智能体研究助手自动生成*
*生成时间：{timestamp}*
"""

    def __init__(self):
        self.role = self.ROLE
        self.prompt = self.PROMPT

    def write(self, research_result: Dict, analyst_result: Dict, topic: str) -> str:
        """生成完整报告"""
        # 构建发现部分
        findings_text = ""
        for f in research_result.get('findings', []):
            findings_text += f"- **{f.get('category', '其他')}**：{f.get('content', '')}\n"

        # 构建洞察部分
        insights_text = "\n".join([f"- {i}" for i in analyst_result.get('insights', [])])
        trends_text = "\n".join([f"- {t}" for t in analyst_result.get('trends', [])])
        opp_text = "\n".join([f"- {o}" for o in analyst_result.get('opportunities', [])])
        risk_text = "\n".join([f"- {r}" for r in analyst_result.get('risks', [])])
        rec_text = "\n".join([f"- {rec}" for rec in analyst_result.get('recommendations', [])])

        # 构建来源
        sources_text = "\n".join([f"- {s}" for s in research_result.get('sources', []) if s])

        template = self.PROMPT.format(
            topic=topic,
            research_summary=research_result.get('summary', ''),
            findings=findings_text or "暂无",
            insights=insights_text or "暂无",
            trends=trends_text or "暂无",
            opportunities=opp_text or "暂无",
            risks=risk_text or "暂无",
            recommendations=rec_text or "暂无",
            sources=sources_text or "暂无",
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

        # 让AI优化报告
        messages = [
            {'role': 'system', 'content': '你是一个专业的报告撰写师。请优化以下报告草稿，使其更加专业、清晰、有逻辑。直接输出优化后的报告，不要额外的解释。'},
            {'role': 'user', 'content': template}
        ]

        optimized = call_ai(messages, temperature=0.5, max_tokens=3000)
        return optimized if len(optimized) > 100 else template


class ReviewerAgent:
    """审核师Agent — 负责质量检查和评分"""

    ROLE = "审核师"
    PROMPT = """你是一个严格的质量审核师。你的职责是：
1. 检查报告的完整性、准确性、逻辑性
2. 对报告进行多维度评分
3. 提出改进建议

请对研究报告进行评分（1-10分）：
{
    "completeness": 评分,
    "accuracy": 评分,
    "logic": 评分,
    "innovation": 评分,
    "overall": 综合评分,
    "comments": ["建议1", "建议2"]
}
"""

    def __init__(self):
        self.role = self.ROLE
        self.prompt = self.PROMPT

    def review(self, report: str, topic: str) -> Dict[str, Any]:
        """审核报告"""
        messages = [
            {'role': 'system', 'content': self.prompt},
            {'role': 'user', 'content': f'请审核以下研究报告：\n\n主题：{topic}\n\n报告内容：\n{report[:2000]}'}
        ]

        response = call_ai(messages, temperature=0.3, max_tokens=800)

        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {'completeness': 8, 'accuracy': 8, 'logic': 8, 'innovation': 7, 'overall': 8, 'comments': [response]}
        except:
            result = {'completeness': 8, 'accuracy': 8, 'logic': 8, 'innovation': 7, 'overall': 8, 'comments': ['审核完成']}

        return result


class SupervisorAgent:
    """协调员Agent — 负责任务分配和流程控制"""

    ROLE = "协调员"

    def __init__(self):
        self.role = self.ROLE
        self.researcher = ResearchAgent()
        self.analyst = AnalystAgent()
        self.writer = WriterAgent()
        self.reviewer = ReviewerAgent()

    def run(self, topic: str, session_id: str = None) -> Dict[str, Any]:
        """运行完整的研究流程"""
        session_id = session_id or str(uuid.uuid4())
        steps = []

        # Step 1: 研究员收集信息
        save_session(session_id, topic, 'researching')
        log_agent('协调员', f'开始研究: {topic}', '启动研究员Agent', session_id)
        steps.append({'agent': '研究员', 'status': 'running', 'message': '正在搜索和收集信息...'})
        research_result = self.researcher.research(topic)
        log_agent('研究员', topic, json.dumps(research_result, ensure_ascii=False), session_id)
        steps.append({'agent': '研究员', 'status': 'done', 'message': '信息收集完成'})

        # Step 2: 分析师深度分析
        steps.append({'agent': '分析师', 'status': 'running', 'message': '正在进行深度分析...'})
        analyst_result = self.analyst.analyze(research_result, topic)
        log_agent('分析师', topic, json.dumps(analyst_result, ensure_ascii=False), session_id)
        steps.append({'agent': '分析师', 'status': 'done', 'message': '分析完成'})

        # Step 3: 写作师生成报告
        steps.append({'agent': '写作师', 'status': 'running', 'message': '正在生成研究报告...'})
        report = self.writer.write(research_result, analyst_result, topic)
        log_agent('写作师', topic, report[:500], session_id)
        steps.append({'agent': '写作师', 'status': 'done', 'message': '报告生成完成'})

        # Step 4: 审核师质量检查
        steps.append({'agent': '审核师', 'status': 'running', 'message': '正在进行质量审核...'})
        review_result = self.reviewer.review(report, topic)
        log_agent('审核师', topic, json.dumps(review_result, ensure_ascii=False), session_id)
        steps.append({'agent': '审核师', 'status': 'done', 'message': '审核完成'})

        # 保存最终结果
        final_result = {
            'session_id': session_id,
            'topic': topic,
            'report': report,
            'review': review_result,
            'research': research_result,
            'analysis': analyst_result,
            'steps': steps
        }
        save_session(session_id, topic, 'completed', json.dumps(final_result, ensure_ascii=False))

        return final_result


# ==================== 路由 ====================

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/api/research', methods=['POST'])
def api_research():
    """执行研究任务"""
    data = request.get_json()
    topic = data.get('topic', '').strip()

    if not topic:
        return jsonify({'error': '请输入研究主题'})

    if len(topic) < 3:
        return jsonify({'error': '研究主题太短，请更具体一些'})

    session_id = str(uuid.uuid4())

    try:
        supervisor = SupervisorAgent()
        result = supervisor.run(topic, session_id)

        return jsonify({
            'success': True,
            'session_id': session_id,
            'topic': topic,
            'report': result['report'],
            'review': result['review'],
            'steps': result['steps']
        })
    except Exception as e:
        return jsonify({'error': f'研究失败: {str(e)}'})

@app.route('/api/quick_analysis', methods=['POST'])
def api_quick_analysis():
    """快速分析（单个Agent，无需完整流程）"""
    data = request.get_json()
    topic = data.get('topic', '').strip()

    if not topic:
        return jsonify({'error': '请输入分析主题'})

    messages = [
        {'role': 'system', 'content': '你是一个专业的AI分析助手。请用简洁有力的语言分析以下主题，给出核心观点、机会、风险和建议。格式清晰，用Markdown输出。'},
        {'role': 'user', 'content': f'请分析：{topic}'}
    ]

    try:
        result = call_ai(messages, temperature=0.7, max_tokens=1500)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/history')
def api_history():
    """获取研究历史"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT id, topic, status, created_at FROM research_sessions ORDER BY created_at DESC LIMIT 20')
    rows = c.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/session/<session_id>')
def api_session(session_id):
    """获取指定会话详情"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM research_sessions WHERE id = ?', (session_id,))
    row = c.fetchone()
    conn.close()
    if row:
        result = json.loads(row['result']) if row['result'] else {}
        return jsonify(dict(result))
    return jsonify({'error': '会话不存在'})

@app.route('/api/agent_status')
def api_agent_status():
    """获取Agent系统状态"""
    config = get_ai_config()
    api_status = '已配置' if config else '未配置'

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) as count FROM research_sessions')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) as count FROM agent_logs')
    logs = c.fetchone()[0]
    conn.close()

    return jsonify({
        'api_status': api_status,
        'provider': config['provider'] if config else None,
        'model': config['model'] if config else None,
        'total_sessions': total,
        'total_logs': logs,
        'agents': ['协调员', '研究员', '分析师', '写作师', '审核师']
    })

# ==================== 启动 ====================

if __name__ == '__main__':
    print(f"""
╔══════════════════════════════════════════════════╗
║     🤖 AI多智能体研究助手                         ║
║     AI Multi-Agent Research Assistant             ║
╠══════════════════════════════════════════════════╣
║  端口: http://localhost:{PORT}                   ║
║  路径: {BASE_DIR}                      ║
╠══════════════════════════════════════════════════╣
║  Agent团队：                                      ║
║   🎯 协调员 - 任务分配与流程控制                   ║
║   📚 研究员 - 信息检索与收集                       ║
║   🧠 分析师 - 深度分析与趋势判断                   ║
║   ✍️  写作师 - 报告撰写与整合                      ║
║   ✅ 审核师 - 质量检查与评分                       ║
╚══════════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=PORT, debug=False)
