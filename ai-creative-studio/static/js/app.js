// ==================== 全局状态 ====================
let currentDocContent = null;
let currentDocId = null;

// ==================== API 状态检查 ====================
async function checkApiStatus() {
    const el = document.getElementById('apiStatus');
    try {
        const resp = await fetch('/api/health');
        const data = await resp.json();
        if (data.status === 'ok') {
            if (data.siliconflow || data.deepseek) {
                el.innerHTML = '<span class="status-dot online"></span><span class="status-text">API 已连接 ✨</span>';
            } else {
                el.innerHTML = '<span class="status-dot offline"></span><span class="status-text">请配置 API 密钥</span>';
            }
        }
    } catch {
        el.innerHTML = '<span class="status-dot offline"></span><span class="status-text">服务未启动</span>';
    }
}

// ==================== 工具切换 ====================
document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const tool = btn.dataset.tool;
        loadTool(tool);
    });
});

async function loadTool(tool) {
    const panel = document.getElementById('toolPanel');
    panel.innerHTML = '<div class="loading-spinner"><div class="spinner"></div>加载中...</div>';
    const tools = {
        'doc-summary': renderDocSummary,
        'doc-qa': renderDocQA,
        'doc-keywords': renderDocKeywords,
        'doc-entities': renderDocEntities,
        'doc-mindmap': renderDocMindmap,
        'doc-flashcards': renderDocFlashcards,
        'doc-quiz': renderDocQuiz,
        'writing-polish': renderWritingPolish,
        'writing-translate': renderWritingTranslate,
        'writing-creative': renderWritingCreative,
        'writing-marketing': renderWritingMarketing,
        'image-generate': renderImageGenerate,
        'resume-analyze': renderResumeAnalyze,
    };
    if (tools[tool]) {
        await tools[tool](panel);
    }
}

// ==================== API 调用封装 ====================
async function apiCall(url, data) {
    const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    const result = await resp.json();
    if (!result.success) {
        throw new Error(result.error || '操作失败');
    }
    return result;
}

// ==================== 工具渲染函数 ====================

// ---- 文档摘要 ----
async function renderDocSummary(panel) {
    panel.innerHTML = `
        <div class="tool-header">
            <h2>📝 AI文档摘要</h2>
            <p>上传文档或粘贴文本，AI 自动生成精炼摘要</p>
        </div>
        <div class="tool-card">
            <div class="tool-card-title">📄 输入文档</div>
            <div class="form-group">
                <input type="file" id="summaryFile" accept=".txt,.pdf,.docx,.md" onchange="handleFileUpload('summary', this)">
            </div>
            <div class="form-group">
                <label class="form-label">或直接粘贴文本内容</label>
                <textarea id="summaryText" placeholder="在这里粘贴需要摘要的文本内容..." oninput="clearDocId('summary')"></textarea>
            </div>
            <button class="btn btn-primary" onclick="runSummarize()">✨ 生成摘要</button>
            <div id="summaryResult"></div>
        </div>
    `;
}

// ---- 文档问答 ----
async function renderDocQA(panel) {
    panel.innerHTML = `
        <div class="tool-header">
            <h2>❓ 文档智能问答</h2>
            <p>上传文档后，针对文档内容自由提问，AI 准确回答</p>
        </div>
        <div class="tool-card">
            <div class="tool-card-title">📄 上传文档</div>
            <input type="file" id="qaFile" accept=".txt,.pdf,.docx,.md" onchange="handleFileUpload('qa', this)">
            <div id="qaDocInfo" style="margin-top:12px; font-size:13px; color:var(--text-secondary);"></div>
        </div>
        <div class="tool-card">
            <div class="tool-card-title">💬 提问</div>
            <div class="form-group">
                <textarea id="qaQuestion" placeholder="输入你想问的问题..." style="min-height:80px;"></textarea>
            </div>
            <button class="btn btn-primary" onclick="runDocQA()">🔍 提问</button>
            <div id="qaResult"></div>
        </div>
    `;
}

