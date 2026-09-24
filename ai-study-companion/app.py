#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 自习伙伴 (AI Study Companion)
=================================
灵感来源：中国国际大学生创新大赛 AI+教育 赛道获奖项目

功能：
- 📚 AI问答助手（任何学科问题都能问）
- 📝 课程笔记管理（添加、整理、搜索）
- 🎯 自动出题（AI根据笔记生成练习题）
- 🧠 间隔重复记忆（SM-2算法驱动的复习计划）
- 📊 学习进度仪表盘

作者：俞 ✨
"""

import os
import re
import json
import uuid
import sqlite3
import hashlib
from datetime import datetime, timedelta
from functools import wraps

import requests
import yaml
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

# ==================== 配置 ====================
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'ai-study-companion-secret-2026')
app.config['JSON_AS_ASCII'] = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

PORT = int(os.environ.get('PORT', 5010))

# ==================== 数据库初始化 ====================
DB_PATH = os.path.join(DATA_DIR, 'study_companion.db')

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表"""
    conn = get_db()
    cur = conn.cursor()
    
    # 科目表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            color TEXT DEFAULT '#4CAF50',
            created_at TEXT NOT NULL
        )
    ''')
    
    # 笔记表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            subject_id TEXT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            tags TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        )
    ''')
    
    # 闪卡表（间隔重复）
    cur.execute('''
        CREATE TABLE IF NOT EXISTS flashcards (
            id TEXT PRIMARY KEY,
            note_id TEXT,
            subject_id TEXT,
            front TEXT NOT NULL,
            back TEXT NOT NULL,
            ease_factor REAL DEFAULT 2.5,
            interval_days INTEGER DEFAULT 0,
            repetitions INTEGER DEFAULT 0,
            next_review TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (note_id) REFERENCES notes(id),
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        )
    ''')
    
    # 复习记录表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS review_logs (
            id TEXT PRIMARY KEY,
            flashcard_id TEXT,
            quality INTEGER,
            reviewed_at TEXT,
            FOREIGN KEY (flashcard_id) REFERENCES flashcards(id)
        )
    ''')
    
    # 学习记录表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS study_logs (
            id TEXT PRIMARY KEY,
            action TEXT NOT NULL,
            detail TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # 插入默认科目
    cur.execute("SELECT COUNT(*) FROM subjects")
    if cur.fetchone()[0] == 0:
        default_subjects = [
            ('math', '数学', '#2196F3'),
            ('cs', '计算机科学', '#9C27B0'),
            ('physics', '物理学', '#FF9800'),
            ('english', '英语', '#E91E63'),
            ('economics', '经济学', '#00BCD4'),
            ('history', '历史', '#795548'),
            ('other', '其他', '#607D8B'),
        ]
        for sid, name, color in default_subjects:
            cur.execute(
                "INSERT OR IGNORE INTO subjects (id, name, color, created_at) VALUES (?, ?, ?, ?)",
                (sid, name, color, datetime.now().isoformat())
            )
    
    conn.commit()
    conn.close()

# SM-2 间隔重复算法
def sm2_algorithm(quality, ease_factor, interval, repetitions):
    """
    SM-2 间隔重复算法
    quality: 0-5 (0=完全忘记, 5=完美记住)
    返回: (new_ease_factor, new_interval, new_repetitions)
    """
    if quality < 3:
        # 忘记，重新开始
        new_repetitions = 0
        new_interval = 1
    else:
        new_repetitions = repetitions + 1
        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            new_interval = round(interval * ease_factor)
    
    # 更新容易度因子
    new_ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ease_factor = max(1.3, new_ease_factor)  # 最低1.3
    
    return new_ease_factor, new_interval, new_repetitions

def quality_from_rating(rating):
    """将1-5评分转换为SM-2质量值"""
    mapping = {1: 0, 2: 1, 3: 3, 4: 4, 5: 5}
    return mapping.get(rating, 3)

# ==================== AI API ====================

def load_api_config():
    """加载API配置"""
    yaml_path = os.path.join(BASE_DIR, 'config.yaml')
    if os.path.exists(yaml_path):
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}

def call_ai(prompt, system_prompt=None, model=None):
    """
    调用AI接口，支持多后端自动切换
    优先级: SiliconFlow(免费) > DeepSeek > OpenAI
    """
    config = load_api_config()
    
    # SiliconFlow (免费额度)
    sf_key = os.environ.get('SILICONFLOW_API_KEY', config.get('siliconflow', {}).get('api_key', ''))
    if sf_key:
        try:
            resp = requests.post(
                'https://api.siliconflow.cn/v1/chat/completions',
                headers={'Authorization': f'Bearer {sf_key}', 'Content-Type': 'application/json'},
                json={
                    'model': model or 'Qwen/Qwen2.5-7B-Instruct',
                    'messages': (
                        [{'role': 'system', 'content': system_prompt}] if system_prompt else []
                    ) + [{'role': 'user', 'content': prompt}],
                    'temperature': 0.7,
                    'max_tokens': 1024,
                },
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
        except Exception:
            pass
    
    # DeepSeek
    ds_key = os.environ.get('DEEPSEEK_API_KEY', config.get('deepseek', {}).get('api_key', ''))
    if ds_key:
        try:
            resp = requests.post(
                'https://api.deepseek.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {ds_key}', 'Content-Type': 'application/json'},
                json={
                    'model': model or 'deepseek-chat',
                    'messages': (
                        [{'role': 'system', 'content': system_prompt}] if system_prompt else []
                    ) + [{'role': 'user', 'content': prompt}],
                    'temperature': 0.7,
                    'max_tokens': 1024,
                },
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
        except Exception:
            pass
    
    # OpenAI
    openai_key = os.environ.get('OPENAI_API_KEY', config.get('openai', {}).get('api_key', ''))
    if openai_key:
        try:
            resp = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {openai_key}', 'Content-Type': 'application/json'},
                json={
                    'model': model or 'gpt-4o-mini',
                    'messages': (
                        [{'role': 'system', 'content': system_prompt}] if system_prompt else []
                    ) + [{'role': 'user', 'content': prompt}],
                    'temperature': 0.7,
                    'max_tokens': 1024,
                },
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
        except Exception:
            pass
    
    return None

# ==================== 页面路由 ====================

@app.route('/')
def index():
    """首页仪表盘"""
    conn = get_db()
    cur = conn.cursor()
    
    # 统计数据
    cur.execute("SELECT COUNT(*) FROM subjects")
    subject_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM notes")
    note_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM flashcards")
    flashcard_count = cur.fetchone()[0]
    
    # 今日待复习
    today = datetime.now().date().isoformat()
    cur.execute("SELECT COUNT(*) FROM flashcards WHERE date(next_review) <= ?", (today,))
    due_review = cur.fetchone()[0]
    
    # 最近学习记录
    cur.execute("SELECT * FROM study_logs ORDER BY created_at DESC LIMIT 10")
    logs = [dict(row) for row in cur.fetchall()]
    
    # 今日新增
    cur.execute("SELECT COUNT(*) FROM notes WHERE date(created_at) = ?", (today,))
    today_notes = cur.fetchone()[0]
    
    conn.close()
    
    return render_template('index.html',
                           subject_count=subject_count,
                           note_count=note_count,
                           flashcard_count=flashcard_count,
                           due_review=due_review,
                           today_notes=today_notes,
                           logs=logs)

@app.route('/subjects')
def subjects_page():
    """科目管理页"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM subjects ORDER BY name")
    subjects = [dict(row) for row in cur.fetchall()]
    
    # 每个科目的笔记和闪卡数量
    for s in subjects:
        cur.execute("SELECT COUNT(*) FROM notes WHERE subject_id = ?", (s['id'],))
        s['note_count'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM flashcards WHERE subject_id = ?", (s['id'],))
        s['flashcard_count'] = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM flashcards WHERE subject_id = ? AND date(next_review) <= ?",
            (s['id'], datetime.now().date().isoformat())
        )
        s['due_review'] = cur.fetchone()[0]
    
    conn.close()
    return render_template('subjects.html', subjects=subjects)

@app.route('/notes')
def notes_page():
    """笔记列表页"""
    subject_id = request.args.get('subject', '')
    search = request.args.get('search', '')
    
    conn = get_db()
    cur = conn.cursor()
    
    query = "SELECT * FROM notes WHERE 1=1"
    params = []
    
    if subject_id:
        query += " AND subject_id = ?"
        params.append(subject_id)
    
    if search:
        query += " AND (title LIKE ? OR content LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])
    
    query += " ORDER BY updated_at DESC"
    cur.execute(query, params)
    notes = [dict(row) for row in cur.fetchall()]
    
    # 加载科目名
    cur.execute("SELECT * FROM subjects")
    subject_map = {row['id']: row['name'] for row in cur.fetchall()}
    for n in notes:
        n['subject_name'] = subject_map.get(n['subject_id'], '未分类')
    
    cur.execute("SELECT * FROM subjects ORDER BY name")
    subjects = [dict(row) for row in cur.fetchall()]
    conn.close()
    
    return render_template('notes.html', notes=notes, subjects=subjects,
                           current_subject=subject_id, search=search)

@app.route('/note/new', methods=['GET', 'POST'])
def note_new():
    """新建笔记"""
    if request.method == 'POST':
        data = request.get_json()
        note_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO notes (id, subject_id, title, content, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (note_id, data.get('subject_id'), data['title'], data['content'],
             data.get('tags', ''), now, now)
        )
        conn.commit()
        conn.close()
        
        # 记录
        log_action('create_note', f"新建笔记: {data['title']}")
        
        return jsonify({'success': True, 'id': note_id})
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM subjects ORDER BY name")
    subjects = [dict(row) for row in cur.fetchall()]
    conn.close()
    return render_template('note_edit.html', note=None, subjects=subjects)

@app.route('/note/<note_id>')
def note_view(note_id):
    """查看笔记"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    note = dict(cur.fetchone()) if cur.fetchone() else None
    
    if not note:
        conn.close()
        return "笔记不存在", 404
    
    cur.execute("SELECT * FROM subjects WHERE id = ?", (note['subject_id'],))
    row = cur.fetchone()
    note['subject_name'] = row['name'] if row else '未分类'
    
    # 相关闪卡
    cur.execute("SELECT * FROM flashcards WHERE note_id = ?", (note_id,))
    note['flashcards'] = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    return render_template('note_view.html', note=note)

@app.route('/note/<note_id>/edit', methods=['GET', 'POST'])
def note_edit(note_id):
    """编辑笔记"""
    conn = get_db()
    cur = conn.cursor()
    
    if request.method == 'POST':
        data = request.get_json()
        now = datetime.now().isoformat()
        cur.execute(
            "UPDATE notes SET title=?, content=?, subject_id=?, tags=?, updated_at=? WHERE id=?",
            (data['title'], data['content'], data.get('subject_id'), data.get('tags', ''), now, note_id)
        )
        conn.commit()
        conn.close()
        log_action('update_note', f"更新笔记: {data['title']}")
        return jsonify({'success': True})
    
    cur.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    note = dict(cur.fetchone()) if cur.fetchone() else None
    cur.execute("SELECT * FROM subjects ORDER BY name")
    subjects = [dict(row) for row in cur.fetchall()]
    conn.close()
    
    if not note:
        return "笔记不存在", 404
    return render_template('note_edit.html', note=note, subjects=subjects)

@app.route('/note/<note_id>/delete', methods=['POST'])
def note_delete(note_id):
    """删除笔记"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT title FROM notes WHERE id = ?", (note_id,))
    row = cur.fetchone()
    title = row['title'] if row else ''
    cur.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    cur.execute("DELETE FROM flashcards WHERE note_id = ?", (note_id,))
    conn.commit()
    conn.close()
    log_action('delete_note', f"删除笔记: {title}")
    return jsonify({'success': True})

@app.route('/api/note/<note_id>/summarize', methods=['POST'])
def summarize_note(note_id):
    """AI生成笔记摘要"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    note = dict(cur.fetchone())
    conn.close()
    
    prompt = f"""请为以下学习笔记生成简洁摘要，并提取3-5个关键知识点。

笔记标题：{note['title']}
笔记内容：
{note['content']}

请用以下格式回复：
摘要：[50字以内的摘要]

关键知识点：
1. [知识点1]
2. [知识点2]
3. [知识点3]
（如果有更多重要知识点继续列在下面）
"""
    
    result = call_ai(prompt, system_prompt="你是一个学习助手，负责帮助学生整理和理解学习内容。请简洁、准确地总结。")
    
    if result:
        # 提取摘要和关键知识点
        summary = ''
        key_points = []
        lines = result.strip().split('\n')
        capture_kp = False
        for line in lines:
            if line.startswith('摘要：') or line.startswith('摘要:'):
                summary = line.split('：', 1)[-1].split(':', 1)[-1].strip()
            elif '关键知识点' in line or '关键知识' in line:
                capture_kp = True
            elif capture_kp and line.strip():
                if line.strip()[0].isdigit() or line.strip().startswith('-') or line.strip().startswith('•'):
                    key_points.append(line.strip())
        
        # 更新笔记
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE notes SET summary = ? WHERE id = ?", (result, note_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'summary': result, 'extracted_points': key_points})
    
    return jsonify({'success': False, 'error': 'AI服务暂时不可用，请检查API配置'})

@app.route('/api/note/<note_id>/generate-flashcards', methods=['POST'])
def generate_flashcards(note_id):
    """AI根据笔记生成闪卡"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    note = dict(cur.fetchone())
    conn.close()
    
    prompt = f"""请根据以下学习笔记，生成5-10个间隔重复闪卡。

每个闪卡包含：
- 正面（问题/概念）
- 背面（答案/解释）

笔记内容：
{note['title']}
{note['content']}

请用JSON数组格式回复，每个元素包含front和back字段：
[
  {{"front": "问题1", "back": "答案1"}},
  {{"front": "问题2", "back": "答案2"}}
]

只回复JSON，不要其他文字：
"""
    
    result = call_ai(prompt, system_prompt="你是一个学习助手，根据笔记内容生成高质量的间隔重复闪卡。")
    
    if result:
        try:
            # 尝试提取JSON
            match = re.search(r'\[.*\]', result, re.DOTALL)
            if match:
                cards = json.loads(match.group())
                
                # 保存闪卡
                conn = get_db()
                cur = conn.cursor()
                now = datetime.now().isoformat()
                next_review = now.split('T')[0]
                for card in cards:
                    fid = str(uuid.uuid4())
                    cur.execute(
                        "INSERT INTO flashcards (id, note_id, subject_id, front, back, next_review, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (fid, note_id, note.get('subject_id'), card['front'], card['back'], next_review, now)
                    )
                conn.commit()
                conn.close()
                
                log_action('generate_flashcards', f"为笔记《{note['title']}》生成了{len(cards)}张闪卡")
                return jsonify({'success': True, 'count': len(cards)})
        except json.JSONDecodeError:
            pass
    
    return jsonify({'success': False, 'error': 'AI服务暂时不可用，请检查API配置'})

@app.route('/api/note/<note_id>/generate-quiz', methods=['POST'])
def generate_quiz(note_id):
    """AI根据笔记生成练习题"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    note = dict(cur.fetchone())
    conn.close()
    
    prompt = f"""请根据以下学习笔记，生成5道练习题，包括选择题和简答题。

笔记内容：
{note['title']}
{note['content']}

请用以下JSON格式回复：
[
  {{"type": "choice", "question": "题目", "options": ["A选项", "B选项", "C选项", "D选项"], "answer": "正确答案"}},
  {{"type": "short", "question": "简答题题目", "answer": "参考答案"}}
]
只回复JSON：
"""
    
    result = call_ai(prompt, system_prompt="你是一个学习助手，根据笔记内容生成高质量练习题。")
    
    if result:
        try:
            match = re.search(r'\[.*\]', result, re.DOTALL)
            if match:
                questions = json.loads(match.group())
                # 存入session用于后续答题
                session['pending_quiz'] = questions
                return jsonify({'success': True, 'questions': questions})
        except json.JSONDecodeError:
            pass
    
    return jsonify({'success': False, 'error': 'AI服务暂时不可用，请检查API配置'})

@app.route('/quiz')
def quiz_page():
    """练习题页面"""
    questions = session.get('pending_quiz', [])
    note_title = request.args.get('title', '练习题')
    return render_template('quiz.html', questions=questions, note_title=note_title)

@app.route('/review')
def review_page():
    """复习页面 - 间隔重复"""
    conn = get_db()
    cur = conn.cursor()
    today = datetime.now().date().isoformat()
    
    # 获取今日待复习的闪卡
    cur.execute("""
        SELECT f.*, n.title as note_title, s.name as subject_name
        FROM flashcards f
        LEFT JOIN notes n ON f.note_id = n.id
        LEFT JOIN subjects s ON f.subject_id = s.id
        WHERE date(f.next_review) <= ?
        ORDER BY f.next_review ASC
    """, (today,))
    cards = [dict(row) for row in cur.fetchall()]
    
    total_due = len(cards)
    conn.close()
    
    return render_template('review.html', cards=cards, total_due=total_due)

@app.route('/api/flashcard/<card_id>/review', methods=['POST'])
def review_flashcard(card_id):
    """提交闪卡复习结果"""
    data = request.get_json()
    rating = int(data.get('rating', 3))  # 1-5评分
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM flashcards WHERE id = ?", (card_id,))
    card = dict(cur.fetchone())
    conn.close()
    
    if not card:
        return jsonify({'success': False, 'error': '闪卡不存在'})
    
    # SM-2算法更新
    quality = quality_from_rating(rating)
    new_ef, new_interval, new_rep = sm2_algorithm(
        quality, card['ease_factor'], card['interval_days'], card['repetitions']
    )
    
    # 计算下次复习日期
    next_date = datetime.now() + timedelta(days=new_interval)
    next_review = next_date.date().isoformat()
    
    # 更新闪卡
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE flashcards SET ease_factor=?, interval_days=?, repetitions=?, next_review=? WHERE id=?",
        (new_ef, new_interval, new_rep, next_review, card_id)
    )
    
    # 记录复习
    log_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO review_logs (id, flashcard_id, quality, reviewed_at) VALUES (?, ?, ?, ?)",
        (log_id, card_id, quality, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    
    log_action('review', f"复习闪卡: {card['front'][:30]}... 评分{rating}")
    
    return jsonify({
        'success': True,
        'next_review': next_review,
        'interval': new_interval,
        'message': f"已记住！{new_interval}天后再复习 🎉" if new_interval > 1 else "继续加油，明天再复习！💪"
    })

@app.route('/flashcards')
def flashcards_page():
    """闪卡管理页面"""
    conn = get_db()
    cur = conn.cursor()
    
    subject_id = request.args.get('subject', '')
    query = '''
        SELECT f.*, n.title as note_title, s.name as subject_name, s.color
        FROM flashcards f
        LEFT JOIN notes n ON f.note_id = n.id
        LEFT JOIN subjects s ON f.subject_id = s.id
        WHERE 1=1
    '''
    params = []
    if subject_id:
        query += " AND f.subject_id = ?"
        params.append(subject_id)
    query += " ORDER BY f.next_review ASC"
    
    cur.execute(query, params)
    flashcards = [dict(row) for row in cur.fetchall()]
    
    cur.execute("SELECT * FROM subjects ORDER BY name")
    subjects = [dict(row) for row in cur.fetchall()]
    conn.close()
    
    return render_template('flashcards.html', flashcards=flashcards, subjects=subjects, current_subject=subject_id)

@app.route('/flashcard/new', methods=['GET', 'POST'])
def flashcard_new():
    """新建闪卡"""
    if request.method == 'POST':
        data = request.get_json()
        fid = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO flashcards (id, subject_id, front, back, next_review, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (fid, data.get('subject_id'), data['front'], data['back'], now.split('T')[0], now)
        )
        conn.commit()
        conn.close()
        
        log_action('create_flashcard', f"新建闪卡: {data['front'][:30]}")
        return jsonify({'success': True, 'id': fid})
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM subjects ORDER BY name")
    subjects = [dict(row) for row in cur.fetchall()]
    conn.close()
    return render_template('flashcard_edit.html', flashcard=None, subjects=subjects)

@app.route('/flashcard/<card_id>/delete', methods=['POST'])
def flashcard_delete(card_id):
    """删除闪卡"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM flashcards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()
    log_action('delete_flashcard', f"删除闪卡 ID:{card_id}")
    return jsonify({'success': True})

@app.route('/ask', methods=['GET', 'POST'])
def ask_page():
    """AI问答页面"""
    if request.method == 'POST':
        question = request.get_json().get('question', '').strip()
        if not question:
            return jsonify({'success': False, 'error': '问题不能为空'})
        
        # 获取相关笔记作为上下文
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM notes ORDER BY updated_at DESC LIMIT 5")
        notes = [dict(row) for row in cur.fetchall()]
        conn.close()
        
        context = ""
        if notes:
            context = "参考笔记：\n" + "\n---\n".join([
                f"《{n['title']}》\n{n['content'][:500]}" 
                for n in notes if n['content']
            ])
        
        prompt = f"""{context}

学生问题：{question}

请用友好、鼓励的方式回答问题。如果涉及到计算或推导，请逐步展示。如果问题超出范围，可以诚实说明。
"""
        
        system_prompt = """你是一个热情、耐心的AI学习伙伴。你的任务是：
1. 用通俗易懂的语言解释概念
2. 如果是解题，要逐步推导
3. 适当举例子帮助理解
4. 鼓励学生继续探索
5. 如果不确定，诚实说明"""
        
        answer = call_ai(prompt, system_prompt=system_prompt)
        
        if answer:
            log_action('ask', f"提问: {question[:50]}")
            return jsonify({'success': True, 'answer': answer})
        else:
            return jsonify({'success': False, 'error': 'AI服务暂时不可用，请检查API配置（支持SiliconFlow/DeepSeek/OpenAI）'})
    
    return render_template('ask.html')

@app.route('/api/subject', methods=['POST'])
def create_subject():
    """创建科目"""
    data = request.get_json()
    sid = data.get('id', hashlib.md5(data['name'].encode()).hexdigest()[:8])
    now = datetime.now().isoformat()
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO subjects (id, name, color, created_at) VALUES (?, ?, ?, ?)",
        (sid, data['name'], data.get('color', '#4CAF50'), now)
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': sid})

def log_action(action, detail):
    """记录学习行为"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO study_logs (id, action, detail, created_at) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), action, detail, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

# ==================== 启动 ====================

@app.template_filter('datetime_format')
def datetime_format(value):
    """格式化日期时间"""
    if not value:
        return ''
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime('%m-%d %H:%M')
    except:
        return value

@app.template_filter('date_format')
def date_format(value):
    """格式化日期"""
    if not value:
        return ''
    try:
        d = datetime.fromisoformat(value).date()
        today = datetime.now().date()
        if d == today:
            return '今天'
        elif d == today + timedelta(days=1):
            return '明天'
        elif d == today - timedelta(days=1):
            return '昨天'
        return d.strftime('%m-%d')
    except:
        return value

if __name__ == '__main__':
    init_db()
    print(f"✨ AI自习伙伴 启动中... http://localhost:{PORT}")
    print(f"📚 间隔重复 + AI问答 + 笔记管理")
    app.run(host='0.0.0.0', port=PORT, debug=True)
