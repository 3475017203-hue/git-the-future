#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI合同风险审查助手
基于中国国际大学生创新大赛获奖项目灵感实现
功能：合同上传、智能分析、风险识别、条款优化建议

灵感来源：AI慧眼+简历优化师的SaaS思路
核心创新：用AI大模型快速识别合同风险点，给出通俗易懂的解释和建议
"""

import os
import re
import io
from datetime import datetime

from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
import requests

# ==================== 配置 ====================
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'ai-contract-reviewer-secret-2026')

# AI API 配置（支持多个提供商，自动选择可用的）
AI_CONFIG = {
    'siliconflow': {
        'enabled': bool(os.environ.get('SILICONFLOW_API_KEY')),
        'api_key': os.environ.get('SILICONFLOW_API_KEY', ''),
        'base_url': 'https://api.siliconflow.cn/v1',
        'model': 'Qwen/Qwen2.5-7B-Instruct',
        'name': '硅基流动 (免费)',
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
        'model': 'gpt-3.5-turbo',
        'name': 'OpenAI GPT-3.5',
    },
    'zhipu': {
        'enabled': bool(os.environ.get('ZHIPU_API_KEY')),
        'api_key': os.environ.get('ZHIPU_API_KEY', ''),
        'base_url': 'https://open.bigmodel.cn/api/paas/v4',
        'model': 'glm-4-flash',
        'name': '智谱AI (免费额度)',
    },
}

# ==================== 合同类型定义 ====================
CONTRACT_TYPES = {
    'employment': {
        'name': '劳动合同',
        'description': '用人单位与劳动者签订的劳动合同',
        'key_points': [
            '试用期条款合法性',
            '社会保险缴纳义务',
            '违约金条款限制',
            '保密协议和竞业限制',
            '解除合同的条件和程序',
        ],
    },
    'rental': {
        'name': '房屋租赁合同',
        'description': '房屋出租方与承租方签订的租赁协议',
        'key_points': [
            '租金支付方式和期限',
            '押金退还条件',
            '提前解约的违约责任',
            '房屋维修责任划分',
            '二房东转租风险',
        ],
    },
    'purchase': {
        'name': '商品买卖合同',
        'description': '买家与卖家之间的商品交易协议',
        'key_points': [
            '商品质量标准',
            '交货时间和地点',
            '付款方式和期限',
            '退货退款条件',
            '违约责任和赔偿',
        ],
    },
    'service': {
        'name': '服务合同',
        'description': '服务提供方与接受方签订的协议',
        'key_points': [
            '服务内容和范围',
            '服务质量和标准',
            '服务费用和支付',
            '服务期限和续约',
            '违约责任和赔偿',
        ],
    },
    'loan': {
        'name': '借贷合同',
        'description': '借款人与出借人之间的借贷协议',
        'key_points': [
            '借款金额和利率',
            '还款方式和期限',
            '逾期利息计算',
            '担保或抵押条款',
            '提前还款条款',
        ],
    },
    'other': {
        'name': '其他合同',
        'description': '其他类型的合同协议',
        'key_points': [
            '合同各方权利义务',
            '合同期限和续约',
            '变更和解除条件',
            '违约责任条款',
            '争议解决方式',
        ],
    },
}


# ==================== AI 调用模块 ====================
def get_available_ai():
    """获取可用的AI配置"""
    for provider, config in AI_CONFIG.items():
        if config['enabled']:
            return provider, config
    return None, None


def call_ai_review(contract_text, contract_type, custom_focus=None):
    """
    调用AI分析合同内容
    
    Args:
        contract_text: 合同文本内容
        contract_type: 合同类型
        custom_focus: 用户自定义关注点
    
    Returns:
        分析结果字典
    """
    provider, config = get_available_ai()
    if not provider:
        return {
            'success': False,
            'error': '没有配置任何AI API密钥，请设置以下任一环境变量：\n'
                     'SILICONFLOW_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY / ZHIPU_API_KEY'
        }
    
    # 获取合同类型信息
    ct_info = CONTRACT_TYPES.get(contract_type, CONTRACT_TYPES['other'])
    key_points = '\n'.join([f'{i+1}. {p}' for i, p in enumerate(ct_info['key_points'])])
    
    # 构建提示词
    system_prompt = f"""你是一位专业、严谨的法律顾问，擅长合同审查和风险分析。