// ---- 关键词提取 ----
async function renderDocKeywords(panel) {
    panel.innerHTML = `
        <div class="tool-header">
            <h2>🔑 关键词提取</h2>
            <p>自动识别文本核心关键词，掌握内容要点</p>
        </div>
        <div class="tool-card">
            <div class="tool-card-title">📄 输入文本</div>
            <textarea id="kwText" placeholder="输入或粘贴需要提取关键词的文本..." style="min-height:150px;"></textarea>
            <button class="btn btn-primary" onclick="runKeywords()" style="margin-top:12px;">🔑 提取关键词</button>
            <div id="kwResult"></div>
        </div>
    `;
}

// ---- 实体识别 ----
async function renderDocEntities(panel) {
    panel.innerHTML = `
        <div class="tool-header">
            <h2>🏷️ 实体识别</h2>
            <p>智能识别文本中的人物、地点、机构、时间</p>
        </div>
        <div class="tool-card">
            <div class="tool-card-title">📄 输入文本</div>
            <textarea id="entityText" placeholder="输入或粘贴文本内容..." style="min-height:150px;"></textarea>
            <button class="btn btn-primary" onclick="runEntities()" style="margin-top:12px;">🏷️ 识别实体</button>
            <div id="entityResult"></div>
        </div>
    `;
}

// ---- 思维导图 ----
async function renderDocMindmap(panel) {
    panel.innerHTML = `
        <div class="tool-header">
            <h2>🧠 思维导图生成</h2>
            <p>输入内容，AI 自动生成结构化思维导图</p>
        </div>
        <div class="tool-card">
            <div class="tool-card-title">📄 输入内容</div>
            <textarea id="mmText" placeholder="输入需要生成思维导图的内容..." style="min-height:150px;"></textarea>
            <button class="btn btn-primary" onclick="runMindmap()" style="margin-top:12px;">🧠 生成导图</button>
            <div id="mmResult"></div>
        </div>
    `;
}

// ---- 闪卡生成 ----
async function renderDocFlashcards(panel) {
    panel.innerHTML = `
        <div class="tool-header">
            <h2>📇 闪卡生成器</h2>
            <p>上传学习材料，AI 生成问答闪卡，助你高效记忆</p>
        </div>
        <div class="tool-card">
            <div class="tool-card-title">📄 学习材料</div>
            <textarea id="fcText" placeholder="输入或粘贴学习材料内容..." style="min-height:150px;"></textarea>
            <div class="form-group" style="margin-top:12px;">
                <label class="form-label">生成数量</label>
                <select id="fcCount">
                    <option value="3">3 张</option>
                    <option value="5" selected>5 张</option>
                    <option value="8">8 张</option>
                    <option value="10">10 张</option>
                </select>
            </div>
            <button class="btn btn-primary" onclick="runFlashcards()">📇 生成闪卡</button>
            <div id="fcResult"></div>
        </div>
    `;
}

// ---- 试题生成 ----
async function renderDocQuiz(panel) {
    panel.innerHTML = `
        <div class="tool-header">
            <h2>📋 AI试题生成</h2>
            <p>输入教材或笔记，AI 自动生成选择题测试卷</p>
        </div>
        <div class="tool-card">
            <div class="tool-card-title">📄 学习材料</div>
            <textarea id="quizText" placeholder="输入学习材料内容..." style="min-height:150px;"></textarea>
            <div class="form-group" style="margin-top:12px;">
                <label class="form-label">题目数量</label>
                <select id="quizCount">
                    <option value="3">3 题</option>
                    <option value="5" selected>5 题</option>
                    <option value="8">8 题</option>
                    <option value="10">10 题</option>
                </select>
            </div>
            <button class="btn btn-primary" onclick="runQuiz()">📋 生成试题</button>
            <div id="quizResult"></div>
        </div>
    `;
}

// ---- 文本润色 ----
async function renderWritingPolish(panel) {
    panel.innerHTML = `
        <div class="tool-header">
            <h2>✨ 文本润色</h2>
            <p>AI 帮你改写、润色、升级文章风格</p>
        </div>
        <div class="tool-card">
            <div class="tool-card-title">✍️ 原始文本</div>
            <textarea id="polishText" placeholder="输入需要润色的文本..." style="min-height:150px;"></textarea>
            <div class="form-group" style="margin-top:12px;">
                <label class="form-label">润色风格</label>
                <select id="polishStyle">
                    <option value="专业">专业正式</option>
                    <option value="简洁">简洁干练</option>
                    <option value="生动">生动活泼</option>
                    <option value="文学">文学优美</option>
                </select>
            </div>
            <button class="btn btn-primary" onclick="runPolish()">✨ 润色文本</button>
            <div id="polishResult"></div>
        </div>
    `;
}

