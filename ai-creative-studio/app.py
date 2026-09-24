#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI多模态创意工作室 (AI Multimodal Creative Studio)
===============================================
集文档处理、图片生成、写作助手于一体的综合AI创意工具箱

灵感来源：中国国际大学生创新大赛 AI软件类获奖项目技术方案
深言科技"智能信息处理平台"的垂直领域AI应用启发

作者：俞 ✨
"""

import os
import re
import json
import uuid
import hashlib
from datetime import datetime
from functools import wraps

import requests
import yaml
from flask import Flask, render_template, request, jsonify, session, send_file

# ==================== Flask App ====================
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'ai-creative-studio-secret-2026')
PORT = int(os.environ.get('PORT', 5003))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_DIR = os.path.join(DATA_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ==================== AI API 配置 ====================

def load_ai_config():
    """加载AI配置"""
    return {
        'siliconflow': {
            'enabled': bool(os.environ.get('SILICONFLOW_API_KEY', '')),
            'api_key': os.environ.get('SILICONFLOW_API_KEY', ''),
            'base_url': 'https://api.siliconflow.cn/v1',
            'chat_model': os.environ.get('SF_CHAT_MODEL', 'Qwen/Qwen2.5-7B-Instruct'),
            'embed_model': 'BAAI/bge-large-zh-v1.5',
            'image_model': 'stabilityai/stable-diffusion-3-medium',
        },
        'deepseek': {
            'enabled': bool(os.environ.get('DEEPSEEK_API_KEY', '')),
            'api_key': os.environ.get('DEEPSEEK_API_KEY', ''),
            'base_url': 'https://api.deepseek.com/v1',
            'chat_model': 'deepseek-chat',
        },
    }

AI_CONFIG = load_ai_config()

# ==================== AI API 调用 ====================

def chat_complete(prompt, system_prompt=None, model=None, temperature=0.7):
    """通用聊天完成接口"""
    cfg = AI_CONFIG['siliconflow'] if AI_CONFIG['siliconflow']['enabled'] else AI_CONFIG['deepseek']
    if not cfg['enabled']:
        raise Exception("请配置 AI API 密钥！请设置 SILICONFLOW_API_KEY 或 DEEPSEEK_API_KEY 环境变量")

    model = model or cfg.get('chat_model', 'Qwen/Qwen2.5-7B-Instruct')
    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': prompt})

    headers = {
        'Authorization': f'Bearer {cfg["api_key"]}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': 2000
    }
    resp = requests.post(
        f'{cfg["base_url"]}/chat/completions',
        headers=headers, json=payload, timeout=120
    )
    resp.raise_for_status()
    data = resp.json()
    return data['choices'][0]['message']['content']


def get_embedding(text):
    """获取文本embedding"""
    cfg = AI_CONFIG['siliconflow']
    if not cfg['enabled']:
        raise Exception("请配置 SILICONFLOW_API_KEY")

    headers = {
        'Authorization': f'Bearer {cfg["api_key"]}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': cfg['embed_model'],
        'input': text
    }
    resp = requests.post(
        f'{cfg["base_url"]}/embeddings',
        headers=headers, json=payload, timeout=60
    )
    resp.raise_for_status()
    return resp.json()['data'][0]['embedding']


def generate_image(prompt, size='1024x1024'):
    """生成图片（通过 SiliconFlow Flux API）"""
    cfg = AI_CONFIG['siliconflow']
    if not cfg['enabled']:
        raise Exception("请配置 SILICONFLOW_API_KEY")

    headers = {
        'Authorization': f'Bearer {cfg["api_key"]}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': 'stabilityai/stable-diffusion-xl-base-1.0',
        'prompt': prompt,
        'image_size': size,
        'num_inference_steps': 30
    }
    resp = requests.post(
        f'{cfg["base_url"]}/images/generations',
        headers=headers, json=payload, timeout=180
    )
    resp.raise_for_status()
    data = resp.json()
    return data['images'][0]['url']


# ==================== 文档解析 ====================

def parse_txt(content):
    return content

def parse_pdf(file_path):
    try:
        import PyPDF2
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return '\n'.join(page.extract_text() or '' for page in reader.pages)
    except ImportError:
        return "[需要 PyPDF2: pip install PyPDF2]"

def parse_docx(file_path):
    try:
        from docx import Document
        doc = Document(file_path)
        return '\n'.join(p.text for p in doc.paragraphs)
    except ImportError:
        return "[需要 python-docx: pip install python-docx]"

def parse_document(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.txt':
        return parse_txt(open(file_path, 'r', encoding='utf-8').read())
    elif ext == '.pdf':
        return parse_pdf(file_path)
    elif ext in ('.docx', '.doc'):
        return parse_docx(file_path)
    else:
        return f"[不支持格式: {ext}]"


# ==================== AI 工具函数 ====================

def summarize_text(text, max_length=500):
    """AI摘要"""
    prompt = f"""请为以下文章生成简洁准确的摘要，控制在{max_length}字以内：

