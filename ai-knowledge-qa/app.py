#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI知识问答助手 (RAG Q&A System)
基于检索增强生成（RAG）技术的智能知识库问答系统
灵感来源：中国国际大学生创新大赛 AI软件类获奖项目技术方案

功能：文档上传 → 智能分块 → 向量化存储 → RAG问答 → 溯源引用
"""

import os
import re
import uuid
import hashlib
from datetime import datetime
from functools import wraps

import requests
import yaml
from flask import Flask, render_template, request, jsonify, session

# ==================== 配置 ====================
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'ai-knowledge-qa-secret-2026')

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DOCS_DIR = os.path.join(DATA_DIR, 'docs')
VECTORSTORE_DIR = os.path.join(DATA_DIR, 'vectorstore')
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(VECTORSTORE_DIR, exist_ok=True)

PORT = int(os.environ.get('PORT', 5002))

# ==================== AI API 配置 ====================
# 优先级：SiliconFlow(免费) > DeepSeek > OpenAI


def load_api_config():
    """加载API配置，支持多后端"""
    # 尝试读取yaml配置
    yaml_path = os.path.join(BASE_DIR, 'config.yaml')
    config = {
        'siliconflow': {
            'enabled': False,
            'api_key': os.environ.get('SILICONFLOW_API_KEY', ''),
            'base_url': 'https://api.siliconflow.cn/v1',
            'model': 'Qwen/Qwen2.5-7B-Instruct',
            'embedding_model': 'BAAI/bge-large-zh-v1.5',
        },
        'deepseek': {
            'enabled': False,
            'api_key': os.environ.get('DEEPSEEK_API_KEY', ''),
            'base_url': 'https://api.deepseek.com/v1',
            'model': 'deepseek-chat',
        },
        'openai': {
            'enabled': False,
            'api_key': os.environ.get('OPENAI_API_KEY', ''),
            'base_url': 'https://api.openai.com/v1',
            'model': 'gpt-3.5-turbo',
        },
    }

    # 检查各后端是否配置了API Key
    for name, cfg in config.items():
        if cfg['api_key']:
            cfg['enabled'] = True

    return config


AI_CONFIG = load_api_config()

# ==================== 文档解析 ====================


def parse_txt(file_path):
    """解析TXT文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def parse_md(file_path):
    """解析Markdown文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def parse_docx(file_path):
    """解析Word文档"""
    try:
        from docx import Document
        doc = Document(file_path)
        text = '\n'.join([para.text for para in doc.paragraphs])
        return text
    except ImportError:
        return "[需要安装 python-docx 库来解析 Word 文档]"


def parse_pdf(file_path):
    """解析PDF文件"""
    try:
        import PyPDF2
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ''
            for page in reader.pages:
                text += page.extract_text() or ''
            return text
    except ImportError:
        return "[需要安装 PyPDF2 库来解析 PDF]"


def parse_document(file_path):
    """根据文件扩展名解析文档"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.txt':
        return parse_txt(file_path)
    elif ext == '.md':
        return parse_md(file_path)
    elif ext == '.docx':
        return parse_docx(file_path)
    elif ext == '.pdf':
        return parse_pdf(file_path)
    else:
        return f"[不支持的文件格式: {ext}]"


# ==================== 文本分块 ====================


def chunk_text(text, chunk_size=500, overlap=50):
    """
    将文本分割成重叠的块
    chunk_size: 每个块的字符数
    overlap: 块之间的重叠字符数
    """
    if not text or len(text.strip()) == 0:
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]

        # 尝试在句号、换行符处断句，使块更有语义
        if end < text_len:
            # 找最后一个句号或换行
            last_period = max(chunk.rfind('。'), chunk.rfind('\n'))
            if last_period > chunk_size // 2:
                end = start + last_period + 1

        chunks.append(text[start:end].strip())
        start = end - overlap
        if start >= text_len:
            break

    return [c for c in chunks if c]  # 过滤空块


