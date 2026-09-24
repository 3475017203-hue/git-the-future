#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI创新路演助手 (AI Pitch Architect)
基于中国国际大学生创新大赛获奖项目灵感实现

帮助大学生快速生成创新大赛路演PPT脚本和演讲稿
"""

import os
import io
import re
import json
import sqlite3
import hashlib
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

# =====================================================================
# Flask App Setup
# =====================================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ai-pitch-architect-2026'
app.config['UPLOAD_FOLDER'] = 'data'
app.config['DB_FILE'] = 'data/pitches.db'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# =====================================================================
# Database Setup
# =====================================================================
def get_db():
    conn = sqlite3.connect(app.config['DB_FILE'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS pitches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            industry TEXT,
            stage TEXT,
            problem TEXT,
            solution TEXT,
            technology TEXT,
            market TEXT,
            business_model TEXT,
            team_info TEXT,
            competitors TEXT,
            advantage TEXT,
            current_status TEXT,
            pitch_script TEXT,
            slide_content TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# =====================================================================
# AI API Integration
# =====================================================================
def call_ai(prompt, system_prompt=None):
    """调用AI生成路演内容，支持多个API"""
    import requests
    
    # 优先使用硅基流动（免费额度）
    api_key = os.environ.get('SILICONFLOW_API_KEY')
    if api_key:
        try:
            url = "https://api.siliconflow.cn/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            data = {
                "model": "Qwen/Qwen2.5-7B-Instruct",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            resp = requests.post(url, headers=headers, json=data, timeout=60)
            if resp.status_code == 200:
                result = resp.json()
                return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"[WARN] SiliconFlow API failed: {e}")
    
    # 备选：DeepSeek
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if api_key:
        try:
            url = "https://api.deepseek.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            data = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            resp = requests.post(url, headers=headers, json=data, timeout=60)
            if resp.status_code == 200:
                result = resp.json()
                return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"[WARN] DeepSeek API failed: {e}")
    
    # 备选：OpenAI
    api_key = os.environ.get('OPENAI_API_KEY')
    if api_key:
        try:
            base_url = os.environ.get('OPENAI_API_BASE', 'https://api.openai.com/v1')
            url = f"{base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            data = {
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            resp = requests.post(url, headers=headers, json=data, timeout=60)
            if resp.status_code == 200:
                result = resp.json()
                return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"[WARN] OpenAI API failed: {e}")
    
    return None

# =====================================================================
# Pitch Generation Logic
# =====================================================================
SYSTEM_PROMPT = """你是一位资深的风险投资人（VC），擅长评估创新项目，也是一位顶尖的创业路演教练。
请基于用户提供的项目信息，生成专业、简洁、有感染力的路演脚本和幻灯片内容。
注意：
- 路演脚本要口语化、有激情、逻辑清晰
- 每页幻灯片内容要精炼，每页不超过3个要点
- 突出项目的创新性和商业价值
- 适当使用数据增强说服力（如市场规模、增长率等）
- 控制在8-10页路演内容
"""

def generate_pitch_content(data):
    """生成完整路演内容"""
    prompt = f"""
## 项目基本信息
- 项目名称：{data.get('project_name', '')}
- 所属行业：{data.get('industry', '')}
- 项目阶段：{data.get('stage', '')}
- 一句话介绍（解决什么问题）：{data.get('problem', '')}

## 解决方案
{data.get('solution', '')}

## 核心技术/创新点
{data.get('technology', '')}

## 市场规模与前景
{data.get('market', '')}

## 商业模式
{data.get('business_model', '')}

## 团队介绍
{data.get('team_info', '')}

## 竞争优势
{data.get('advantage', '')}

## 当前进展
{data.get('current_status', '')}

请生成以下内容：

### 1. 路演脚本
为每个幻灯片写一段路演演讲稿（约150字/页），包含：
- 开场hook（一句话吸引评委）
- 核心内容（2-3个要点）
- 金句收尾

### 2. 幻灯片内容（JSON格式）
8-10页幻灯片，每页包含：
- slide_number: 页码
- title: 标题
- subtitle: 副标题
- points: 要点列表（每页不超过3个）
- talking_point: 本页核心演讲词
- visual_suggestion: 建议的视觉元素

