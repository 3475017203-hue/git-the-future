#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI路演答辩助手
基于中国国际大学生创新大赛获奖项目分析研发
功能：智能生成答辩PPT、模拟评委提问、方案优化建议、路演话术生成

灵感来源：
- 创新大赛金奖项目"妙聊"、"法信AI"的项目展示技巧
- AI+教育/商业策划赛道获奖作品的技术方案
核心创新：AI + 创新大赛路演备赛细分场景，帮参赛者打磨出能获奖的展示方案

技术亮点：
- 多后端AI支持（硅基流动/DeepSeek/OpenAI）
- 答辩话术智能生成
- 评委高频问题库 + 智能模拟
- 路演PPT大纲自动生成
"""

import os
import sqlite3
import json
import random
from datetime import datetime
from functools import wraps

import requests
from flask import Flask, render_template, request, jsonify, session, g

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'ai-pitch-presenter-secret-2026')
DATABASE = os.path.join(os.path.dirname(__file__), 'pitch_assistant.db')

# ============ AI API 配置 ============
AI_CONFIG = {
    'siliconflow': {
        'enabled': bool(os.environ.get('SILICONFLOW_API_KEY')),
        'api_key': os.environ.get('SILICONFLOW_API_KEY', ''),
        'base_url': 'https://api.siliconflow.cn/v1',
        'model': 'Qwen/Qwen2.5-7B-Instruct',
        'name': '硅基流动（免费）',
    },
    'deepseek': {
        'enabled': bool(os.environ.get('DEEPSEEK_API_KEY')),
        'api_key': os.environ.get('DEEPSEEK_API_KEY', ''),
        'base_url': 'https://api.deepseek.com/v1',
        'model': 'deepseek-chat',
        'name': 'DeepSeek',
    },
    'openai': {
        'enabled': bool(os.environ.get('OPENAI_API_KEY')),
        'api_key': os.environ.get('OPENAI_API_KEY', ''),
        'base_url': 'https://api.openai.com/v1',
        'model': 'gpt-4o-mini',
        'name': 'OpenAI',
    },
}

# ============ 评委高频问题库 ============
JUDGE_QUESTIONS = [
    {
        "category": "项目概述",
        "questions": [
            "用一句话介绍你的项目？",
            "你们项目解决了什么具体问题？",
            "这个需求的真实性和紧迫性在哪里？",
            "目标用户是谁？市场规模有多大？",
        ]
    },
    {
        "category": "技术创新",
        "questions": [
            "你们的技术方案有什么创新点？",
            "相比现有方案，你们的优势是什么？",
            "技术壁垒在哪里？其他团队容易复制吗？",
            "核心算法/模型是如何训练的？数据从哪里来？",
        ]
    },
    {
        "category": "商业模式",
        "questions": [
            "你们怎么赚钱？收入来源是什么？",
            "目标客户是谁？谁会为这个付费？",
            "获客成本和客户终身价值是多少？",
            "未来的盈利预期和成长空间？",
        ]
    },
    {
        "category": "团队与进展",
        "questions": [
            "团队成员有哪些？各自负责什么？",
            "项目目前做到什么阶段了？",
            "有哪些落地成果/试点/用户数据？",
            "如果拿到投资，你们打算怎么用？",
        ]
    },
    {
        "category": "竞争分析",
        "questions": [
            "有哪些竞争对手？你们和他们有什么区别？",
            "如果大厂也做这个，你们怎么办？",
            "你们的护城河是什么？",
        ]
    },
    {
        "category": "社会价值",
        "questions": [
            "这个项目有什么社会价值？",
            "是否符合国家政策导向？",
            "可能有哪些风险和伦理问题？",
        ]
    },
]

# ============ 获奖PPT结构模板 ============
PPT_TEMPLATES = {
    "standard": [
        {"slide": 1, "title": "封面", "content": "项目名称 + Slogan + 团队名称 + 联系方式"},
        {"slide": 2, "title": "痛点问题", "content": "用真实数据和故事说明问题有多严重"},
        {"slide": 3, "title": "解决方案", "content": "一句话说清你们做什么 + 核心创新点"},
        {"slide": 4, "title": "产品介绍", "content": "产品截图/演示视频 + 核心功能"},
        {"slide": 5, "title": "技术架构", "content": "技术方案亮点 + 为什么能做"},
        {"slide": 6, "title": "商业模式", "content": "谁付费 + 怎么收钱 + 财务预测"},
        {"slide": 7, "title": "运营数据", "content": "用户数/收入/试点成果 + 增长趋势"},
        {"slide": 8, "title": "竞争分析", "content": "对比竞争对手，突出差异化优势"},
        {"slide": 9, "title": "团队介绍", "content": "成员背景与项目契合度"},
        {"slide": 10, "title": "未来规划", "content": "下一步目标 + 融资需求"},
    ],
    "compact": [
        {"slide": 1, "title": "封面", "content": "项目名称 + Slogan + 团队"},
        {"slide": 2, "title": "痛点+方案", "content": "问题多严重 + 你们怎么解决"},
        {"slide": 3, "title": "产品+技术", "content": "核心功能 + 技术亮点"},
        {"slide": 4, "title": "商业+数据", "content": "盈利模式 + 运营成果"},
        {"slide": 5, "title": "团队+规划", "content": "成员背景 + 未来目标"},
    ],
}


# ============ 数据库 ============
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """初始化数据库"""
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS project_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            field TEXT,
            target_users TEXT,
            core_problem TEXT,
            solution TEXT,
            tech_stack TEXT,
            business_model TEXT,
            team_info TEXT,
            current_progress TEXT,
            advantages TEXT,
            risks TEXT,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS qa_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT,
            category TEXT,
            project_context TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS pitch_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            pitch_content TEXT,
            ppt_outline TEXT,
            created_at TEXT
        );
    ''')
    db.commit()


# ============ AI 调用 ============
def get_active_ai_backend():
    """获取当前可用的AI后端"""
    for backend, config in AI_CONFIG.items():
        if config['enabled']:
            return backend, config
    return None, None


def call_ai(prompt, system_prompt=None):
    """调用AI生成内容"""
    backend, config = get_active_ai_backend()
    if not backend:
        return None, "未配置任何AI后端，请设置环境变量 SILICONFLOW_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY"

    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": config['model'],
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000,
    }

    try:
        resp = requests.post(
            f"{config['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data['choices'][0]['message']['content'], None
    except Exception as e:
        return None, str(e)


# ============ 核心AI功能 ============
def generate_pitch_script(project_info, duration_minutes=5):
    """生成路演话术"""
    system_prompt = """你是一个创新大赛路演教练，帮助用户生成专业的项目路演话术。