---
{text[:3000]}
---

摘要："""
    return chat_complete(prompt, system_prompt="你是一个专业的文章摘要助手，擅长提取文章核心内容。")

def extract_keywords(text, top_n=10):
    """提取关键词"""
    prompt = f"""从以下文本中提取{top_n}个最重要的关键词，用逗号分隔：

---
{text[:2000]}
---

关键词："""
    result = chat_complete(prompt, system_prompt="你是一个关键词提取专家。")
    return [k.strip() for k in result.replace('，', ',').split(',') if k.strip()]

def extract_entities(text):
    """提取实体（人物、地点、机构等）"""
    prompt = f"""从以下文本中提取所有实体，并按类型分类：

---
{text[:2000]}
---

请用以下JSON格式返回：
{{"人物": [...], "地点": [...], "机构": [...], "时间": [...]}}"""
    result = chat_complete(prompt, temperature=0.3)
    try:
        import re
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    return {"人物": [], "地点": [], "机构": [], "时间": []}

def generate_mindmap(text):
    """生成思维导图（文本格式）"""
    prompt = f"""根据以下内容，生成一个清晰的思维导图结构。用层级缩进表示：

---
{text[:2000]}
---

格式要求：
- 中心主题在最前面，用 ** 包围
- 子主题用 - 开头，逐层缩进
- 控制在8个主分支以内
- 每个分支3-5个子点

思维导图："""
    return chat_complete(prompt, system_prompt="你是一个思维导图专家，擅长将复杂内容结构化。")

def generate_flashcards(text, count=5):
    """生成闪卡/问答对"""
    prompt = f"""根据以下内容，生成{count}个学习闪卡（问答对）：

---
{text[:2000]}
---

格式要求：
- 每个问答对格式：【问题】xxx 【答案】yyy
- 问题要具体，答案要简洁准确
- 用中文输出

"""
    return chat_complete(prompt, system_prompt="你是一个教育专家，擅长生成学习闪卡。")

def generate_quiz(text, count=5):
    """生成测试题"""
    prompt = f"""根据以下内容，生成{count}道测试题（3个选项，单选）：

---
{text[:2000]}
---

格式要求：
【题目N】问题内容
A. 选项A
B. 选项B
C. 选项C
答案：B

"""
    return chat_complete(prompt, system_prompt="你是一个出题专家，擅长生成高质量测试题。")

def polish_text(text, style="专业"):
    """润色/改写文本"""
    prompt = f"""请将以下文本改写成更加{style}的风格：

---
{text[:1500]}
---

改写后的文本："""
    return chat_complete(prompt, system_prompt=f"你是一个专业的文本改写助手，风格要求：{style}。")

def translate_text(text, target_lang="英文"):
    """翻译文本"""
    prompt = f"""将以下中文文本翻译成{target_lang}，保持原意和风格：

---
{text[:1500]}
---

