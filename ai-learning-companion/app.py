#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI学习伙伴 - 智能问答 + 学习管理助手
功能：AI答疑、学习笔记、番茄钟、学习统计
基于中国国际大学生创新大赛获奖项目"慧语科技"教育AI灵感实现
"""

import os
import json
import time
import uuid
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, render_template, jsonify, session, redirect, url_for
import requests

# ==================== 配置 ====================
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'ai-learning-companion-secret-2026')

# AI API 配置 - 支持多个免费/低成本API
AI_CONFIG = {
    # 硅基流动 API (免费额度)
    'siliconflow': {
        'enabled': bool(os.environ.get('SILICONFLOW_API_KEY')),
        'api_key': os.environ.get('SILICONFLOW_API_KEY', ''),
        'base_url': 'https://api.siliconflow.cn/v1',
        'model': 'Qwen/Qwen2.5-7B-Instruct',
        'name': '硅基流动 (免费)',
    },
    # OpenAI API (可选)
    'openai': {
        'enabled': bool(os.environ.get('OPENAI_API_KEY')),
        'api_key': os.environ.get('OPENAI_API_KEY', ''),
        'base_url': 'https://api.openai.com/v1',
        'model': 'gpt-3.5-turbo',
        'name': 'OpenAI GPT-3.5',
    },
    # DeepSeek API (低成本)
    'deepseek': {
        'enabled': bool(os.environ.get('DEEPSEEK_API_KEY')),
        'api_key': os.environ.get('DEEPSEEK_API_KEY', ''),
        'base_url': 'https://api.deepseek.com/v1',
        'model': 'deepseek-chat',
        'name': 'DeepSeek',
    },
}

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'learning_companion.db')

# ==================== 数据库初始化 ====================
def init_db():
    """初始化SQLite数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 笔记表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            subject TEXT,
            tags TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    # 问答历史表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS qa_history (
            id TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT,
            subject TEXT,
            created_at TEXT
        )
    ''')
    
    # 番茄钟记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pomodoro_records (
            id TEXT PRIMARY KEY,
            duration INTEGER,
            subject TEXT,
            completed_at TEXT
        )
    ''')
    
    # 学习统计表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            pomodoro_count INTEGER DEFAULT 0,
            total_minutes INTEGER DEFAULT 0,
            questions_asked INTEGER DEFAULT 0,
            notes_created INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ==================== 辅助函数 ====================
def get_today_str():
    return datetime.now().strftime('%Y-%m-%d')

def update_today_stats(field, increment=1):
    """更新今日统计"""
    today = get_today_str()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM study_stats WHERE date = ?', (today,))
    row = cursor.fetchone()
    
    if row:
        cursor.execute(f'UPDATE study_stats SET {field} = {field} + ? WHERE date = ?', (increment, today))
    else:
        cursor.execute('INSERT INTO study_stats (date, pomodoro_count, total_minutes, questions_asked, notes_created) VALUES (?, 0, 0, 0, 0)', (today,))
        cursor.execute(f'UPDATE study_stats SET {field} = ? WHERE date = ?', (increment, today))
    
    conn.commit()
    conn.close()