要求：
1. 语言简洁有力，适合口头演讲
2. 突出项目亮点和社会价值
3. 控制时长在指定分钟内
4. 使用"我们"而非"我"
5. 每个部分标注时间分配"""

    prompt = f"""请为以下创新大赛参赛项目生成{duration_minutes}分钟路演话术。

项目信息：
- 项目名称：{project_info.get('name', '未命名项目')}
- 项目领域：{project_info.get('field', '通用')}
- 目标用户：{project_info.get('target_users', '待定')}
- 核心问题：{project_info.get('core_problem', '待定')}
- 解决方案：{project_info.get('solution', '待定')}
- 技术方案：{project_info.get('tech_stack', '待定')}
- 商业模式：{project_info.get('business_model', '待定')}
- 团队信息：{project_info.get('team_info', '待定')}
- 当前进展：{project_info.get('current_progress', '待定')}
- 竞争优势：{project_info.get('advantages', '待定')}

请生成完整的路演话术，包括：
1. 开场吸引（如何让评委眼前一亮）
2. 痛点阐述（为什么这个项目值得做）
3. 解决方案（你们做了什么，怎么做的）
4. 成果展示（有什么数据/试点支撑）
5. 商业模式（怎么赚钱）
6. 团队介绍（为什么你们能做成）
7. 结束语（有力的收尾）

时间分配建议：
- 开场：10%
- 痛点+方案：30%
- 成果+商业：30%
- 团队+展望：30%"""

    return call_ai(prompt, system_prompt)


def generate_ppt_outline(project_info, template_type="standard"):
    """生成PPT大纲"""
    template = PPT_TEMPLATES.get(template_type, PPT_TEMPLATES["standard"])

    system_prompt = """你是一个创新大赛PPT设计专家，帮助用户设计专业的参赛PPT结构。
要求：
1. 每页突出一个核心信息
2. 视觉化表达（能用图表不用文字）
3. 数据说话（用具体数字不用模糊表述）
4. 符合大赛评审逻辑"""

    prompt = f"""请为以下项目生成PPT内容大纲（{len(template)}页）。