# ==================== Embedding ====================


def get_embedding(text, config=None):
    """获取文本的embedding向量"""
    if config is None:
        config = AI_CONFIG

    # 优先使用 SiliconFlow
    if config['siliconflow']['enabled']:
        return _embedding_siliconflow(text, config['siliconflow'])

    # 备用 DeepSeek
    if config['deepseek']['enabled']:
        return _embedding_deepseek(text, config['deepseek'])

    if config['openai']['enabled']:
        return _embedding_openai(text, config['openai'])

    raise Exception("未配置任何可用的Embedding API，请配置 SILICONFLOW_API_KEY 等环境变量")


def _embedding_siliconflow(text, cfg):
    """SiliconFlow embedding API"""
    headers = {
        'Authorization': f'Bearer {cfg["api_key"]}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': cfg.get('embedding_model', 'BAAI/bge-large-zh-v1.5'),
        'input': text
    }
    resp = requests.post(
        f'{cfg["base_url"]}/embeddings',
        headers=headers, json=payload, timeout=60
    )
    resp.raise_for_status()
    data = resp.json()
    return data['data'][0]['embedding']


def _embedding_deepseek(text, cfg):
    """DeepSeek embedding API"""
    headers = {
        'Authorization': f'Bearer {cfg["api_key"]}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': 'deepseek-embed',
        'input': text
    }
    resp = requests.post(
        f'{cfg["base_url"]}/embeddings',
        headers=headers, json=payload, timeout=60
    )
    resp.raise_for_status()
    data = resp.json()
    return data['data'][0]['embedding']


def _embedding_openai(text, cfg):
    """OpenAI embedding API"""
    headers = {
        'Authorization': f'Bearer {cfg["api_key"]}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': 'text-embedding-3-small',
        'input': text
    }
    resp = requests.post(
        f'{cfg["base_url"]}/embeddings',
        headers=headers, json=payload, timeout=60
    )
    resp.raise_for_status()
    data = resp.json()
    return data['data'][0]['embedding']


# ==================== FAISS 向量存储 ====================


def build_faiss_index(chunks, config=None):
    """构建FAISS索引"""
    try:
        import faiss
        import numpy as np
    except ImportError:
        raise Exception("请先安装 faiss-cpu: pip install faiss-cpu")

    if not chunks:
        return None, []

    # 获取所有chunk的embedding
    embeddings = []
    for i, chunk in enumerate(chunks):
        print(f"  生成Embedding [{i+1}/{len(chunks)}]...")
        emb = get_embedding(chunk, config)
        embeddings.append(emb)

    # 转换为numpy数组（确保是float32）
    embedding_array = np.array(embeddings).astype('float32')

    # L2归一化（对bge-large-zh-v1.5效果更好）
    norms = np.linalg.norm(embedding_array, axis=1, keepdims=True)
    norms[norms == 0] = 1  # 避免除零
    embedding_array = embedding_array / norms

    # 创建FAISS索引
    dimension = embedding_array.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Inner Product（归一化后等价于cosine）
    index.add(embedding_array)

    return index, chunks


# ==================== 向量检索 ====================


def search_chunks(query, index, chunks, top_k=5, config=None):
    """检索最相关的chunk"""
    try:
        import faiss
        import numpy as np
    except ImportError:
        return []

    if index is None or not chunks:
        return []

    # 获取query的embedding
    query_emb = get_embedding(query, config)
    query_array = np.array([query_emb]).astype('float32')

    # L2归一化
    norm = np.linalg.norm(query_array)
    if norm > 0:
        query_array = query_array / norm

    # 检索
    distances, indices = index.search(query_array, min(top_k, len(chunks)))

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx >= 0 and idx < len(chunks):
            results.append({
                'chunk': chunks[idx],
                'score': float(dist),
                'index': int(idx)
            })

    return results


# ==================== LLM 生成 ====================