请用JSON格式输出slides内容。
"""

    result = call_ai(prompt, SYSTEM_PROMPT)
    return result

def parse_slides_from_ai(ai_output):
    """从AI输出中解析幻灯片JSON"""
    if not ai_output:
        return None
    
    # 尝试提取JSON
    json_match = re.search(r'\[.*\]', ai_output, re.DOTALL)
    if json_match:
        try:
            slides = json.loads(json_match.group())
            return slides
        except:
            pass
    
    # 尝试在整个输出中找JSON对象
    try:
        # 查找 ```json ... ``` 块
        json_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', ai_output)
        for block in json_blocks:
            try:
                slides = json.loads(block.strip())
                if isinstance(slides, list):
                    return slides
            except:
                pass
    except:
        pass
    
    return None

def build_slide_content(data, ai_output=None):
    """构建幻灯片内容"""
    slides_data = parse_slides_from_ai(ai_output)
    
    if slides_data is None:
        # 使用默认模板
        slides_data = [
            {
                "slide_number": 1,
                "title": "封面",
                "subtitle": data.get('project_name', '项目名称'),
                "points": [f"行业：{data.get('industry', '未知')}", f"阶段：{data.get('stage', '未知')}"],
                "talking_point": f"各位评委好，今天我为大家介绍{data.get('project_name', '我们的项目')}，我们致力于解决{data.get('problem', '行业痛点')}。",
                "visual_suggestion": "项目名称大字居中，团队logo，日期"
            },
            {
                "slide_number": 2,
                "title": "痛点分析",
                "subtitle": "我们发现了什么问题？",
                "points": [data.get('problem', '行业存在以下痛点')],
                "talking_point": f"在我们深入调研后发现，当前市场存在严重的问题：{data.get('problem', '痛点描述')}",
                "visual_suggestion": "用数据图表展示市场规模和痛点严重程度"
            },
            {
                "slide_number": 3,
                "title": "解决方案",
                "subtitle": "我们如何解决这个问题？",
                "points": [data.get('solution', '解决方案描述')],
                "talking_point": f"针对上述问题，我们提出了创新的解决方案：{data.get('solution', '')}",
                "visual_suggestion": "产品截图或流程图，展示核心功能"
            },
            {
                "slide_number": 4,
                "title": "核心技术",
                "subtitle": "我们的技术优势",
                "points": [data.get('technology', '核心技术描述')],
                "talking_point": f"我们的核心竞争力在于：{data.get('technology', '')}",
                "visual_suggestion": "技术架构图或原理示意图"
            },
            {
                "slide_number": 5,
                "title": "市场分析",
                "subtitle": "蛋糕有多大？",
                "points": [data.get('market', '市场分析描述')],
                "talking_point": f"根据我们的调研：{data.get('market', '')}",
                "visual_suggestion": "市场容量图表，目标用户画像"
            },
            {
                "slide_number": 6,
                "title": "商业模式",
                "subtitle": "如何赚钱？",
                "points": [data.get('business_model', '商业模式描述')],
                "talking_point": f"我们的商业模式：{data.get('business_model', '')}",
                "visual_suggestion": "收入结构图或运营数据"
            },
            {
                "slide_number": 7,
                "title": "竞争优势",
                "subtitle": "为什么是我们？",
                "points": [data.get('advantage', '竞争优势描述')],
                "talking_point": f"相比竞争对手，我们的优势在于：{data.get('advantage', '')}",
                "visual_suggestion": "对比表格，突出差异化"
            },
            {
                "slide_number": 8,
                "title": "团队介绍",
                "subtitle": "谁在做这件事？",
                "points": [data.get('team_info', '团队介绍')],
                "talking_point": f"我们的团队：{data.get('team_info', '')}",
                "visual_suggestion": "团队成员照片+背景介绍"
            },
            {
                "slide_number": 9,
                "title": "当前进展",
                "subtitle": "我们做到了什么？",
                "points": [data.get('current_status', '当前进展')],
                "talking_point": f"目前我们已经：{data.get('current_status', '')}",
                "visual_suggestion": "时间轴或里程碑成果展示"
            },
            {
                "slide_number": 10,
                "title": "融资计划",
                "subtitle": "期待您的支持",
                "points": ["本轮计划融资[X]万元", "资金用途：研发[X%] + 市场[X%] + 团队[X%]", "预计[X]年内实现盈亏平衡"],
                "talking_point": "我们希望获得本轮融资，用于加速产品研发和市场拓展，期待与各位评委共同见证项目的成长！",
                "visual_suggestion": "融资用途饼图，里程碑规划"
            }
        ]
    
    return slides_data

def build_pitch_script(data, slides_data):
    """生成路演脚本"""
    if not slides_data:
        return "路演脚本生成失败，请重试。"
    
    script_parts = []
    for i, slide in enumerate(slides_data):
        script_parts.append(f"""
{'='*50}
📄 第{slide['slide_number']}页：{slide['title']}
{'='*50}

🎤 演讲稿：
{slide.get('talking_point', '')}

📌 核心要点：
{chr(10).join([f"  • {p}" for p in slide.get('points', [])])}

🎨 视觉建议：{slide.get('visual_suggestion', '')}

""")
    
    return "\n".join(script_parts)

# =====================================================================
# Routes
# =====================================================================
@app.route('/')
def index():
    """主页"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM pitches ORDER BY created_at DESC LIMIT 10')
    recent = [dict(row) for row in c.fetchall()]
    conn.close()
    return render_template('index.html', recent=recent)