项目信息：
- 项目名称：{project_info.get('name', '未命名项目')}
- 项目领域：{project_info.get('field', '通用')}
- 目标用户：{project_info.get('target_users', '待定')}
- 核心问题：{project_info.get('core_problem', '待定')}
- 解决方案：{project_info.get('solution', '待定')}
- 技术方案：{project_info.get('tech_stack', '待定')}
- 商业模式：{project_info.get('business_model', '待定')}
- 团队信息：{project_info.get('team_info', '待定')}
- 当前进展：{project_info.get('current_progress', '待定')}
- 竞争优势：{project_info.get('advantages', '待定')}

PPT模板结构：
{json.dumps(template, ensure_ascii=False, indent=2)}

请为每一页填充：
1. 标题（简洁有力）
2. 核心内容要点（3-5条）
3. 建议使用的视觉元素（图表/图片/数据卡片）
4. 演讲时该页的关键话术（1-2句）

以JSON格式返回。"""

    return call_ai(prompt, system_prompt)


def simulate_judge_qa(project_info, category=None):
    """模拟评委提问"""
    questions = []
    if category:
        for cat in JUDGE_QUESTIONS:
            if cat["category"] == category:
                questions = random.sample(cat["questions"], min(3, len(cat["questions"])))
                break
    else:
        all_qs = []
        for cat in JUDGE_QUESTIONS:
            all_qs.extend([(q, cat["category"]) for q in cat["questions"]])
        selected = random.sample(all_qs, min(5, len(all_qs)))
        questions = selected

    system_prompt = """你是一个创新大赛资深评委，擅长从技术、商业、团队等多维度提问。
要求：
1. 问题尖锐但有建设性
2. 关注项目的可行性和可信度
3. 问题要能让参赛者展现优势
4. 参考真实评委风格"""

    prompt = f"""你是创新大赛评委，请针对以下项目生成专业、有挑战性的提问。

项目信息：
- 项目名称：{project_info.get('name', '未命名项目')}
- 项目领域：{project_info.get('field', '通用')}
- 目标用户：{project_info.get('target_users', '待定')}
- 核心问题：{project_info.get('core_problem', '待定')}
- 解决方案：{project_info.get('solution', '待定')}
- 技术方案：{project_info.get('tech_stack', '待定')}
- 商业模式：{project_info.get('business_model', '待定')}
- 团队信息：{project_info.get('team_info', '待定')}
- 当前进展：{project_info.get('current_progress', '待定')}
- 竞争优势：{project_info.get('advantages', '待定')}
- 潜在风险：{project_info.get('risks', '待定')}

需要生成的问题数量：{len(questions)}个

评委可能问的问题（参考）：
{chr(10).join([f"- {q}" for q in questions])}

请为每个问题生成：
1. 问题本身
2. 提问目的（评委想知道什么）
3. 最佳回答方向（如何应对）

以JSON格式返回数组。"""

    return call_ai(prompt, system_prompt)


def generate_answer(question, project_info):
    """生成问题回答"""
    system_prompt = """你是一个创新大赛路演教练，帮助参赛者回答评委问题。
要求：
1. 回答简洁有力，不超过2分钟
2. 突出项目优势和差异化
3. 用数据说话，不要空泛
4. 展现团队专业性"""

    prompt = f"""请为以下评委问题生成专业回答。

项目信息：
- 项目名称：{project_info.get('name', '未命名项目')}
- 项目领域：{project_info.get('field', '通用')}
- 目标用户：{project_info.get('target_users', '待定')}
- 核心问题：{project_info.get('core_problem', '待定')}
- 解决方案：{project_info.get('solution', '待定')}
- 技术方案：{project_info.get('tech_stack', '待定')}
- 商业模式：{project_info.get('business_model', '待定')}
- 团队信息：{project_info.get('team_info', '待定')}
- 当前进展：{project_info.get('current_progress', '待定')}
- 竞争优势：{project_info.get('advantages', '待定')}

评委问题：{question}

请生成：
1. 回答要点（3-5条）
2. 参考话术（可直接使用）
3. 注意事项（避免的错误）"""

    return call_ai(prompt, system_prompt)


def optimize_project(project_info):
    """优化项目方案"""
    system_prompt = """你是一个创新大赛评审专家和创业导师，帮助优化项目方案使其更具竞争力。