def get_week_stats():
    """获取最近7天的学习统计"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    placeholders = ','.join(['?' for _ in dates])
    
    cursor.execute(f'''
        SELECT date, pomodoro_count, total_minutes, questions_asked, notes_created 
        FROM study_stats 
        WHERE date IN ({placeholders})
        ORDER BY date
    ''', dates)
    
    rows = cursor.fetchall()
    conn.close()
    
    stats = {row[0]: {'pomodoro': row[1], 'minutes': row[2], 'questions': row[3], 'notes': row[4]} for row in rows}
    
    # 填充没有数据的日期
    for d in dates:
        if d not in stats:
            stats[d] = {'pomodoro': 0, 'minutes': 0, 'questions': 0, 'notes': 0}
    
    return [(d, stats[d]) for d in dates]

# ==================== AI 调用函数 ====================
def call_ai(prompt, system_prompt="你是一个友好的AI学习助手，擅长解答各学科问题。"):
    """调用AI API，支持多后端自动切换"""
    
    # 优先使用硅基流动（免费）
    if AI_CONFIG['siliconflow']['enabled']:
        return call_siliconflow(prompt, system_prompt)
    elif AI_CONFIG['deepseek']['enabled']:
        return call_deepseek(prompt, system_prompt)
    elif AI_CONFIG['openai']['enabled']:
        return call_openai(prompt, system_prompt)
    else:
        return None, "⚠️ 未配置AI API，请设置以下任一环境变量：\n- SILICONFLOW_API_KEY（推荐，免费）\n- DEEPSEEK_API_KEY\n- OPENAI_API_KEY"

def call_siliconflow(prompt, system_prompt):
    """调用硅基流动API"""
    config = AI_CONFIG['siliconflow']
    headers = {
        'Authorization': f'Bearer {config["api_key"]}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': config['model'],
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7,
        'max_tokens': 2000,
    }
    
    try:
        response = requests.post(
            f'{config["base_url"]}/chat/completions',
            headers=headers,
            json=payload,
            timeout=60
        )
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content'], None
        elif 'error' in result:
            return None, f"API错误: {result['error'].get('message', '未知错误')}"
        else:
            return None, f"响应格式异常: {str(result)[:200]}"
    except Exception as e:
        return None, f"请求失败: {str(e)}"

def call_deepseek(prompt, system_prompt):
    """调用DeepSeek API"""
    config = AI_CONFIG['deepseek']
    headers = {
        'Authorization': f'Bearer {config["api_key"]}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': config['model'],
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7,
        'max_tokens': 2000,
    }
    
    try:
        response = requests.post(
            f'{config["base_url"]}/chat/completions',
            headers=headers,
            json=payload,
            timeout=60
        )
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content'], None
        elif 'error' in result:
            return None, f"API错误: {result['error'].get('message', '未知错误')}"
        else:
            return None, f"响应格式异常: {str(result)[:200]}"
    except Exception as e:
        return None, f"请求失败: {str(e)}"

def call_openai(prompt, system_prompt):
    """调用OpenAI API"""
    config = AI_CONFIG['openai']
    headers = {
        'Authorization': f'Bearer {config["api_key"]}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': config['model'],
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7,
        'max_tokens': 2000,
    }
    
    try:
        response = requests.post(
            f'{config["base_url"]}/chat/completions',
            headers=headers,
            json=payload,
            timeout=60
        )
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content'], None
        elif 'error' in result:
            return None, f"API错误: {result['error'].get('message', '未知错误')}"
        else:
            return None, f"响应格式异常: {str(result)[:200]}"
    except Exception as e:
        return None, f"请求失败: {str(e)}"

def get_ai_status():
    """获取当前AI配置状态"""
    for name, config in AI_CONFIG.items():
        if config['enabled']:
            return f"✅ {config['name']}"
    return "❌ 未配置"

# ==================== 路由 ====================
@app.route('/')
def index():
    """主页"""
    # 获取统计数据
    week_stats = get_week_stats()
    total_pomodoro = sum(s[1]['pomodoro'] for s in week_stats)
    total_minutes = sum(s[1]['minutes'] for s in week_stats)
    total_questions = sum(s[1]['questions'] for s in week_stats)
    total_notes = sum(s[1]['notes'] for s in week_stats)
    
    # 获取最新笔记
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, subject, created_at FROM notes ORDER BY created_at DESC LIMIT 5')
    recent_notes = cursor.fetchall()
    cursor.execute('SELECT id, question, answer, subject, created_at FROM qa_history ORDER BY created_at DESC LIMIT 5')
    recent_qa = cursor.fetchall()
    conn.close()
    
    return render_template(
        'index.html',
        week_stats=week_stats,
        total_pomodoro=total_pomodoro,
        total_minutes=total_minutes,
        total_questions=total_questions,
        total_notes=total_notes,
        recent_notes=recent_notes,
        recent_qa=recent_qa,
        ai_status=get_ai_status(),
    )

@app.route('/ask', methods=['POST'])
def ask():
    """AI问答接口"""
    data = request.get_json()
    question = data.get('question', '').strip()
    subject = data.get('subject', '通用')
    
    if not question:
        return jsonify({'success': False, 'error': '问题不能为空'})
    
    # 构建提示词
    system_prompt = f"""你是一个友好的AI学习助手，擅长解答各学科问题。