// ---- 文本翻译 ----
async function renderWritingTranslate(panel) {
    panel.innerHTML = `
        <div class="tool-header">
            <h2>🌐 AI翻译</h2>
            <p>高质量多语言翻译，保持原文风格</p>
        </div>
        <div class="tool-card">
            <div class="tool-card-title">📝 待翻译文本</div>
            <textarea id="transText" placeholder="输入需要翻译的文本（中文）..." style="min-height:150px;"></textarea>
            <div class="form-group" style="margin-top:12px;">
                <label class="form-label">目标语言</label>
                <select id="transLang">
                    <option value="英文">英文</option>
                    <option value="日文">日文</option>
                    <option value="韩文">韩文</option>
                    <option value="法文">法文</option>
                    <option value="德文">德文</option>
                    <option value="西班牙文">西班牙文</option>
                    <option value="俄文">俄文</option>
                </select>
            </div>
            <button class="btn btn-primary" onclick="runTranslate()">🌐 翻译</button>
            <div id="transResult"></div>
        </div>
    `;
}

// ---- 创意写作 ----
async function renderWritingCreative(panel) {
    panel.innerHTML = `
        <div class="tool-header">
            <h2>📖 AI创意写作</h2>
            <p>输入主题，AI 帮你写出精彩故事或文章</p>
        </div>
        <div class="tool-card">
            <div class="tool-card-title">📝 写作主题</div>
            <div class="form-group">
                <input type="text" id="creativeTopic" placeholder="输入写作主题，例如：未来城市的最后一个图书管理员">
            </div>
            <div class="two-col">
                <div class="form-group">
                    <label class="form-label">文体</label>
                    <select id="creativeGenre">
                        <option value="故事">故事</option>
                        <option value="小说">小说</option>
                        <option value="诗歌">诗歌</option>
                        <option value="散文">散文</option>
                        <option value="科幻">科幻</option>
                        <option value="童话">童话</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">篇幅</label>
                    <select id="creativeLength">
                        <option value="短">短篇（300字）</option>
                        <option value="中等" selected>中等（800字）</option>
                        <option value="长">长篇（1500字）</option>
                    </select>
                </div>
            </div>
            <button class="btn btn-primary" onclick="runCreative()">📖 开始写作</button>
            <div id="creativeResult"></div>
        </div>
    `;
}

// ---- 营销文案 ----
async function renderWritingMarketing(panel) {
    panel.innerHTML = `
        <div class="tool-header">
            <h2>📣 营销文案生成</h2>
            <p>输入产品信息，AI 生成高转化率营销文案</p>
        </div>
        <div class="tool-card">
            <div class="tool-card-title">📦 产品信息</div>
            <div class="form-group">
                <input type="text" id="mktProduct" placeholder="输入产品名称和核心卖点">
            </div>
            <div class="two-col">
                <div class="form-group">
                    <label class="form-label">目标人群</label>
                    <select id="mktTarget">
                        <option value="年轻消费者">年轻消费者</option>
                        <option value="职场人士">职场人士</option>
                        <option value="学生群体">学生群体</option>
                        <option value="家庭用户">家庭用户</option>
                        <option value="中老年用户">中老年用户</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">文案风格</label>
                    <select id="mktTone">
                        <option value="活泼">活泼</option>
                        <option value="专业">专业</option>
                        <option value="温情">温情</option>
                        <option value="震撼">震撼</option>
                        <option value="简约">简约</option>
                    </select>
                </div>
            </div>
            <button class="btn btn-primary" onclick="runMarketing()">📣 生成文案</button>
            <div id="marketingResult"></div>
        </div>
    `;
}