你的任务是：
1. 仔细阅读并分析用户提交的{ct_info['name']}文本
2. 识别合同中存在的风险点、漏洞和不公平条款
3. 用通俗易懂的语言解释每个风险点
4. 提出具体的修改建议

分析维度：
- 合同各方的权利义务是否对等
- 关键条款是否完整、清晰
- 是否存在模糊、歧义性表述
- 违约责任是否过重或缺失
- 是否存在法律风险或隐患
- 格式条款是否公平合理

重点关注（{ct_info['name']}）：
{key_points}

请以JSON格式输出分析结果，格式如下：
{{
    "summary": "总体评价（2-3句话）",
    "risk_level": "低/中/高",
    "risk_count": {{"high": 数字, "medium": 数字, "low": 数字}},
    "risks": [
        {{
            "type": "高/中/低",
            "clause": "涉及的具体条款原文（引用）",
            "problem": "存在的问题或风险",
            "suggestion": "修改建议"
        }}
    ],
    "strengths": ["合同中写得好的地方"],
    "recommendations": ["综合改进建议"]
}}
"""

    user_message = f"请分析以下{ct_info['name']}合同：\n\n{contract_text}"
    
    if custom_focus:
        user_message += f"\n\n⚠️ 用户特别关注：{custom_focus}"
        system_prompt += f"\n\n⚠️ 用户特别关注：{custom_focus}，请重点分析这些方面。"
    
    try:
        headers = {
            'Authorization': f'Bearer {config["api_key"]}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'model': config['model'],
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message},
            ],
            'temperature': 0.3,  # 降低随机性，保持分析稳定性
            'max_tokens': 3000,
        }
        
        response = requests.post(
            f'{config["base_url"]}/chat/completions',
            headers=headers,
            json=payload,
            timeout=60,
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # 尝试解析JSON
            try:
                # 尝试提取JSON部分
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    analysis = json.loads(json_match.group())
                    analysis['success'] = True
                    analysis['provider'] = config['name']
                    return analysis
                else:
                    # 如果没有JSON，把原文返回
                    return {
                        'success': True,
                        'provider': config['name'],
                        'raw_response': content,
                        'summary': content[:200] + '...',
                        'risks': [],
                        'risk_level': '未知',
                    }
            except json.JSONDecodeError:
                return {
                    'success': True,
                    'provider': config['name'],
                    'raw_response': content,
                    'summary': content[:200] + '...',
                    'risks': [],
                    'risk_level': '未知',
                }
        else:
            return {
                'success': False,
                'error': f'API调用失败：{response.status_code} - {response.text}',
            }
            
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'AI分析超时，请稍后重试'}
    except Exception as e:
        return {'success': False, 'error': f'分析失败：{str(e)}'}


def call_ai_clause_explain(clause_text, contract_type):
    """
    解释单个条款的含义和风险
    """
    provider, config = get_available_ai()
    if not provider:
        return {'success': False, 'error': '没有配置AI API密钥'}
    
    ct_info = CONTRACT_TYPES.get(contract_type, CONTRACT_TYPES['other'])
    
    prompt = f"""你是一位专业法律顾问。请用通俗易懂的语言解释以下{ct_info['name']}合同条款：

条款原文：
{clause_text}

请输出JSON格式：
{{
    "plain_language": "用通俗语言解释这条款说了什么",
    "your_rights": "作为签署方，你有什么权利",
    "risks": "这条款可能对你有什么风险",
    "advice": "要不要签这条，有什么建议"
}}
"""
    
    try:
        headers = {
            'Authorization': f'Bearer {config["api_key"]}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'model': config['model'],
            'messages': [
                {'role': 'user', 'content': prompt},
            ],
            'temperature': 0.5,
            'max_tokens': 1000,
        }
        
        response = requests.post(
            f'{config["base_url"]}/chat/completions',
            headers=headers,
            json=payload,
            timeout=30,
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return {'success': True, 'data': json.loads(json_match.group())}
            
            return {'success': True, 'data': {'raw': content}}
        else:
            return {'success': False, 'error': f'API调用失败：{response.status_code}'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}


def call_ai_clause_suggest(clause_text, contract_type, goal):
    """
    为用户提供优化条款的建议
    """
    provider, config = get_available_ai()
    if not provider:
        return {'success': False, 'error': '没有配置AI API密钥'}
    
    ct_info = CONTRACT_TYPES.get(contract_type, CONTRACT_TYPES['other'])
    
    prompt = f"""你是一位专业法律顾问。请为以下{ct_info['name']}合同条款提供优化建议。