要求：
1. 参考历年获奖项目的成功要素
2. 指出项目的薄弱环节
3. 提供具体可执行的改进建议
4. 强调创新性和商业可行性"""

    prompt = f"""请分析并优化以下创新大赛参赛项目。

项目信息：
- 项目名称：{project_info.get('name', '未命名项目')}
- 项目领域：{project_info.get('field', '通用')}
- 目标用户：{project_info.get('target_users', '待定')}
- 核心问题：{project_info.get('core_problem', '待定')}
- 解决方案：{project_info.get('solution', '待定')}
- 技术方案：{project_info.get('tech_stack', '待定')}
- 商业模式：{project_info.get('business_model', '待定')}
- 团队信息：{project_info.get('team_info', '待定')}
- 当前进展：{project_info.get('current_progress', '待定')}
- 竞争优势：{project_info.get('advantages', '待定')}
- 潜在风险：{project_info.get('risks', '待定')}

请从以下维度分析并给出优化建议：
1. 项目定位（是否清晰、有差异化）
2. 痛点真实性（是否真实需求还是YY）
3. 技术壁垒（是否足够难以复制）
4. 商业模式（是否有人愿意付费）
5. 社会价值（是否符合大赛导向）
6. 团队展示（是否展现了核心竞争力）
7. 整体打分（10分制）和改进空间"""

    return call_ai(prompt, system_prompt)


# ============ 路由 ============
@app.route('/')
def index():
    init_db()
    return render_template('index.html')


@app.route('/api/ai-status')
def ai_status():
    """检查AI后端状态"""
    backends = []
    for name, config in AI_CONFIG.items():
        backends.append({
            'name': name,
            'display_name': config['name'],
            'enabled': config['enabled'],
        })
    return jsonify({'backends': backends})


@app.route('/api/save-project', methods=['POST'])
def save_project():
    """保存项目信息"""
    data = request.json
    db = get_db()

    now = datetime.now().isoformat()
    db.execute('''
        INSERT INTO project_info
        (name, field, target_users, core_problem, solution, tech_stack,
         business_model, team_info, current_progress, advantages, risks, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('name', ''),
        data.get('field', ''),
        data.get('target_users', ''),
        data.get('core_problem', ''),
        data.get('solution', ''),
        data.get('tech_stack', ''),
        data.get('business_model', ''),
        data.get('team_info', ''),
        data.get('current_progress', ''),
        data.get('advantages', ''),
        data.get('risks', ''),
        now, now,
    ))
    db.commit()
    return jsonify({'success': True, 'message': '项目信息已保存'})


@app.route('/api/load-project/<int:project_id>')
def load_project(project_id):
    """加载项目信息"""
    db = get_db()
    row = db.execute('SELECT * FROM project_info WHERE id = ?', (project_id,)).fetchone()
    if row:
        return jsonify({k: row[k] for k in row.keys()})
    return jsonify({'error': '项目不存在'}), 404


@app.route('/api/generate-pitch', methods=['POST'])
def api_generate_pitch():
    """生成路演话术"""
    project_info = request.json
    duration = project_info.pop('duration', 5)
    content, error = generate_pitch_script(project_info, duration)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'content': content})


@app.route('/api/generate-ppt', methods=['POST'])
def api_generate_ppt():
    """生成PPT大纲"""
    project_info = request.json
    template_type = project_info.pop('template_type', 'standard')
    content, error = generate_ppt_outline(project_info, template_type)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'content': content})


@app.route('/api/simulate-qa', methods=['POST'])
def api_simulate_qa():
    """模拟评委提问"""
    data = request.json
    project_info = data.get('project_info', {})
    category = data.get('category')
    content, error = simulate_judge_qa(project_info, category)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'content': content})


@app.route('/api/answer-question', methods=['POST'])
def api_answer_question():
    """生成问题回答"""
    data = request.json
    project_info = data.get('project_info', {})
    question = data.get('question', '')
    content, error = generate_answer(question, project_info)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'content': content})


@app.route('/api/optimize-project', methods=['POST'])
def api_optimize_project():
    """优化项目方案"""
    project_info = request.json
    content, error = optimize_project(project_info)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'content': content})


@app.route('/api/judge-questions')
def api_judge_questions():
    """获取评委问题库"""
    return jsonify({'categories': JUDGE_QUESTIONS})


# ============ 启动 ============
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5010))
    app.run(host='0.0.0.0', port=port, debug=True)