// ---- 图片生成 ----
async function renderImageGenerate(panel) {
    panel.innerHTML = `
        <div class="tool-header">
            <h2>🖼️ AI图片生成</h2>
            <p>输入描述词，AI 为你生成精美图片</p>
        </div>
        <div class="tool-card">
            <div class="tool-card-title">🎨 图片描述</div>
            <div class="form-group">
                <textarea id="imgPrompt" placeholder="描述你想要的图片，例如：一只戴着墨镜的柯基犬站在东京街头，赛博朋克风格，霓虹灯光..." style="min-height:100px;"></textarea>
            </div>
            <div class="form-group">
                <label class="form-label">图片尺寸</label>
                <select id="imgSize">
                    <option value="1024x1024">正方形 1:1</option>
                    <option value="1024x768">横版 4:3</option>
                    <option value="768x1024">竖版 3:4</option>
                </select>
            </div>
            <button class="btn btn-primary" onclick="runImageGen()">🎨 生成图片</button>
            <div id="imgResult"></div>
        </div>
    `;
}

// ---- 简历分析 ----
async function renderResumeAnalyze(panel) {
    panel.innerHTML = `
        <div class="tool-header">
            <h2>📊 AI简历分析</h2>
            <p>上传或粘贴简历，AI 给出详细评估与优化建议</p>
        </div>
        <div class="tool-card">
            <div class="tool-card-title">📄 简历内容</div>
            <textarea id="resumeText" placeholder="粘贴简历内容（个人信息部分可脱敏）..." style="min-height:200px;"></textarea>
            <button class="btn btn-primary" onclick="runResume()" style="margin-top:12px;">📊 分析简历</button>
            <div id="resumeResult"></div>
        </div>
    `;
}

// ==================== 文件上传处理 ====================
async function handleFileUpload(prefix, input) {
    const file = input.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const resp = await fetch('/api/upload-document', { method: 'POST', body: formData });
        const data = await resp.json();

        if (data.success) {
            currentDocId = data.doc_id;
            currentDocContent = data.content_preview;

            if (prefix === 'summary') {
                document.getElementById('summaryText').value = data.content_preview;
            } else if (prefix === 'qa') {
                document.getElementById('qaDocInfo').innerHTML =
                    `✅ 已加载：<strong>${data.name}</strong><br><small style="color:var(--text-muted)">${data.preview.slice(0, 100)}...</small>`;
                currentDocContent = data.content_preview;
            }
        } else {
            alert('上传失败：' + data.error);
        }
    } catch (e) {
        alert('上传出错：' + e.message);
    }
}

function clearDocId(prefix) {
    if (prefix === 'summary') {
        currentDocId = null;
    }
}

// ==================== 操作执行函数 ====================

async function runSummarize() {
    const text = document.getElementById('summaryText').value.trim();
    const resultEl = document.getElementById('summaryResult');

    if (!text) { resultEl.innerHTML = '<div class="error-msg">请输入或上传需要摘要的文本内容</div>'; return; }

    resultEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div>AI 正在生成摘要，请稍候...</div>';
    try {
        const data = await apiCall('/api/summarize', { text });
        resultEl.innerHTML = `
            <div class="result-label">✨ 摘要结果</div>
            <div class="result-box">${escapeHtml(data.result)}</div>`;
    } catch (e) {
        resultEl.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
    }
}

async function runDocQA() {
    const question = document.getElementById('qaQuestion').value.trim();
    const resultEl = document.getElementById('qaResult');

    if (!question) { resultEl.innerHTML = '<div class="error-msg">请输入问题</div>'; return; }
    if (!currentDocContent) { resultEl.innerHTML = '<div class="error-msg">请先上传文档</div>'; return; }

    resultEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div>AI 正在阅读文档并回答...</div>';
    try {
        const data = await apiCall('/api/qa', { question, context: currentDocContent });
        resultEl.innerHTML = `
            <div class="result-label">💬 AI 回答</div>
            <div class="result-box">${escapeHtml(data.result)}</div>`;
    } catch (e) {
        resultEl.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
    }
}

async function runKeywords() {
    const text = document.getElementById('kwText').value.trim();
    const resultEl = document.getElementById('kwResult');

    if (!text) { resultEl.innerHTML = '<div class="error-msg">请输入文本内容</div>'; return; }

    resultEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div>提取中...</div>';
    try {
        const data = await apiCall('/api/keywords', { text });
        const tags = data.result.map(k => `<span class="tag">${escapeHtml(k)}</span>`).join('');
        resultEl.innerHTML = `<div class="result-label">🔑 关键词</div><div style="margin-top:8px;">${tags}</div>`;
    } catch (e) {
        resultEl.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
    }
}