@app.route('/guide')
def guide():
    """路演指南"""
    return render_template('guide.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    """生成路演内容"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '请提供项目信息'})
    
    project_name = data.get('project_name', '').strip()
    if not project_name:
        return jsonify({'success': False, 'message': '请输入项目名称'})
    
    # 生成AI内容
    ai_output = generate_pitch_content(data)
    
    # 构建幻灯片
    slides = build_slide_content(data, ai_output)
    
    # 构建脚本
    script = build_pitch_script(data, slides)
    
    # 保存到数据库
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO pitches 
        (project_name, industry, stage, problem, solution, technology, market, business_model, team_info, competitors, advantage, current_status, pitch_script, slide_content, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        project_name,
        data.get('industry', ''),
        data.get('stage', ''),
        data.get('problem', ''),
        data.get('solution', ''),
        data.get('technology', ''),
        data.get('market', ''),
        data.get('business_model', ''),
        data.get('team_info', ''),
        data.get('competitors', ''),
        data.get('advantage', ''),
        data.get('current_status', ''),
        script,
        json.dumps(slides, ensure_ascii=False),
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))
    pitch_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'pitch_id': pitch_id,
        'slides': slides,
        'script': script,
        'message': '路演内容生成成功！'
    })

@app.route('/api/pitch/<int:pitch_id>')
def get_pitch(pitch_id):
    """获取历史路演"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM pitches WHERE id = ?', (pitch_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({'success': False, 'message': '未找到该路演'})
    
    row_dict = dict(row)
    if row_dict.get('slide_content'):
        try:
            row_dict['slides'] = json.loads(row_dict['slide_content'])
        except:
            row_dict['slides'] = []
    
    return jsonify({'success': True, 'pitch': row_dict})

@app.route('/api/history')
def history():
    """获取历史记录"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, project_name, industry, created_at FROM pitches ORDER BY created_at DESC LIMIT 50')
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'success': True, 'history': rows})

@app.route('/slides/<int:pitch_id>')
def view_slides(pitch_id):
    """幻灯片预览"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM pitches WHERE id = ?', (pitch_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return "未找到该路演", 404
    
    row_dict = dict(row)
    if row_dict.get('slide_content'):
        try:
            row_dict['slides'] = json.loads(row_dict['slide_content'])
        except:
            row_dict['slides'] = []
    
    row_dict['slides_json'] = json.dumps(row_dict.get('slides', []), ensure_ascii=False)
    return render_template('slides.html', pitch=row_dict)

@app.route('/api/improve_slide', methods=['POST'])
def improve_slide():
    """AI优化单页幻灯片"""
    data = request.get_json()
    slide_text = data.get('slide_text', '')
    slide_num = data.get('slide_num', 1)
    
    if not slide_text:
        return jsonify({'success': False, 'message': '请提供幻灯片内容'})
    
    prompt = f"""请优化以下第{slide_num}页幻灯片内容，让它更有感染力和说服力：

当前内容：
{slide_text}

请以JSON格式返回优化后的内容，格式如下：
{{
    "title": "优化后的标题",
    "subtitle": "优化后的副标题", 
    "points": ["要点1", "要点2", "要点3"],
    "talking_point": "优化后的演讲词（约150字，有激情有逻辑）"
}}
只返回JSON，不要其他内容。
"""
    
    result = call_ai(prompt)
    if result:
        try:
            improved = json.loads(result)
            return jsonify({'success': True, 'improved': improved})
        except:
            return jsonify({'success': False, 'message': '优化解析失败', 'raw': result})
    
    return jsonify({'success': False, 'message': 'AI服务暂不可用，请检查API配置'})

@app.route('/api/export_script/<int:pitch_id>')
def export_script(pitch_id):
    """导出路演脚本"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT pitch_script, project_name FROM pitches WHERE id = ?', (pitch_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return "未找到该路演", 404
    
    script_content = f"""
================================================================================
                        {row['project_name']} - 路演脚本
================================================================================
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
--------------------------------------------------------------------------------
{row['pitch_script']}

================================================================================
                          使用说明
================================================================================
1. 熟读每页内容，理解核心观点
2. 控制每页演讲时间在60-90秒
3. 注意语速和眼神交流
4. 数据部分要自信、有感染力
5. 结尾要有号召力，留下深刻印象
================================================================================
"""
    
    filename = f"路演脚本_{row['project_name']}_{datetime.now().strftime('%Y%m%d')}.txt"
    return send_file(
        io.BytesIO(script_content.encode('utf-8')),
        mimetype='text/plain',
        as_attachment=True,
        download_name=filename
    )

# =====================================================================
# Entry Point
# =====================================================================
if __name__ == '__main__':
    print("=" * 60)
    print("🎯 AI创新路演助手 (AI Pitch Architect)")
    print("📍 访问地址: http://localhost:5095")
    print("=" * 60)
    print("提示：首次使用建议配置AI API以获得更好的生成效果")
    print("  硅基流动（推荐）: export SILICONFLOW_API_KEY=your_key")
    print("  DeepSeek: export DEEPSEEK_API_KEY=your_key")
    print("  OpenAI: export OPENAI_API_KEY=your_key")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5095, debug=True)