原始条款：
{clause_text}

用户希望达成的目标：{goal}

请输出JSON格式：
{{
    "revised_clause": "优化后的条款文本",
    "explanation": "修改的理由说明",
    "notes": "需要注意的要点"
}}
"""
    
    try:
        headers = {
            'Authorization': f'Bearer {config["api_key"]}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'model': config['model'],
            'messages': [
                {'role': 'user', 'content': prompt},
            ],
            'temperature': 0.5,
            'max_tokens': 1500,
        }
        
        response = requests.post(
            f'{config["base_url"]}/chat/completions',
            headers=headers,
            json=payload,
            timeout=30,
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return {'success': True, 'data': json.loads(json_match.group())}
            
            return {'success': True, 'data': {'raw': content}}
        else:
            return {'success': False, 'error': f'API调用失败：{response.status_code}'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ==================== Flask 路由 ====================
@app.route('/')
def index():
    """首页"""
    available_ai = get_available_ai()
    return render_template(
        'index.html',
        contract_types=CONTRACT_TYPES,
        ai_configured=available_ai[0] is not None,
        ai_name=available_ai[1]['name'] if available_ai[1] else None,
    )


@app.route('/review', methods=['POST'])
def review():
    """提交合同进行AI审查"""
    # 获取合同文本
    contract_text = request.form.get('contract_text', '').strip()
    contract_type = request.form.get('contract_type', 'other')
    custom_focus = request.form.get('custom_focus', '').strip()
    
    # 处理文本上传
    text_file = request.files.get('text_file')
    if text_file and text_file.filename:
        try:
            contract_text = text_file.read().decode('utf-8')
        except:
            contract_text = text_file.read().decode('gbk', errors='ignore')
    
    if not contract_text:
        flash('请输入合同文本或上传文件', 'error')
        return redirect(url_for('index'))
    
    if len(contract_text) < 50:
        flash('合同文本太短，请提供更完整的内容', 'error')
        return redirect(url_for('index'))
    
    # 调用AI分析
    result = call_ai_review(contract_text, contract_type, custom_focus)
    
    if result.get('success'):
        return render_template(
            'result.html',
            result=result,
            contract_type=CONTRACT_TYPES.get(contract_type, CONTRACT_TYPES['other']),
            original_text=contract_text[:500] + '...' if len(contract_text) > 500 else contract_text,
        )
    else:
        flash(result.get('error', '分析失败'), 'error')
        return redirect(url_for('index'))


@app.route('/explain', methods=['POST'])
def explain():
    """解释单个条款"""
    clause = request.form.get('clause', '').strip()
    contract_type = request.form.get('contract_type', 'other')
    
    if not clause:
        return jsonify({'success': False, 'error': '请输入要解释的条款'})
    
    result = call_ai_clause_explain(clause, contract_type)
    return jsonify(result)


@app.route('/suggest', methods=['POST'])
def suggest():
    """获取条款优化建议"""
    clause = request.form.get('clause', '').strip()
    contract_type = request.form.get('contract_type', 'other')
    goal = request.form.get('goal', '').strip()
    
    if not clause:
        return jsonify({'success': False, 'error': '请输入要优化的条款'})
    
    result = call_ai_clause_suggest(clause, contract_type, goal)
    return jsonify(result)


# ==================== 启动 ====================
if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║              AI合同风险审查助手 v1.0                      ║
    ║                                                          ║
    ║  📋 智能分析合同风险、识别不公平条款                     ║
    ║  💡 提供通俗易懂的法律建议                               ║
    ║  ✨ 支持劳动合同/租赁/买卖/服务等多种合同类型            ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # 检查AI配置
    provider, config = get_available_ai()
    if provider:
        print(f"✅ AI已配置：{config['name']}")
    else:
        print("⚠️  警告：没有配置AI API密钥，功能将受限！")
        print("   请设置以下任一环境变量：")
        print("   - SILICONFLOW_API_KEY (推荐，免费)")
        print("   - DEEPSEEK_API_KEY")
        print("   - ZHIPU_API_KEY")
        print("   - OPENAI_API_KEY")
        print()
    
    print("🌐 启动服务：http://localhost:5002")
    print("   按 Ctrl+C 停止服务\n")
    
    app.run(host='0.0.0.0', port=5002, debug=True)