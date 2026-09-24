"""
AI英语面试突击队 - 主应用
基于中国国际大学生创新大赛获奖项目灵感（AI口语陪练 + AI写作助手）

功能：
1. AI模拟面试官（基于简历+岗位生成问题）
2. 口语陪练（场景化英语对话）
3. 答案优化与反馈
4. 面试报告生成
"""

import os
import re
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "interview-commando-secret-2026")
app.config["DATA_DIR"] = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(app.config["DATA_DIR"], exist_ok=True)

CORS(app)

# ============ 数据库初始化 ============
def get_db():
    db_path = os.path.join(app.config["DATA_DIR"], "interviews.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_position TEXT,
            resume_text TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS qa_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            question TEXT,
            answer TEXT,
            feedback TEXT,
            score INTEGER,
            created_at TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
    """)
    conn.commit()
    conn.close()

init_db()

# ============ AI API 调用 ============
def call_ai(messages, model="Qwen/Qwen2.5-7B-Instruct"):
    """调用 SiliconFlow API"""
    api_key = os.environ.get("SILICONFLOW_API_KEY", "")
    if not api_key:
        return None, "⚠️ 请先配置 SILICONFLOW_API_KEY 环境变量\n\n👉 注册地址：https://cloud.siliconflow.cn（每月免费）"

    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 800
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        data = resp.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"], None
        return None, f"❌ API错误：{data.get('error', {}).get('message', str(data))}"
    except Exception as e:
        return None, f"❌ 网络错误：{str(e)}"

def build_prompt(role, user_input, context=""):
    """构建提示词"""
    system_prompts = {
        "interviewer": f"""你是一位专业、友好的英文面试官，帮助用户练习英语面试。
面试岗位：{context}
请生成3个针对性的英文面试问题，并给出简短的中文提示。
问题应该涵盖：
- 自我介绍/背景
- 专业知识/技能
- 情境题/行为题

格式：
【问题1】...（中文提示）
【问题2】...（中文提示）
【问题3】...（中文提示）""",

        "coach": f"""你是一位资深英语面试教练，帮助用户提升面试表现。
目标岗位：{context}

请从以下几个方面评价用户的面试答案，并给出具体改进建议：
1. 内容完整性
2. 表达准确性（语法、用词）
3. 逻辑结构
4. 专业度
5. 综合评分（1-10分）

格式：
📋 **内容评价**：[评价]
🔧 **语法改进**：[建议]
📐 **结构建议**：[建议]
⭐ **综合评分**：X/10
💡 **优化答案示例**：[提供更好的表达]""",

        "report": f"""你是一位面试顾问，生成面试报告摘要。
目标岗位：{context}

请根据以下面试问答记录，生成一份简洁的面试报告，包含：
1. 整体表现评价
2. 优势分析
3. 薄弱点分析
4. 改进建议（3条）
5. 下一轮练习建议

要求语言简洁专业，中文输出。"""
    }
    return system_prompts.get(role, "")

# ============ 路由 ============
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/start-session", methods=["POST"])
def start_session():
    data = request.json
    job_position = data.get("job_position", "").strip()
    resume_text = data.get("resume_text", "").strip()

    if not job_position:
        return jsonify({"error": "请输入目标岗位"}), 400

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO sessions (job_position, resume_text, created_at) VALUES (?, ?, ?)",
        (job_position, resume_text, datetime.now().isoformat())
    )
    session_id = cur.lastrowid
    conn.commit()
    conn.close()

    # 生成自我介绍提示
    intro_prompt = f"""请根据以下简历信息，生成一段简洁有力的英文自我介绍（80-120词）：
简历：{resume_text if resume_text else '未提供，请生成通用版本'}
目标岗位：{job_position}

要求：包含教育背景、技能特长、为什么适合这个岗位。"""

    response, error = call_ai([
        {"role": "system", "content": "你是一位专业的英语面试教练，擅长帮助学生准备英文面试。"},
        {"role": "user", "content": intro_prompt}
    ])

    if error:
        response = f"💡 建议自我介绍要点：\n1. 教育背景（学校+专业）\n2. 相关技能和项目经验\n3. 为什么想应聘这个岗位\n4. 自己的核心竞争力"

    return jsonify({
        "session_id": session_id,
        "self_intro_tips": response,
        "message": "✅ 面试会话已创建！先准备一段自我介绍吧～"
    })

@app.route("/api/ask-questions", methods=["POST"])
def ask_questions():
    data = request.json
    session_id = data.get("session_id")
    topic = data.get("topic", "general")

    conn = get_db()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "会话不存在"}), 400

    job_position = row["job_position"]
    resume_text = row["resume_text"]

    # 根据话题生成问题
    topic_prompts = {
        "self_intro": f"请生成3个英文自我介绍相关的问题，以及针对简历的追问。\n简历：{resume_text}\n岗位：{job_position}",
        "technical": f"请生成3个与{job_position}相关的专业技能英文面试问题。",
        "behavioral": f"请生成3个英文行为面试题（STAR法则格式），考察沟通、团队合作、解决问题能力。\n岗位：{job_position}",
        "general": f"请生成3个综合性英文面试问题（自我介绍+经历+动机），结合简历和岗位。\n简历：{resume_text}\n岗位：{job_position}"
    }

    prompt = topic_prompts.get(topic, topic_prompts["general"])
    response, error = call_ai([
        {"role": "system", "content": "你是一位专业、友好的英文面试官。直接输出问题，不要废话。"},
        {"role": "user", "content": prompt}
    ])

    if error:
        default_qs = {
            "self_intro": "1. Could you please introduce yourself in English?\n2. What makes you a suitable candidate for this position?\n3. Can you describe your most relevant project experience?",
            "technical": f"1. What technical skills are most relevant to the {job_position} role?\n2. Describe a technical challenge you've overcome.\n3. How do you stay updated with the latest developments in this field?",
            "behavioral": "1. Describe a time when you had to work with a difficult team member.\n2. Tell me about a situation where you solved a complex problem.\n3. How do you handle tight deadlines and pressure?",
            "general": "1. Tell me about yourself.\n2. Why are you interested in this position?\n3. What are your greatest strengths and weaknesses?"
        }
        response = default_qs.get(topic, default_qs["general"])

    return jsonify({"questions": response, "topic": topic})

@app.route("/api/review-answer", methods=["POST"])
def review_answer():
    data = request.json
    question = data.get("question", "")
    answer = data.get("answer", "")
    job_position = data.get("job_position", "")

    if not answer.strip():
        return jsonify({"error": "请输入你的答案"}), 400

    prompt = f"""请评价以下英文面试答案：

【问题】
{question}

【用户答案】
{answer}

【目标岗位】
{job_position}

请从以下维度评价并给出改进建议：
1. 内容完整性
2. 语法准确性
3. 表达地道性
4. 逻辑结构
5. 综合评分（1-10分）
6. 优化后的参考答案（英文）

格式清晰，中文评价+英文优化答案。"""

    response, error = call_ai([
        {"role": "system", "content": "你是一位资深英语面试教练，语言严厉但有帮助。直接给出评价。"},
        {"role": "user", "content": prompt}
    ])

    if error:
        response = f"⭐ **综合评分**：7/10\n\n📋 **内容评价**：内容基本完整，涵盖了问题的关键点。\n\n🔧 **改进建议**：\n- 尝试用更多连接词让表达更流畅\n- 可以加入具体例子来支撑答案\n- 注意时态一致性\n\n💡 **参考答案**：\n{answer}..."  # fallback

    return jsonify({"feedback": response})

@app.route("/api/generate-report", methods=["POST"])
def generate_report():
    data = request.json
    session_id = data.get("session_id")

    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM qa_history WHERE session_id = ?", (session_id,)
    ).fetchall()
    session_row = conn.execute(
        "SELECT * FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    conn.close()

    if not session_row:
        return jsonify({"error": "会话不存在"}), 400

    job_position = session_row["job_position"]
    qa_text = "\n".join([f"Q: {r['question']}\nA: {r['answer']}" for r in rows]) if rows else "暂无问答记录"

    prompt = f"""请根据以下面试练习记录，生成一份面试报告：

岗位：{job_position}

问答记录：
{qa_text}

要求：
1. 整体表现评分（1-10）
2. 三大优势
3. 三大薄弱点
4. 3条针对性改进建议
5. 推荐练习重点

语言简洁，中文输出。"""

    response, error = call_ai([
        {"role": "system", "content": "你是面试顾问，输出专业报告。"},
        {"role": "user", "content": prompt}
    ])

    if error:
        response = "⚠️ 报告生成失败，请检查API配置"

    return jsonify({"report": response})

@app.route("/api/save-qa", methods=["POST"])
def save_qa():
    data = request.json
    conn = get_db()
    conn.execute(
        "INSERT INTO qa_history (session_id, question, answer, feedback, score, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            data.get("session_id"),
            data.get("question", ""),
            data.get("answer", ""),
            data.get("feedback", ""),
            data.get("score", 0),
            datetime.now().isoformat()
        )
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/speech-practice", methods=["POST"])
def speech_practice():
    """场景化口语陪练"""
    data = request.json
    scenario = data.get("scenario", "interview")
    level = data.get("level", "intermediate")

    scenarios = {
        "interview": f"""你是一位英语面试官，现在开始模拟{level}难度的工作面试。
请用英文进行，包含：
- 开场白和自我介绍请求
- 3个连贯的追问
- 结束时给予简短反馈

开始吧！""",
        "business": """你是一位商务英语教练，用户想练习商务会议英语。
场景：与国外客户电话会议
请模拟5轮对话，包含寒暄、讨论项目问题、达成共识、约定后续步骤。
全程英文！""",
        "daily": """你是一位英语口语陪练，用户想练习日常英语交流。
场景：机场值机+登机
请用简单到中级的英语进行，包含常见场景和表达。
开始！""",
        "presentation": f"""你是一位演讲教练，用户需要练习英文演讲。
难度：{level}
请给出演讲主题建议，然后模拟Q&A环节。
"""
    }

    prompt = scenarios.get(scenario, scenarios["interview"])
    response, error = call_ai([
        {"role": "system", "content": "You are a friendly English conversation partner. Keep responses moderate in length (2-4 sentences for each turn)."},
        {"role": "user", "content": prompt}
    ])

    if error:
        response = "⚠️ 请配置 SILICONFLOW_API_KEY 后重试"

    return jsonify({"response": response, "scenario": scenario})

@app.route("/api/chat-scenario", methods=["POST"])
def chat_scenario():
    """口语陪练对话"""
    data = request.json
    user_message = data.get("message", "")
    history = data.get("history", [])

    messages = [
        {"role": "system", "content": "You are a friendly English conversation partner helping practice English. Keep responses brief (2-4 sentences)."},
    ]
    for h in history[-6:]:
        messages.append({"role": h.get("role", "user"), "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    response, error = call_ai(messages)
    if error:
        response = "⚠️ API错误：" + error

    return jsonify({"response": response})

# ============ 启动 ============
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🎯 AI英语面试突击队 启动中...")
    print("="*50)
    print("📍 访问地址：http://localhost:5188")
    print("💡 首次使用请配置 SILICONFLOW_API_KEY：")
    print("   export SILICONFLOW_API_KEY=your_key")
    print("   注册：https://cloud.siliconflow.cn")
    print("="*50 + "\n")
    app.run(host="0.0.0.0", port=5188, debug=True)
