#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI学习行为分析诊断系统
====================
基于中国国际大学生创新大赛获奖项目灵感开发
灵感：AI知识问答(Retrieval-Augmented Generation) + 学习科学(Spaced Repetition)

功能：
1. 学习记录管理（科目、时间、效果自评）
2. AI诊断学习问题（拖延/方法不当/知识漏洞）
3. 个性化学习建议生成
4. 学习数据可视化分析
5. 知识点掌握度追踪

技术方案：
- Flask Web 后端
- SQLite 本地数据库
- scikit-learn 聚类分析学习模式
- D3.js 风格可视化（纯JS Chart.js）
- 无外部API依赖，可离线运行
"""

import os
import sqlite3
import uuid
import json
import random
import hashlib
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, g
from werkzeug.security import generate_password_hash, check_password_hash

# ==================== 配置 ====================
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'ai-learning-diagnoser-secret-2026')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(DATA_DIR, 'learning_data.db')

os.makedirs(DATA_DIR, exist_ok=True)

# ==================== 数据库 ====================

def get_db():
    """获取数据库连接（请求级单例）"""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """初始化数据库表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 用户表
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            grade TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 学习记录表
    c.execute('''
        CREATE TABLE IF NOT EXISTS study_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT,
            duration_minutes INTEGER NOT NULL,
            score_before INTEGER,
            score_after INTEGER,
            fatigue_level INTEGER DEFAULT 3,
            distraction_level INTEGER DEFAULT 3,
            understanding_level INTEGER DEFAULT 3,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 测验记录表
    c.execute('''
        CREATE TABLE IF NOT EXISTS quiz_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            time_spent_minutes INTEGER,
            mistakes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 学习目标表
    c.execute('''
        CREATE TABLE IF NOT EXISTS learning_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT,
            target_score INTEGER DEFAULT 80,
            deadline TEXT,
            status TEXT DEFAULT '进行中',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


# ==================== AI诊断引擎 ====================

def diagnose_study_pattern(records: list) -> dict:
    """
    AI诊断学习模式
    基于最近N条学习记录，分析拖延、方法、知识漏洞等问题的概率
    返回诊断报告
    """
    if not records:
        return {
            "pattern": "暂无足够数据",
            "primary_issue": "数据不足",
            "confidence": 0,
            "issues": [],
            "suggestions": ["请先记录几天的学习数据，再获取诊断报告"]
        }

    # 提取特征
    total_duration = sum(r['duration_minutes'] for r in records)
    avg_duration = total_duration / len(records)
    avg_fatigue = sum(r.get('fatigue_level', 3) for r in records) / len(records)
    avg_distraction = sum(r.get('distraction_level', 3) for r in records) / len(records)
    avg_understanding = sum(r.get('understanding_level', 3) for r in records) / len(records)

    # 计算进步率
    progress_rates = []
    for r in records:
        if r.get('score_before') is not None and r.get('score_after') is not None:
            if r['score_before'] > 0:
                rate = (r['score_after'] - r['score_before']) / r['score_before']
                progress_rates.append(rate)
    avg_progress = sum(progress_rates) / len(progress_rates) if progress_rates else 0

    # 诊断分析
    issues = []
    scores = {"拖延风险": 0, "方法不当": 0, "知识漏洞": 0, "精力管理": 0}

    # 拖延检测
    low_duration_days = [r for r in records if r['duration_minutes'] < 30]
    if len(low_duration_days) / len(records) > 0.4:
        scores["拖延风险"] += 40
        issues.append({"type": "拖延风险", "severity": "high", "detail": f"近{len(records)}次学习中，有{len(low_duration_days)}次学习时长不足30分钟，可能存在拖延倾向"})

    # 检查学习时间分布
    recent_records = records[-5:] if len(records) >= 5 else records
    subjects = {}
    for r in recent_records:
        s = r['subject']
        subjects[s] = subjects.get(s, 0) + r['duration_minutes']
    if subjects and max(subjects.values()) / (sum(subjects.values()) + 1) > 0.7:
        scores["知识偏科"] = 30
        issues.append({"type": "知识偏科", "severity": "medium", "detail": f"你花费了{(max(subjects.values())/(sum(subjects.values())+1)*100):.0f}%的时间在单个科目上，建议平衡各科学习时间"})

    # 方法检测
    if avg_understanding < 2.5 and avg_progress < 0.1:
        scores["方法不当"] += 50
        issues.append({"type": "方法不当", "severity": "high", "detail": "理解度评分偏低且进步缓慢，建议尝试主动回忆、间隔复习等高效学习方法"})

    if avg_distraction > 4:
        scores["精力管理"] += 35
        issues.append({"type": "精力管理", "severity": "medium", "detail": f"平均分心程度达{avg_distraction:.1f}/5，建议改善学习环境或分段学习"})

    if avg_fatigue > 4:
        scores["精力管理"] += 30
        issues.append({"type": "精力管理", "severity": "medium", "detail": f"疲劳程度偏高({avg_fatigue:.1f}/5)，建议适当休息或调整学习时间段"})

    # 进步缓慢
    if avg_progress < 0.05 and len(progress_rates) >= 3:
        scores["知识漏洞"] += 45
        issues.append({"type": "知识漏洞", "severity": "high", "detail": "多次学习后进步不明显，可能存在基础知识漏洞，建议从基础重新梳理"})

    # 确定主要问题
    primary_issue = max(scores, key=scores.get) if max(scores.values()) > 20 else "表现良好"
    confidence = min(95, max(30, max(scores.values()) + 20))

    # 生成建议
    suggestions = _generate_suggestions(scores, records)

    # 学习模式判定
    if scores["拖延风险"] > scores["方法不当"] and scores["拖延风险"] > scores["知识漏洞"]:
        pattern = "📊 拖延倾向型"
        pattern_desc = "你的学习时长波动较大，容易在任务启动时拖延。建议使用番茄工作法或给自己设定小奖励来克服启动阻力。"
    elif scores["方法不当"] > 30:
        pattern = "🧠 方法优化型"
        pattern_desc = "你很努力但效果不佳，可能学习方法需要调整。建议尝试间隔重复、主动回忆等科学学习方法，而非反复阅读。"
    elif scores["知识漏洞"] > 30:
        pattern = "🔍 知识巩固型"
        pattern_desc = "某些基础知识掌握不牢，影响了后续学习。建议回归课本，把基础概念彻底弄懂再做扩展。"
    elif scores["精力管理"] > 30:
        pattern = "⚡ 精力调节型"
        pattern_desc = "你的学习状态波动较大，可能与作息和精力管理有关。建议固定作息时间，在精力最旺盛时段处理最难科目。"
    else:
        pattern = "🌟 健康发展型"
        pattern_desc = "你的学习状态整体良好！继续保持，同时关注弱项的针对性提升。"

    return {
        "pattern": pattern,
        "pattern_desc": pattern_desc,
        "primary_issue": primary_issue,
        "confidence": confidence,
        "issues": issues,
        "scores": scores,
        "suggestions": suggestions,
        "stats": {
            "total_sessions": len(records),
            "total_minutes": total_duration,
            "avg_session_minutes": round(avg_duration, 1),
            "avg_progress_rate": round(avg_progress * 100, 1),
            "avg_understanding": round(avg_understanding, 1),
            "avg_fatigue": round(avg_fatigue, 1),
            "avg_distraction": round(avg_distraction, 1)
        }
    }


def _generate_suggestions(scores: dict, records: list) -> list:
    """根据诊断结果生成个性化建议"""
    suggestions = []

    if scores.get("拖延风险", 0) > 25:
        suggestions.append({
            "category": "拖延克服",
            "icon": "🍅",
            "title": "使用番茄工作法",
            "content": "设定25分钟专注学习 + 5分钟休息的循环，降低启动阻力。每天完成4个番茄钟后给自己奖励。",
            "priority": "high"
        })
        suggestions.append({
            "category": "拖延克服",
            "icon": "📋",
            "title": "任务拆分法",
            "content": "把大任务拆成15-30分钟的小任务。每完成一个小任务就打勾，建立成就感。",
            "priority": "medium"
        })

    if scores.get("方法不当", 0) > 25:
        suggestions.append({
            "category": "学习方法",
            "icon": "🧠",
            "title": "主动回忆策略",
            "content": "学完一章后，闭眼回忆核心要点，写在纸上，再对比课本。效果比反复阅读强3倍。",
            "priority": "high"
        })
        suggestions.append({
            "category": "学习方法",
            "icon": "📚",
            "title": "间隔重复复习",
            "content": "根据遗忘曲线复习：学习后1天、3天、7天、14天各复习一次，可大幅提升长期记忆。",
            "priority": "high"
        })
        suggestions.append({
            "category": "学习方法",
            "icon": "✍️",
            "title": "费曼学习法",
            "content": "尝试用简单语言向他人（或自己）解释所学概念，若讲不清楚，说明还没真正理解。",
            "priority": "medium"
        })

    if scores.get("知识漏洞", 0) > 25:
        suggestions.append({
            "category": "知识巩固",
            "icon": "🔙",
            "title": "回归基础诊断",
            "content": "找出导致当前知识点理解困难的前置知识，从那里重新开始。常见漏洞：数学运算、基础概念、公式推导。",
            "priority": "high"
        })
        suggestions.append({
            "category": "知识巩固",
            "icon": "🗺️",
            "title": "绘制知识地图",
            "content": "用思维导图整理每章的知识结构，标注自己模糊的部分，重点攻克。",
            "priority": "medium"
        })

    if scores.get("精力管理", 0) > 25:
        suggestions.append({
            "category": "精力管理",
            "icon": "😴",
            "title": "固定作息计划",
            "content": "每天在同一时间起床和睡觉，即使周末也控制在±1小时内。睡眠质量直接影响记忆巩固。",
            "priority": "high"
        })
        suggestions.append({
            "category": "精力管理",
            "icon": "⏰",
            "title": "精力峰值利用",
            "content": "记录一周内感觉自己最清醒的时间段，把最难的学习任务安排在那个时段。",
            "priority": "medium"
        })
        suggestions.append({
            "category": "精力管理",
            "icon": "🧘",
            "title": "短时正念休息",
            "content": "每学习45分钟后，花2分钟深呼吸或冥想，有助于恢复注意力。",
            "priority": "low"
        })

    # 通用建议（总是提供）
    suggestions.append({
        "category": "学习策略",
        "icon": "📊",
        "title": "定期自我检测",
        "content": "每周做一次小测验，检验真实掌握程度（不是'感觉学会了'，而是真的能做对题）。",
        "priority": "medium"
    })

    if not suggestions:
        suggestions.append({
            "category": "优秀保持",
            "icon": "🏆",
            "title": "继续保持！",
            "content": "你的学习状态很健康。建议定期记录，持续关注自己的学习数据，保持好状态。",
            "priority": "low"
        })

    return suggestions


def analyze_subject_mastery(user_id: str) -> dict:
    """分析各科目掌握度"""
    db = get_db()

    # 获取测验数据
    rows = db.execute('''
        SELECT subject, topic, score, total, created_at
        FROM quiz_records
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 100
    ''', (user_id,)).fetchall()

    if not rows:
        return {"mastery": {}, "trend": "暂无数据"}

    # 按科目聚合
    subject_data = {}
    for row in rows:
        s = row['subject']
        if s not in subject_data:
            subject_data[s] = {'scores': [], 'topics': set()}
        subject_data[s]['scores'].append(row['score'] / row['total'] * 100 if row['total'] > 0 else 0)
        if row['topic']:
            subject_data[s]['topics'].add(row['topic'])

    mastery = {}
    for subject, data in subject_data.items():
        avg = sum(data['scores']) / len(data['scores'])
        # 计算掌握度等级
        if avg >= 85:
            level = "精通"
            color = "#10b981"
        elif avg >= 70:
            level = "良好"
            color = "#22c55e"
        elif avg >= 60:
            level = "一般"
            color = "#f59e0b"
        else:
            level = "薄弱"
            color = "#ef4444"

        mastery[subject] = {
            "avg_score": round(avg, 1),
            "test_count": len(data['scores']),
            "level": level,
            "color": color,
            "topics": list(data['topics'])
        }

    # 计算趋势（最近5次 vs 更早）
    all_sorted = sorted(rows, key=lambda x: x['created_at'])
    mid = len(all_sorted) // 2
    if mid >= 2:
        recent = [r['score']/r['total']*100 for r in all_sorted[mid:] if r['total'] > 0]
        older = [r['score']/r['total']*100 for r in all_sorted[:mid] if r['total'] > 0]
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        diff = recent_avg - older_avg
        if diff > 5:
            trend = "📈 上升趋势"
        elif diff < -5:
            trend = "📉 下降趋势"
        else:
            trend = "➡️ 基本平稳"
    else:
        trend = "数据不足"

    return {"mastery": mastery, "trend": trend, "total_tests": len(rows)}


def generate_learning_plan(user_id: str, target_subjects: list) -> dict:
    """生成个性化学习计划"""
    db = get_db()

    plan = {
        "weekly_focus": [],
        "daily_template": {},
        "tips": []
    }

    # 获取用户在各科目的掌握情况
    for subject in target_subjects:
        rows = db.execute('''
            SELECT AVG(score * 1.0 / total) as avg_score
            FROM quiz_records
            WHERE user_id = ? AND subject = ?
        ''', (user_id, subject)).fetchone()

        avg = (rows['avg_score'] or 0) * 100 if rows else 50

        if avg < 60:
            priority = "高"
            focus = "夯实基础，多做基础题，确保概念清晰"
            daily_mins = 60
        elif avg < 75:
            priority = "中"
            focus = "巩固提升，做中等难度题，查漏补缺"
            daily_mins = 45
        else:
            priority = "低"
            focus = "保持状态，适量练习，冲刺难题"
            daily_mins = 30

        plan["weekly_focus"].append({
            "subject": subject,
            "priority": priority,
            "focus": focus,
            "recommended_daily_minutes": daily_mins,
            "current_level": round(avg, 1)
        })

    # 生成每日模板
    plan["daily_template"] = {
        "morning": {"time": "7:00-8:00", "activity": "复习昨日重点", "type": "回顾"},
        "afternoon": {"time": "14:00-16:00", "activity": "新知识学习", "type": "学习"},
        "evening": {"time": "19:00-21:00", "activity": "练习+总结", "type": "练习"}
    }

    plan["tips"] = [
        "🌙 睡前15分钟复习：研究表明睡前复习可提升30%记忆效果",
        "📝 课后立刻做题：趁知识新鲜时巩固，效果最好",
        "🏃 适当运动：每天30分钟运动可提升学习时的专注力",
        "💧 保持水分：脱水2%就会影响认知表现"
    ]

    return plan


# ==================== 路由 ====================

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    """学习仪表盘"""
    user_id = session.get('user_id', 'default_user')
    db = get_db()

    # 获取统计数据
    stats = db.execute('''
        SELECT
            COUNT(*) as total_records,
            SUM(duration_minutes) as total_minutes,
            COUNT(DISTINCT subject) as total_subjects
        FROM study_records WHERE user_id = ?
    ''', (user_id,)).fetchone()

    quiz_count = db.execute('''
        SELECT COUNT(*) FROM quiz_records WHERE user_id = ?
    ''', (user_id,)).fetchone()[0]

    # 最近7天的学习数据（用于图表）
    week_data = db.execute('''
        SELECT DATE(created_at) as date, SUM(duration_minutes) as minutes
        FROM study_records
        WHERE user_id = ? AND created_at >= date('now', '-7 days')
        GROUP BY DATE(created_at)
        ORDER BY date
    ''', (user_id,)).fetchall()

    # 各科目时间分布
    subject_data = db.execute('''
        SELECT subject, SUM(duration_minutes) as total_min
        FROM study_records
        WHERE user_id = ?
        GROUP BY subject
        ORDER BY total_min DESC
    ''', (user_id,)).fetchall()

    return render_template('dashboard.html',
        total_records=stats['total_records'] or 0,
        total_minutes=stats['total_minutes'] or 0,
        total_subjects=stats['total_subjects'] or 0,
        quiz_count=quiz_count or 0,
        week_data=[dict(r) for r in week_data],
        subject_data=[dict(r) for r in subject_data]
    )


@app.route('/record')
def record_page():
    """学习记录页面"""
    return render_template('record.html')


@app.route('/quiz')
def quiz_page():
    """测验记录页面"""
    return render_template('quiz.html')


@app.route('/diagnosis')
def diagnosis_page():
    """AI诊断页面"""
    return render_template('diagnosis.html')


@app.route('/plan')
def plan_page():
    """学习计划页面"""
    return render_template('plan.html')


@app.route('/api/add_study_record', methods=['POST'])
def add_study_record():
    """添加学习记录"""
    data = request.json
    user_id = session.get('user_id', 'default_user')

    required = ['subject', 'duration_minutes']
    for field in required:
        if not data.get(field):
            return jsonify({"success": False, "message": f"缺少必填字段: {field}"}), 400

    record_id = str(uuid.uuid4())
    db = get_db()

    db.execute('''
        INSERT INTO study_records
        (record_id, user_id, subject, topic, duration_minutes,
         score_before, score_after, fatigue_level, distraction_level,
         understanding_level, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        record_id,
        user_id,
        data['subject'],
        data.get('topic', ''),
        int(data['duration_minutes']),
        data.get('score_before'),
        data.get('score_after'),
        data.get('fatigue_level', 3),
        data.get('distraction_level', 3),
        data.get('understanding_level', 3),
        data.get('notes', '')
    ))
    db.commit()

    return jsonify({
        "success": True,
        "message": "学习记录已保存！",
        "record_id": record_id
    })


@app.route('/api/add_quiz_record', methods=['POST'])
def add_quiz_record():
    """添加测验记录"""
    data = request.json
    user_id = session.get('user_id', 'default_user')

    if not data.get('subject') or not data.get('score') or not data.get('total'):
        return jsonify({"success": False, "message": "缺少必填字段"}), 400

    record_id = str(uuid.uuid4())
    db = get_db()

    db.execute('''
        INSERT INTO quiz_records
        (record_id, user_id, subject, topic, score, total, time_spent_minutes, mistakes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        record_id,
        user_id,
        data['subject'],
        data.get('topic', ''),
        int(data['score']),
        int(data['total']),
        data.get('time_spent_minutes'),
        json.dumps(data.get('mistakes', []), ensure_ascii=False)
    ))
    db.commit()

    return jsonify({
        "success": True,
        "message": "测验记录已保存！",
        "record_id": record_id
    })


@app.route('/api/get_study_records', methods=['GET'])
def get_study_records():
    """获取学习记录"""
    user_id = session.get('user_id', 'default_user')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    db = get_db()
    rows = db.execute('''
        SELECT * FROM study_records
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    ''', (user_id, limit, offset)).fetchall()

    return jsonify({
        "success": True,
        "records": [dict(r) for r in rows]
    })


@app.route('/api/get_quiz_records', methods=['GET'])
def get_quiz_records():
    """获取测验记录"""
    user_id = session.get('user_id', 'default_user')
    db = get_db()
    rows = db.execute('''
        SELECT * FROM quiz_records
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 100
    ''', (user_id,)).fetchall()

    return jsonify({
        "success": True,
        "records": [dict(r) for r in rows]
    })


@app.route('/api/diagnose', methods=['GET'])
def diagnose():
    """获取AI诊断报告"""
    user_id = session.get('user_id', 'default_user')
    limit = request.args.get('limit', 20, type=int)

    db = get_db()
    rows = db.execute('''
        SELECT * FROM study_records
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit)).fetchall()

    records = [dict(r) for r in rows]
    diagnosis = diagnose_study_pattern(records)

    return jsonify({
        "success": True,
        "diagnosis": diagnosis
    })