当前科目：{subject}
请用清晰、易懂的方式回答问题，适当使用markdown格式。
如果问题是关于数学或科学，请尽量给出步骤解释。"""
    
    answer, error = call_ai(question, system_prompt)
    
    if error:
        return jsonify({'success': False, 'error': error})
    
    # 保存到数据库
    qa_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO qa_history (id, question, answer, subject, created_at) VALUES (?, ?, ?, ?, ?)',
        (qa_id, question, answer, subject, now)
    )
    conn.commit()
    conn.close()
    
    update_today_stats('questions_asked')
    
    return jsonify({
        'success': True,
        'answer': answer,
        'qa_id': qa_id,
    })

@app.route('/notes', methods=['GET', 'POST'])
def notes():
    """笔记管理"""
    if request.method == 'POST':
        data = request.get_json()
        action = data.get('action')
        
        if action == 'create':
            note_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO notes (id, title, content, subject, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (note_id, data.get('title', '无标题'), data.get('content', ''), 
                 data.get('subject', ''), data.get('tags', ''), now, now)
            )
            conn.commit()
            conn.close()
            
            update_today_stats('notes_created')
            return jsonify({'success': True, 'id': note_id})
        
        elif action == 'update':
            note_id = data.get('id')
            now = datetime.now().isoformat()
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE notes SET title=?, content=?, subject=?, tags=?, updated_at=? WHERE id=?',
                (data.get('title'), data.get('content'), data.get('subject'),
                 data.get('tags'), now, note_id)
            )
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        
        elif action == 'delete':
            note_id = data.get('id')
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM notes WHERE id=?', (note_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
    
    # GET: 获取所有笔记
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, content, subject, tags, created_at, updated_at FROM notes ORDER BY updated_at DESC')
    all_notes = cursor.fetchall()
    conn.close()
    
    return render_template('notes.html', notes=all_notes)

@app.route('/note/<note_id>')
def note_detail(note_id):
    """笔记详情"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, content, subject, tags, created_at, updated_at FROM notes WHERE id=?', (note_id,))
    note = cursor.fetchone()
    conn.close()
    
    if not note:
        return "笔记不存在", 404
    
    return render_template('note_detail.html', note=note)

@app.route('/pomodoro', methods=['GET', 'POST'])
def pomodoro():
    """番茄钟"""
    if request.method == 'POST':
        data = request.get_json()
        action = data.get('action')
        
        if action == 'record':
            # 记录完成的番茄钟
            record_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            duration = data.get('duration', 25)
            subject = data.get('subject', '通用')
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO pomodoro_records (id, duration, subject, completed_at) VALUES (?, ?, ?, ?)',
                (record_id, duration, subject, now)
            )
            conn.commit()
            conn.close()
            
            update_today_stats('pomodoro_count')
            update_today_stats('total_minutes', duration)
            
            return jsonify({'success': True})
    
    # 获取今日番茄钟数量
    today = get_today_str()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT pomodoro_count, total_minutes FROM study_stats WHERE date=?', (today,))
    row = cursor.fetchone()
    today_pomodoro = row[0] if row else 0
    today_minutes = row[1] if row else 0
    conn.close()
    
    return render_template('pomodoro.html', today_pomodoro=today_pomodoro, today_minutes=today_minutes)

@app.route('/api/stats')
def stats():
    """获取统计数据API"""
    week_stats = get_week_stats()
    return jsonify({
        'success': True,
        'week_stats': [
            {'date': d, 'pomodoro': s['pomodoro'], 'minutes': s['minutes'], 
             'questions': s['questions'], 'notes': s['notes']}
            for d, s in week_stats
        ]
    })

# ==================== 启动 ====================
if __name__ == '__main__':
    print("=" * 60)
    print("📚 AI学习伙伴 启动中...")
    print(f"   AI状态: {get_ai_status()}")
    print("📍 访问地址: http://localhost:5050")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5050, debug=True)