翻译结果："""
    return chat_complete(prompt, system_prompt="你是一个专业翻译，擅长准确流畅的翻译。")

def creative_writing(topic, genre="故事", length="中等"):
    """创意写作"""
    length_map = {"短": "300字", "中等": "800字", "长": "1500字"}
    target_len = length_map.get(length, "800字")
    prompt = f"""请写一篇{length}的{genre}，主题是：{topic}

要求：
- 原创内容，想象力丰富
- 结构完整，有开头、发展、结尾
- 人物刻画生动
- 用中文写作

"""
    return chat_complete(prompt, system_prompt="你是一个富有想象力的作家，擅长创意写作。", temperature=0.9)

def generate_marketing_copy(product, target="年轻消费者", tone="活泼"):
    """生成营销文案"""
    prompt = f"""为以下产品生成一段{tone}风格的营销文案，目标人群：{target}：

产品介绍：
{product}

要求：
- 突出产品核心卖点
- 吸引目标人群注意
- 有感染力和号召力
- 长度适中（100-200字）

文案："""
    return chat_complete(prompt, system_prompt="你是一个顶级营销文案专家，擅长创作高转化率的文案。", temperature=0.8)

def analyze_resume(text):
    """简历分析"""
    prompt = f"""请分析以下简历，给出详细建议：

---
{text[:2500]}
---

分析维度：
1. 【整体评价】综合评分(1-10)及总体评价
2. 【优势】简历的亮点
3. 【不足】需要改进的地方
4. 【优化建议】具体可操作的改进建议
5. 【面试预测】可能的面试问题

请用中文详细分析："""
    return chat_complete(prompt, system_prompt="你是一个资深HR，擅长简历评估和改进建议。")

def qa_document(question, context):
    """基于文档的问答"""
    prompt = f"""基于以下文档内容，回答用户的问题。

【文档内容】
{context[:3000]}

【用户问题】
{question}

回答要求：
- 只基于文档内容回答，不要编造
- 如果文档中没有相关信息，明确说明
- 引用相关原文

