from flask import Flask, jsonify, request
from flask_cors import CORS
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# 简化 CORS 配置 - 允许所有来源和所有方法
CORS(app, 
     origins="*",
     methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
     supports_credentials=False)

# 确保所有响应都包含 CORS 头（双重保险）
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, Accept")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PATCH, PUT, DELETE, OPTIONS")
    response.headers.add("Access-Control-Max-Age", "3600")
    return response

# Supabase 配置（使用 service_role key，和 test_api.py 一致）
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://qvikvgutnvjxmfbxsqcn.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2aWt2Z3V0bnZqeG1mYnhzcWNuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NDMyNTk1OCwiZXhwIjoyMDc5OTAxOTU4fQ.qdGx619JaeY-lHw584TUu1uDW1ChNm4W3DvGPvAmJds')

# 初始化 Supabase 客户端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.route('/api/calls', methods=['GET'])
def get_calls():
    """获取所有 call 列表"""
    try:
        print(f"[API] 收到请求: GET /api/calls")
        # 查询所有 call，按创建时间倒序，限制 50 条
        response = supabase.table('n8n_voice_feedback')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(50)\
            .execute()
        
        calls = response.data
        print(f"[API] 查询到 {len(calls)} 条记录")
        
        # 处理数据，计算轮次数
        import json
        for call in calls:
            # 如果有 conversations 字段，计算轮次数
            conversations = call.get('conversations')
            if conversations:
                try:
                    # 如果是字符串，尝试解析 JSON
                    if isinstance(conversations, str):
                        # 检查是否是空字符串或无效 JSON
                        conversations_str = conversations.strip()
                        if not conversations_str or conversations_str == 'null':
                            conversations = None
                        else:
                            conversations = json.loads(conversations_str)
                    # 如果已经是字典，直接使用
                    elif isinstance(conversations, dict):
                        pass  # 已经是字典，不需要处理
                    else:
                        conversations = None
                except (json.JSONDecodeError, ValueError) as e:
                    # JSON 解析失败，记录错误但继续处理
                    print(f"[API] 警告: 无法解析 conversations (call_sid: {call.get('call_sid', 'unknown')}): {e}")
                    conversations = None
                
                # 计算轮次数
                if conversations and isinstance(conversations, dict):
                    call['rounds'] = len(conversations)
                else:
                    call['rounds'] = 0
            else:
                call['rounds'] = call.get('current_round', 0)
        
        result = {
            'success': True,
            'data': calls,
            'count': len(calls)
        }
        print(f"[API] 返回结果: success={result['success']}, count={result['count']}")
        return jsonify(result)
    
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"[API] 错误: {error_msg}")
        print(f"[API] 错误堆栈: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@app.route('/api/calls/<call_sid>', methods=['GET'])
def get_call(call_sid):
    """获取单个 call 的详细信息"""
    try:
        response = supabase.table('n8n_voice_feedback')\
            .select('*')\
            .eq('call_sid', call_sid)\
            .execute()
        
        if not response.data:
            return jsonify({
                'success': False,
                'error': 'Call not found'
            }), 404
        
        call = response.data[0]
        
        # 解析 conversations
        import json
        conversations = call.get('conversations')
        if conversations:
            try:
                if isinstance(conversations, str):
                    conversations_str = conversations.strip()
                    if not conversations_str or conversations_str == 'null':
                        call['conversations'] = None
                    else:
                        call['conversations'] = json.loads(conversations_str)
                elif isinstance(conversations, dict):
                    pass  # 已经是字典，不需要处理
                else:
                    call['conversations'] = None
            except (json.JSONDecodeError, ValueError) as e:
                print(f"[API] 警告: 无法解析 conversations (call_sid: {call_sid}): {e}")
                call['conversations'] = None
        
        return jsonify({
            'success': True,
            'data': call
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/calls/<call_sid>/feedback', methods=['PATCH', 'POST'])
def update_feedback(call_sid):
    """更新或提交反馈"""
    try:
        data = request.get_json()
        
        # 准备更新数据
        update_data = {}
        
        # Legacy fields (for backward compatibility)
        if 'is_appropriate' in data:
            update_data['is_appropriate'] = data['is_appropriate']
        
        if 'issue_type' in data:
            update_data['issue_type'] = data['issue_type']
        
        if 'audio_issues' in data:
            update_data['audio_issues'] = data['audio_issues']
        
        # New structured fields
        if 'asr_issues' in data:
            update_data['asr_issues'] = data['asr_issues']
        
        if 'tts_issues' in data:
            update_data['tts_issues'] = data['tts_issues']
        
        if 'text_issues' in data:
            update_data['text_issues'] = data['text_issues']
        
        # Description fields
        if 'asr_other_description' in data:
            update_data['asr_other_description'] = data['asr_other_description']
        
        if 'tts_other_description' in data:
            update_data['tts_other_description'] = data['tts_other_description']
        
        if 'text_other_description' in data:
            update_data['text_other_description'] = data['text_other_description']
        
        if 'description' in data:
            update_data['description'] = data['description']
        
        if 'preferred_response' in data:
            update_data['preferred_response'] = data['preferred_response']
        
        if 'bug_description' in data:
            update_data['bug_description'] = data['bug_description']
        
        if 'advice' in data:
            update_data['advice'] = data['advice']
        
        # Round-specific feedbacks
        if 'round_feedbacks' in data:
            update_data['round_feedbacks'] = data['round_feedbacks']
        
        # 更新数据库
        response = supabase.table('n8n_voice_feedback')\
            .update(update_data)\
            .eq('call_sid', call_sid)\
            .execute()
        
        if not response.data:
            return jsonify({
                'success': False,
                'error': 'Call not found or update failed'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Feedback submitted successfully',
            'data': response.data[0] if response.data else None
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'success': True,
        'message': 'API is running',
        'supabase_url': SUPABASE_URL
    })


if __name__ == '__main__':
    PORT = 5010
    
    print(f"Starting Flask server...")
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"API will be available at: http://localhost:{PORT}")
    print(f"Test endpoint: http://localhost:{PORT}/api/health")
    print(f"CORS enabled for all origins")
    print(f"\n等待请求...")
    app.run(debug=True, port=PORT, host='127.0.0.1')