async function runEntities() {
    const text = document.getElementById('entityText').value.trim();
    const resultEl = document.getElementById('entityResult');

    if (!text) { resultEl.innerHTML = '<div class="error-msg">请输入文本内容</div>'; return; }

    resultEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div>识别中...</div>';
    try {
        const data = await apiCall('/api/entities', { text });
        const r = data.result;
        let html = '';
        for (const [type, items] of Object.entries(r)) {
            if (items && items.length > 0) {
                const cls = type.includes('人物') ? 'person' : type.includes('地点') ? 'place' : type.includes('机构') ? 'org' : 'time';
                const tags = items.map(i => `<span class="tag tag-${cls}">${escapeHtml(i)}</span>`).join('');
                html += `<div style="margin-bottom:12px;"><strong>${type}：</strong>${tags}</div>`;
            }
        }
        resultEl.innerHTML = html || '<div class="result-box">未识别到实体</div>';
    } catch (e) {
        resultEl.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
    }
}

async function runMindmap() {
    const text = document.getElementById('mmText').value.trim();
    const resultEl = document.getElementById('mmResult');

    if (!text) { resultEl.innerHTML = '<div class="error-msg">请输入内容</div>'; return; }

    resultEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div>生成思维导图中...</div>';
    try {
        const data = await apiCall('/api/mindmap', { text });
        resultEl.innerHTML = `
            <div class="result-label">🧠 思维导图</div>
            <div class="result-box mindmap-output">${escapeHtml(data.result)}</div>`;
    } catch (e) {
        resultEl.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
    }
}

async function runFlashcards() {
    const text = document.getElementById('fcText').value.trim();
    const count = parseInt(document.getElementById('fcCount').value);
    const resultEl = document.getElementById('fcResult');

    if (!text) { resultEl.innerHTML = '<div class="error-msg">请输入学习材料</div>'; return; }

    resultEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div>生成闪卡中...</div>';
    try {
        const data = await apiCall('/api/flashcards', { text, count });
        // 解析闪卡格式：【问题】xxx 【答案】yyy
        const cards = parseFlashcards(data.result);
        let html = '';
        cards.forEach((card, i) => {
            html += `<div class="flashcard">
                <div class="flashcard-q">Q${i+1}：${escapeHtml(card.q)}</div>
                <div class="flashcard-a">A：${escapeHtml(card.a)}</div>
            </div>`;
        });
        resultEl.innerHTML = `<div class="result-label">📇 闪卡（共${cards.length}张）</div>${html}`;
    } catch (e) {
        resultEl.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
    }
}

async function runQuiz() {
    const text = document.getElementById('quizText').value.trim();
    const count = parseInt(document.getElementById('quizCount').value);
    const resultEl = document.getElementById('quizResult');

    if (!text) { resultEl.innerHTML = '<div class="error-msg">请输入学习材料</div>'; return; }

    resultEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div>生成试题中...</div>';
    try {
        const data = await apiCall('/api/quiz', { text, count });
        resultEl.innerHTML = `
            <div class="result-label">📋 测试题</div>
            <div class="result-box">${escapeHtml(data.result)}</div>`;
    } catch (e) {
        resultEl.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
    }
}

async function runPolish() {
    const text = document.getElementById('polishText').value.trim();
    const style = document.getElementById('polishStyle').value;
    const resultEl = document.getElementById('polishResult');

    if (!text) { resultEl.innerHTML = '<div class="error-msg">请输入需要润色的文本</div>'; return; }

    resultEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div>润色中...</div>';
    try {
        const data = await apiCall('/api/polish', { text, style });
        resultEl.innerHTML = `
            <div class="result-label">✨ 润色结果（${style}风格）</div>
            <div class="result-box">${escapeHtml(data.result)}</div>`;
    } catch (e) {
        resultEl.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
    }
}