回答："""
    return chat_complete(prompt, system_prompt="你是一个智能文档问答助手，根据给定文档准确回答问题。", temperature=0.3)


# ==================== Flask 路由 ====================

@app.route('/')
def index():
    return render_template('index.html')


# ---- 文档工具 ----

@app.route('/api/summarize', methods=['POST'])
def api_summarize():
    """文档摘要"""
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'})
    try:
        result = summarize_text(text)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/keywords', methods=['POST'])
def api_keywords():
    """关键词提取"""
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'})
    try:
        result = extract_keywords(text)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/entities', methods=['POST'])
def api_entities():
    """实体提取"""
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'})
    try:
        result = extract_entities(text)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/mindmap', methods=['POST'])
def api_mindmap():
    """思维导图生成"""
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'})
    try:
        result = generate_mindmap(text)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/flashcards', methods=['POST'])
def api_flashcards():
    """闪卡生成"""
    data = request.get_json()
    text = data.get('text', '').strip()
    count = int(data.get('count', 5))
    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'})
    try:
        result = generate_flashcards(text, count)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/quiz', methods=['POST'])
def api_quiz():
    """测试题生成"""
    data = request.get_json()
    text = data.get('text', '').strip()
    count = int(data.get('count', 5))
    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'})
    try:
        result = generate_quiz(text, count)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/qa', methods=['POST'])
def api_qa():
    """文档问答"""
    data = request.get_json()
    question = data.get('question', '').strip()
    context = data.get('context', '').strip()
    if not question:
        return jsonify({'success': False, 'error': '问题不能为空'})
    if not context:
        return jsonify({'success': False, 'error': '文档内容不能为空'})
    try:
        result = qa_document(question, context)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ---- 写作工具 ----

@app.route('/api/polish', methods=['POST'])
def api_polish():
    """文本润色"""
    data = request.get_json()
    text = data.get('text', '').strip()
    style = data.get('style', '专业')
    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'})
    try:
        result = polish_text(text, style)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/translate', methods=['POST'])
def api_translate():
    """翻译"""
    data = request.get_json()
    text = data.get('text', '').strip()
    target = data.get('target', '英文')
    if not text:
        return jsonify({'success': False, 'error': '文本不能为空'})
    try:
        result = translate_text(text, target)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/creative-writing', methods=['POST'])
def api_creative_writing():
    """创意写作"""
    data = request.get_json()
    topic = data.get('topic', '').strip()
    genre = data.get('genre', '故事')
    length = data.get('length', '中等')
    if not topic:
        return jsonify({'success': False, 'error': '主题不能为空'})
    try:
        result = creative_writing(topic, genre, length)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/marketing-copy', methods=['POST'])
def api_marketing_copy():
    """营销文案"""
    data = request.get_json()
    product = data.get('product', '').strip()
    target = data.get('target', '年轻消费者')
    tone = data.get('tone', '活泼')
    if not product:
        return jsonify({'success': False, 'error': '产品信息不能为空'})
    try:
        result = generate_marketing_copy(product, target, tone)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ---- 图片工具 ----

@app.route('/api/generate-image', methods=['POST'])
def api_generate_image():
    """AI图片生成"""
    data = request.get_json()
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({'success': False, 'error': '图片描述不能为空'})
    try:
        image_url = generate_image(prompt)
        return jsonify({'success': True, 'image_url': image_url, 'prompt': prompt})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ---- 简历工具 ----

@app.route('/api/analyze-resume', methods=['POST'])
def api_analyze_resume():
    """简历分析"""
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'success': False, 'error': '简历内容不能为空'})
    try:
        result = analyze_resume(text)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ---- 文件上传 ----

@app.route('/api/upload-document', methods=['POST'])
def api_upload_document():
    """上传并解析文档"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有上传文件'})

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': '请选择文件'})

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.txt', '.pdf', '.docx', '.doc', '.md'):
        return jsonify({'success': False, 'error': f'不支持的格式: {ext}'})

    file_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, file_id + ext)
    file.save(save_path)

    try:
        content = parse_document(save_path)
        preview = content[:500]
        # 保存到session供后续使用
        if 'documents' not in session:
            session['documents'] = {}
        session['documents'][file_id] = {
            'name': file.filename,
            'content': content,
            'preview': preview
        }
        return jsonify({
            'success': True,
            'doc_id': file_id,
            'name': file.filename,
            'preview': preview,
            'content_preview': content[:2000]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        if os.path.exists(save_path):
            os.remove(save_path)


@app.route('/api/get-document/<doc_id>', methods=['GET'])
def api_get_document(doc_id):
    """获取已上传文档内容"""
    docs = session.get('documents', {})
    if doc_id not in docs:
        return jsonify({'success': False, 'error': '文档不存在'})
    return jsonify({'success': True, 'content': docs[doc_id]['content']})


# ==================== 健康检查 ====================

@app.route('/api/health', methods=['GET'])
def api_health():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'siliconflow': AI_CONFIG['siliconflow']['enabled'],
        'deepseek': AI_CONFIG['deepseek']['enabled'],
        'port': PORT
    })


# ==================== 启动 ====================

if __name__ == '__main__':
    has_api = any(c['enabled'] for c in AI_CONFIG.values())
    if not has_api:
        print("⚠️  警告：未配置 AI API 密钥！")
        print("   请设置环境变量：")
        print("   Linux/macOS: export SILICONFLOW_API_KEY=your_key")
        print("   Windows:     set SILICONFLOW_API_KEY=your_key")
        print("   免费API申请: https://cloud.siliconflow.cn")
        print()

    print(f"🚀 AI多模态创意工作室 启动中...")
    print(f"   访问地址：http://localhost:{PORT}")
    print(f"   SiliconFlow: {'✅ 已配置' if AI_CONFIG['siliconflow']['enabled'] else '❌ 未配置'}")
    print(f"   DeepSeek:    {'✅ 已配置' if AI_CONFIG['deepseek']['enabled'] else '❌ 未配置'}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