def generate_answer(prompt, config=None):
    """调用LLM生成答案"""
    if config is None:
        config = AI_CONFIG

    if config['siliconflow']['enabled']:
        return _generate_siliconflow(prompt, config['siliconflow'])

    if config['deepseek']['enabled']:
        return _generate_deepseek(prompt, config['deepseek'])

    if config['openai']['enabled']:
        return _generate_openai(prompt, config['openai'])

    raise Exception("未配置任何可用的LLM API，请配置 SILICONFLOW_API_KEY 等环境变量")


def _generate_siliconflow(prompt, cfg):
    """SiliconFlow LLM API"""
    headers = {
        'Authorization': f'Bearer {cfg["api_key"]}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': cfg.get('model', 'Qwen/Qwen2.5-7B-Instruct'),
        'messages': [
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7,
        'max_tokens': 1000
    }
    resp = requests.post(
        f'{cfg["base_url"]}/chat/completions',
        headers=headers, json=payload, timeout=120
    )
    resp.raise_for_status()
    data = resp.json()
    return data['choices'][0]['message']['content']


def _generate_deepseek(prompt, cfg):
    """DeepSeek LLM API"""
    headers = {
        'Authorization': f'Bearer {cfg["api_key"]}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': cfg.get('model', 'deepseek-chat'),
        'messages': [
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7,
        'max_tokens': 1000
    }
    resp = requests.post(
        f'{cfg["base_url"]}/chat/completions',
        headers=headers, json=payload, timeout=120
    )
    resp.raise_for_status()
    data = resp.json()
    return data['choices'][0]['message']['content']


def _generate_openai(prompt, cfg):
    """OpenAI LLM API"""
    headers = {
        'Authorization': f'Bearer {cfg["api_key"]}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': cfg.get('model', 'gpt-3.5-turbo'),
        'messages': [
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.7,
        'max_tokens': 1000
    }
    resp = requests.post(
        f'{cfg["base_url"]}/chat/completions',
        headers=headers, json=payload, timeout=120
    )
    resp.raise_for_status()
    data = resp.json()
    return data['choices'][0]['message']['content']


# ==================== RAG Pipeline ====================


class RAGIndex:
    """RAG索引管理器"""

    def __init__(self, doc_id):
        self.doc_id = doc_id
        self.index_file = os.path.join(VECTORSTORE_DIR, f'{doc_id}.index')
        self.chunks_file = os.path.join(VECTORSTORE_DIR, f'{doc_id}.chunks')
        self.meta_file = os.path.join(VECTORSTORE_DIR, f'{doc_id}.meta')
        self.index = None
        self.chunks = []
        self.meta = {}

    def save(self, index, chunks, meta=None):
        """保存索引和chunks"""
        import faiss
        import numpy as np

        self.index = index
        self.chunks = chunks
        self.meta = meta or {}

        # 保存FAISS索引
        faiss.write_index(index, self.index_file)

        # 保存chunks
        with open(self.chunks_file, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                f.write(chunk + '\n===CHUNK_SEPARATOR===\n')

        # 保存元信息
        with open(self.meta_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.meta, f, allow_unicode=True)

    def load(self):
        """加载索引"""
        import faiss

        if not os.path.exists(self.index_file):
            return False

        self.index = faiss.read_index(self.index_file)

        with open(self.chunks_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.chunks = content.split('\n===CHUNK_SEPARATOR===\n')
            self.chunks = [c for c in self.chunks if c]

        if os.path.exists(self.meta_file):
            with open(self.meta_file, 'r', encoding='utf-8') as f:
                self.meta = yaml.safe_load(f) or {}

        return True

    def delete(self):
        """删除索引文件"""
        for f in [self.index_file, self.chunks_file, self.meta_file]:
            if os.path.exists(f):
                os.remove(f)


class GlobalIndex:
    """全局索引管理器，管理所有文档"""

    def __init__(self):
        self.doc_dir = DOCS_DIR
        self.index_file = os.path.join(VECTORSTORE_DIR, 'global.index')
        self.chunks_file = os.path.join(VECTORSTORE_DIR, 'global.chunks')
        self.docs_file = os.path.join(VECTORSTORE_DIR, 'global.docs')
        self.index = None
        self.chunks = []
        self.doc_map = {}  # chunk_index -> {doc_id, doc_name}
        self.docs = {}  # doc_id -> {name, status, upload_time}

        # 确保目录存在
        os.makedirs(self.doc_dir, exist_ok=True)
        os.makedirs(VECTORSTORE_DIR, exist_ok=True)

    def _get_all_chunks(self):
        """获取所有文档的所有chunks"""
        all_chunks = []
        chunk_docs = []
        chunk_indices = []

        idx = 0
        for doc_id in os.listdir(self.doc_dir):
            doc_path = os.path.join(self.doc_dir, doc_id)
            if not os.path.isdir(doc_path):
                continue

            meta_file = os.path.join(doc_path, 'meta.yaml')
            if not os.path.exists(meta_file):
                continue

            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = yaml.safe_load(f) or {}

            chunks_file = os.path.join(doc_path, 'chunks.txt')
            if os.path.exists(chunks_file):
                with open(chunks_file, 'r', encoding='utf-8') as f:
                    chunks = f.read().split('\n===CHUNK_SEPARATOR===\n')
                    chunks = [c for c in chunks if c]

                for chunk in chunks:
                    all_chunks.append(chunk)
                    chunk_docs.append(meta.get('name', doc_id))
                    chunk_indices.append(idx)
                    idx += 1

        return all_chunks, chunk_docs, chunk_indices

    def rebuild_index(self, config=None):
        """重建全局索引"""
        import faiss
        import numpy as np

        all_chunks, chunk_docs, chunk_indices = self._get_all_chunks()

        if not all_chunks:
            self.index = None
            self.chunks = []
            self.doc_map = {}
            if os.path.exists(self.index_file):
                os.remove(self.index_file)
            return True

        print(f"正在为 {len(all_chunks)} 个chunks生成embeddings...")
        embeddings = []
        for i, chunk in enumerate(all_chunks):
            print(f"  [{i+1}/{len(all_chunks)}]")
            emb = get_embedding(chunk, config)
            embeddings.append(emb)
            # 每20个chunks保存一次进度（避免API超时）
            if (i + 1) % 20 == 0:
                print(f"  已生成 {i+1} 个embeddings...")

        embedding_array = np.array(embeddings).astype('float32')

        # L2归一化
        norms = np.linalg.norm(embedding_array, axis=1, keepdims=True)
        norms[norms == 0] = 1
        embedding_array = embedding_array / norms

        dimension = embedding_array.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embedding_array)

        self.chunks = all_chunks
        self.doc_map = {i: {'doc_name': chunk_docs[i]} for i in range(len(all_chunks))}

        # 保存索引
        faiss.write_index(self.index, self.index_file)

        with open(self.chunks_file, 'w', encoding='utf-8') as f:
            for chunk in all_chunks:
                f.write(chunk + '\n===CHUNK_SEPARATOR===\n')

        with open(self.docs_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.docs, f, allow_unicode=True)

        return True

    def load(self):
        """加载全局索引"""
        import faiss

        if not os.path.exists(self.index_file):
            return False

        self.index = faiss.read_index(self.index_file)

        if os.path.exists(self.chunks_file):
            with open(self.chunks_file, 'r', encoding='utf-8') as f:
                content = f.read()
                self.chunks = content.split('\n===CHUNK_SEPARATOR===\n')
                self.chunks = [c for c in self.chunks if c]

        if os.path.exists(self.docs_file):
            with open(self.docs_file, 'r', encoding='utf-8') as f:
                self.docs = yaml.safe_load(f) or {}

        return True

    def search(self, query, top_k=5, config=None):
        """检索相关chunks"""
        import faiss
        import numpy as np

        if self.index is None:
            return []

        query_emb = get_embedding(query, config)
        query_array = np.array([query_emb]).astype('float32')

        norm = np.linalg.norm(query_array)
        if norm > 0:
            query_array = query_array / norm

        distances, indices = self.index.search(query_array, min(top_k, len(self.chunks)))

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(self.chunks):
                results.append({
                    'chunk': self.chunks[idx],
                    'score': float(dist),
                    'index': int(idx),
                    'doc_name': self.doc_map.get(idx, {}).get('doc_name', '未知文档')
                })

        return results


# 全局索引实例
_global_index = None


def get_global_index():
    """获取全局索引单例"""
    global _global_index
    if _global_index is None:
        _global_index = GlobalIndex()
        _global_index.load()
    return _global_index


# ==================== Flask 路由 ====================


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_document():
    """上传并解析文档"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有上传文件'})

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': '请选择文件'})

    # 保存文件
    doc_id = str(uuid.uuid4())
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()

    # 支持格式
    if ext not in ['.txt', '.md', '.docx', '.pdf']:
        return jsonify({'success': False, 'error': f'不支持的格式 {ext}，支持：txt, md, docx, pdf'})

    doc_dir = os.path.join(DOCS_DIR, doc_id)
    os.makedirs(doc_dir, exist_ok=True)

    file_path = os.path.join(doc_dir, filename)
    file.save(file_path)

    # 解析文档
    try:
        text = parse_document(file_path)
    except Exception as e:
        return jsonify({'success': False, 'error': f'解析文档失败: {str(e)}'})

    if not text or len(text.strip()) == 0:
        return jsonify({'success': False, 'error': '文档内容为空'})

    # 分块
    chunks = chunk_text(text)
    if not chunks:
        return jsonify({'success': False, 'error': '文档分块失败'})

    # 保存chunks
    chunks_file = os.path.join(doc_dir, 'chunks.txt')
    with open(chunks_file, 'w', encoding='utf-8') as f:
        f.write('\n===CHUNK_SEPARATOR===\n'.join(chunks))

    # 保存元信息
    meta = {
        'doc_id': doc_id,
        'name': filename,
        'size': os.path.getsize(file_path),
        'chunk_count': len(chunks),
        'upload_time': datetime.now().isoformat(),
    }
    meta_file = os.path.join(doc_dir, 'meta.yaml')
    with open(meta_file, 'w', encoding='utf-8') as f:
        yaml.dump(meta, f, allow_unicode=True)

    # 保存原始文本（供预览用）
    text_file = os.path.join(doc_dir, 'content.txt')
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(text[:5000])  # 保存前5000字符预览

    # 重建全局索引
    gidx = get_global_index()
    gidx.docs[doc_id] = {
        'name': filename,
        'size': os.path.getsize(file_path),
        'chunk_count': len(chunks),
        'upload_time': datetime.now().isoformat(),
        'status': 'ready'
    }

    try:
        gidx.rebuild_index(AI_CONFIG)
    except Exception as e:
        return jsonify({'success': False, 'error': f'索引构建失败: {str(e)}'})

    return jsonify({
        'success': True,
        'doc_id': doc_id,
        'name': filename,
        'chunk_count': len(chunks),
        'preview': text[:500]
    })


@app.route('/api/docs', methods=['GET'])
def list_docs():
    """获取文档列表"""
    docs = []
    for doc_id in os.listdir(DOCS_DIR):
        doc_path = os.path.join(DOCS_DIR, doc_id)
        if not os.path.isdir(doc_path):
            continue

        meta_file = os.path.join(doc_path, 'meta.yaml')
        if not os.path.exists(meta_file):
            continue

        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = yaml.safe_load(f) or {}

        docs.append({
            'doc_id': doc_id,
            'name': meta.get('name', doc_id),
            'size': meta.get('size', 0),
            'chunk_count': meta.get('chunk_count', 0),
            'upload_time': meta.get('upload_time', ''),
        })

    docs.sort(key=lambda x: x['upload_time'], reverse=True)
    return jsonify({'success': True, 'docs': docs})


@app.route('/api/docs/<doc_id>', methods=['DELETE'])
def delete_doc(doc_id):
    """删除文档"""
    doc_dir = os.path.join(DOCS_DIR, doc_id)
    if os.path.exists(doc_dir):
        import shutil
        shutil.rmtree(doc_dir)

    # 重建全局索引
    gidx = get_global_index()
    if doc_id in gidx.docs:
        del gidx.docs[doc_id]

    try:
        gidx.rebuild_index(AI_CONFIG)
    except Exception as e:
        pass  # 忽略重建错误

    return jsonify({'success': True})


@app.route('/api/ask', methods=['POST'])
def ask_question():
    """RAG问答"""
    data = request.get_json()
    question = data.get('question', '').strip()

    if not question:
        return jsonify({'success': False, 'error': '问题不能为空'})

    if not os.path.exists(VECTORSTORE_DIR + '/global.index'):
        return jsonify({'success': False, 'error': '请先上传文档到知识库'})

    gidx = get_global_index()

    # 1. 检索相关chunks
    search_results = gidx.search(question, top_k=5, config=AI_CONFIG)

    if not search_results:
        return jsonify({
            'success': True,
            'answer': '抱歉，知识库中没有找到与您问题相关的内容。',
            'sources': []
        })

    # 2. 构建RAG prompt
    context = "\n\n".join([
        f"【来源{chr(65+i)}】{r['chunk']}"
        for i, r in enumerate(search_results)
    ])

    prompt = f"""你是一个基于给定文档内容的智能问答助手。请根据以下文档内容，准确回答用户的问题。

【重要规则】
1. 只根据提供的文档内容回答，不要编造答案
2. 如果文档中没有相关内容，请明确说明"根据当前文档无法回答这个问题"
3. 回答要准确引用来源，用【来源X】标注答案对应的文档来源
4. 回答要简洁有条理，使用中文

【相关文档内容】
{context}

【用户问题】
{question}

【回答】
"""

    # 3. 调用LLM生成答案
    try:
        answer = generate_answer(prompt, AI_CONFIG)
    except Exception as e:
        return jsonify({'success': False, 'error': f'生成答案失败: {str(e)}'})

    # 4. 构建sources
    sources = []
    seen_docs = set()
    for i, r in enumerate(search_results):
        doc_name = r.get('doc_name', '未知文档')
        if doc_name not in seen_docs:
            sources.append({
                'label': f'来源{chr(65 + i)}',
                'doc_name': doc_name,
                'content': r['chunk'][:200] + '...',
                'score': round(r['score'], 3)
            })
            seen_docs.add(doc_name)

    return jsonify({
        'success': True,
        'answer': answer,
        'sources': sources
    })


# ==================== 启动 ====================


if __name__ == '__main__':
    # 检查依赖
    try:
        import faiss
    except ImportError:
        print("❌ 缺少 faiss-cpu，请先安装：")
        print("   pip install faiss-cpu")
        print()

    try:
        import yaml
    except ImportError:
        print("❌ 缺少 pyyaml，请先安装：")
        print("   pip install pyyaml")
        print()

    # 检查API配置
    has_api = any(cfg['enabled'] for cfg in AI_CONFIG.values())
    if not has_api:
        print("⚠️  警告：未配置AI API密钥，功能将受限")
        print("   推荐使用硅基流动（免费）：https://cloud.siliconflow.cn")
        print("   设置环境变量：export SILICONFLOW_API_KEY=your_key")
        print()

    print(f"🚀 AI知识问答助手启动中...")
    print(f"   访问地址：http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)