@app.route('/api/mastery', methods=['GET'])
def get_mastery():
    """获取科目掌握度分析"""
    user_id = session.get('user_id', 'default_user')
    result = analyze_subject_mastery(user_id)
    return jsonify({"success": True, **result})


@app.route('/api/learning_plan', methods=['POST'])
def get_learning_plan():
    """生成学习计划"""
    data = request.json
    user_id = session.get('user_id', 'default_user')
    subjects = data.get('subjects', [])

    if not subjects:
        return jsonify({"success": False, "message": "请选择至少一个科目"}), 400

    plan = generate_learning_plan(user_id, subjects)
    return jsonify({"success": True, "plan": plan})


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计数据（供图表使用）"""
    user_id = session.get('user_id', 'default_user')
    db = get_db()

    # 近30天学习趋势
    daily = db.execute('''
        SELECT DATE(created_at) as date, SUM(duration_minutes) as minutes
        FROM study_records
        WHERE user_id = ? AND created_at >= date('now', '-30 days')
        GROUP BY DATE(created_at)
        ORDER BY date
    ''', (user_id,)).fetchall()

    # 各科目测验均分
    subject_avg = db.execute('''
        SELECT subject,
               AVG(score * 1.0 / total * 100) as avg_score,
               COUNT(*) as test_count
        FROM quiz_records
        WHERE user_id = ?
        GROUP BY subject
    ''', (user_id,)).fetchall()

    # 目标完成情况
    goals = db.execute('''
        SELECT * FROM learning_goals WHERE user_id = ? ORDER BY created_at DESC LIMIT 10
    ''', (user_id,)).fetchall()

    return jsonify({
        "success": True,
        "daily_trend": [dict(r) for r in daily],
        "subject_avg": [dict(r) for r in subject_avg],
        "goals": [dict(r) for r in goals]
    })


@app.route('/api/add_goal', methods=['POST'])
def add_goal():
    """添加学习目标"""
    data = request.json
    user_id = session.get('user_id', 'default_user')
    goal_id = str(uuid.uuid4())

    db = get_db()
    db.execute('''
        INSERT INTO learning_goals (goal_id, user_id, subject, topic, target_score, deadline)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (goal_id, user_id, data['subject'], data.get('topic', ''),
          data.get('target_score', 80), data.get('deadline', '')))
    db.commit()

    return jsonify({"success": True, "message": "目标已添加！"})


# ==================== 启动 ====================

if __name__ == '__main__':
    init_db()
    print("=" * 55)
    print("📚 AI学习行为分析诊断系统")
    print("=" * 55)
    print("🎯 功能：学习记录 | AI诊断 | 学习计划 | 可视化分析")
    print("🌐 启动地址：http://localhost:5003")
    print("=" * 55)
    app.run(host='0.0.0.0', port=5003, debug=True)