async function runTranslate() {
    const text = document.getElementById('transText').value.trim();
    const target = document.getElementById('transLang').value;
    const resultEl = document.getElementById('transResult');

    if (!text) { resultEl.innerHTML = '<div class="error-msg">请输入需要翻译的文本</div>'; return; }

    resultEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div>翻译中...</div>';
    try {
        const data = await apiCall('/api/translate', { text, target_lang: target });
        resultEl.innerHTML = `
            <div class="result-label">🌐 翻译结果（${target}）</div>
            <div class="result-box">${escapeHtml(data.result)}</div>`;
    } catch (e) {
        resultEl.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
    }
}

async function runCreative() {
    const topic = document.getElementById('creativeTopic').value.trim();
    const genre = document.getElementById('creativeGenre').value;
    const length = document.getElementById('creativeLength').value;
    const resultEl = document.getElementById('creativeResult');

    if (!topic) { resultEl.innerHTML = '<div class="error-msg">请输入写作主题</div>'; return; }

    resultEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div>创意写作中，这可能需要一点时间...</div>';
    try {
        const data = await apiCall('/api/creative-writing', { topic, genre, length });
        resultEl.innerHTML = `
            <div class="result-label">📖 创作成果（${genre}·${length}篇）</div>
            <div class="result-box">${escapeHtml(data.result)}</div>`;
    } catch (e) {
        resultEl.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
    }
}

async function runMarketing() {
    const product = document.getElementById('mktProduct').value.trim();
    const target = document.getElementById('mktTarget').value;
    const tone = document.getElementById('mktTone').value;
    const resultEl = document.getElementById('marketingResult');

    if (!product) { resultEl.innerHTML = '<div class="error-msg">请输入产品信息</div>'; return; }

    resultEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div>生成营销文案...</div>';
    try {
        const data = await apiCall('/api/marketing-copy', { product, target, tone });
        resultEl.innerHTML = `
            <div class="result-label">📣 营销文案（面向${target}，${tone}风格）</div>
            <div class="result-box">${escapeHtml(data.result)}</div>`;
    } catch (e) {
        resultEl.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
    }
}

async function runImageGen() {
    const prompt = document.getElementById('imgPrompt').value.trim();
    const size = document.getElementById('imgSize').value;
    const resultEl = document.getElementById('imgResult');

    if (!prompt) { resultEl.innerHTML = '<div class="error-msg">请输入图片描述</div>'; return; }

    resultEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div>AI 正在生成图片，请稍候...</div>';
    try {
        const data = await apiCall('/api/generate-image', { prompt, size });
        resultEl.innerHTML = `
            <div class="image-preview">
                <img src="${data.image_url}" alt="AI生成的图片" onerror="this.src='data:image/svg+xml,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'400\\' height=\\'400\\'><rect fill=\\'%231a1a2e\\' width=\\'400\\' height=\\'400\\'/><text x=\\'50%\\' y=\\'50%\\' fill=\\'%2394a3b8\\' text-anchor=\\'middle\\' dy=\\'.3em\\'>图片加载中...</text></svg>'">
                <span class="prompt-tag">描述：${escapeHtml(prompt)}</span>
            </div>`;
    } catch (e) {
        resultEl.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
    }
}

async function runResume() {
    const text = document.getElementById('resumeText').value.trim();
    const resultEl = document.getElementById('resumeResult');

    if (!text) { resultEl.innerHTML = '<div class="error-msg">请输入简历内容</div>'; return; }

    resultEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div>分析简历中...</div>';
    try {
        const data = await apiCall('/api/analyze-resume', { text });
        resultEl.innerHTML = `
            <div class="result-label">📊 简历分析报告</div>
            <div class="result-box">${escapeHtml(data.result)}</div>`;
    } catch (e) {
        resultEl.innerHTML = `<div class="error-msg">❌ ${e.message}</div>`;
    }
}

// ==================== 辅助函数 ====================

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;')
        .replace(/\n/g, '<br>');
}

function parseFlashcards(text) {
    const cards = [];
    // 匹配【问题】xxx 【答案】yyy 格式
    const regex = /【问题】(.*?)【答案】(.*?)(?=【问题】|$)/gs;
    let match;
    while ((match = regex.exec(text)) !== null) {
        cards.push({ q: match[1].trim(), a: match[2].trim() });
    }
    return cards;
}

// 默认加载文档摘要
loadTool('doc-summary');
