#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人脸识别系统 - Flask Web应用
功能：照片训练 + 摄像头实时识别
"""

import os
import cv2
import numpy as np
import base64
import shutil
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'dataset'
app.config['ENCODINGS_FILE'] = 'face_encodings.pkl'

# 确保目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

# 全局变量存储人脸数据
face_database = {}  # {name: [encodings...]}
names_list = []  # 已训练的人员名单
# 识别记录（前端轮询获取）
recognition_log = []  # list of {'name': str, 'time': 'YYYY-MM-DD HH:MM:SS'}
# 用于防止短时间内重复记录同一人
last_seen = {}  # name -> datetime


def load_encodings():
    """加载已保存的人脸编码"""
    global face_database, names_list
    if os.path.exists(app.config['ENCODINGS_FILE']):
        import pickle
        with open(app.config['ENCODINGS_FILE'], 'rb') as f:
            data = pickle.load(f)
            face_database = data.get('database', {})
            names_list = data.get('names', [])
    else:
        face_database = {}
        names_list = []


def save_encodings():
    """保存人脸编码到文件"""
    import pickle
    with open(app.config['ENCODINGS_FILE'], 'wb') as f:
        pickle.dump({
            'database': face_database,
            'names': names_list
        }, f)


def init_face_recognition():
    """初始化dlib人脸检测器（延迟加载）"""
    import face_recognition
    return face_recognition


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg', 'png'}


def get_face_encoding(fr, image_path):
    """从图片获取人脸编码"""
    try:
        # 读取图片，face_recognition.load_image_file 返回的是 RGB 图像
        image = fr.load_image_file(image_path)

        # 如果是灰度图或带透明通道的图像，则规范为 RGB
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)

        rgb_image = image

        # 获取人脸编码
        encodings = fr.face_encodings(rgb_image)

        if len(encodings) == 0:
            return None, "未检测到人脸，请上传清晰正面照片"
        elif len(encodings) > 1:
            return None, "检测到多个人脸，请上传单人照片"

        return encodings[0], "OK"
    except Exception as e:
        return None, f"处理失败: {str(e)}"


@app.route('/')
def index():
    """主页"""
    load_encodings()
    return render_template('index.html', names=names_list)


@app.route('/api/add_person', methods=['POST'])
def add_person():
    """添加人员：上传照片进行训练"""
    try:
        # 获取请求数据
        data = request.get_json(silent=True) or {}
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'success': False, 'message': '请输入姓名'})
        
        if name in face_database:
            return jsonify({'success': False, 'message': f'姓名"{name}"已存在，请使用其他姓名'})
        
        # 检查是否有待处理的图片数据
        image_data = data.get('image_data', '')
        if not image_data:
            return jsonify({'success': False, 'message': '请上传照片'})
        
        # 保存临时图片
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{name}_{timestamp}.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # 解码base64图片
        try:
            # 移除data:image/jpeg;base64,前缀
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
        except Exception as e:
            return jsonify({'success': False, 'message': f'图片保存失败: {str(e)}'})
        
        # 延迟导入face_recognition
        import face_recognition as fr
        
        # 获取人脸编码
        encoding, msg = get_face_encoding(fr, filepath)
        
        if encoding is None:
            os.remove(filepath)  # 删除无效图片
            return jsonify({'success': False, 'message': msg})
        
        # 添加到数据库
        face_database[name] = [encoding.tolist()]
        names_list.append(name)
        save_encodings()
        
        # 删除临时图片
        os.remove(filepath)
        
        return jsonify({
            'success': True, 
            'message': f'✅ {name} 训练成功！',
            'count': len(names_list)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'错误: {str(e)}'})


@app.route('/api/delete_person', methods=['POST'])
def delete_person():
    """删除指定人员"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if name in face_database:
            del face_database[name]
            names_list.remove(name)
            save_encodings()
            return jsonify({'success': True, 'message': f'已删除 {name}'})
        else:
            return jsonify({'success': False, 'message': '未找到该人员'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'错误: {str(e)}'})


@app.route('/api/clear_all', methods=['POST'])
def clear_all():
    """清空所有人脸数据"""
    try:
        global face_database, names_list
        face_database = {}
        names_list = []
        save_encodings()
        
        # 清空数据集目录
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            shutil.rmtree(app.config['UPLOAD_FOLDER'])
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        return jsonify({'success': True, 'message': '数据库已清空'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'错误: {str(e)}'})


@app.route('/api/get_names', methods=['GET'])
def get_names():
    """获取已训练人员列表"""
    load_encodings()
    return jsonify({'success': True, 'names': names_list, 'count': len(names_list)})


@app.route('/api/get_results', methods=['GET'])
def get_results():
    """返回近期的识别记录（不清空，前端可根据时间去重）"""
    # 返回最近 N 条记录
    recent = recognition_log[-100:]
    return jsonify({'success': True, 'results': recent})


def gen_frames():
    """生成摄像头帧，用于实时显示"""
    import face_recognition as fr
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return
    
    load_encodings()  # 加载最新的人脸数据
    
    # 转换已存储的编码
    known_encodings = []
    known_names = []
    
    for name, encodings_list in face_database.items():
        for enc in encodings_list:
            known_encodings.append(np.array(enc))
            known_names.append(name)
    
    print(f"[INFO] 已加载 {len(known_names)} 个人脸数据")
    
    process_this_frame = True
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 小尺寸处理提高性能
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # 每隔一帧处理一次
            if process_this_frame:
                face_locations = fr.face_locations(rgb_frame, number_of_times_to_upsample=1)
                face_encodings = fr.face_encodings(rgb_frame, face_locations)
                
                face_names = []
                for encoding in face_encodings:
                    matches = fr.compare_faces(known_encodings, encoding, tolerance=0.4)
                    name = "Unknown"
                    
                    # 找最佳匹配
                    face_distances = fr.face_distance(known_encodings, encoding)
                    if len(face_distances) > 0:
                        best_match_idx = np.argmin(face_distances)
                        if matches[best_match_idx]:
                            name = known_names[best_match_idx]
                    
                    face_names.append(name)

                # 将识别事件记录到 recognition_log（避免短时间重复）
                for name in face_names:
                    if name != "Unknown":
                        now = datetime.now()
                        prev = last_seen.get(name)
                        # 只有当上次记录时间超过 5 秒才追加新记录
                        if prev is None or (now - prev).total_seconds() > 5:
                            ts = now.strftime('%Y-%m-%d %H:%M:%S')
                            recognition_log.append({'name': name, 'time': ts})
                            # 保持日志最大长度
                            if len(recognition_log) > 200:
                                recognition_log.pop(0)
                            last_seen[name] = now
            
            process_this_frame = not process_this_frame
            
            # 绘制结果（坐标要放大4倍）
            for (top, right, bottom, left), name in zip(face_locations, face_names):
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
                
                # 框的颜色
                if name == "Unknown":
                    color = (0, 0, 255)  # 红色
                else:
                    color = (0, 255, 0)  # 绿色
                
                # 画框
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                
                # 画名字背景
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                
                # 写名字
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.8, (255, 255, 255), 1)
            
            # 编码为jpeg
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    finally:
        cap.release()


@app.route('/video_feed')
def video_feed():
    """摄像头视频流"""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/camera_status', methods=['GET'])
def camera_status():
    """检查摄像头是否可用"""
    cap = cv2.VideoCapture(0)
    status = cap.isOpened()
    cap.release()
    return jsonify({'success': True, 'available': status})


if __name__ == '__main__':
    print("=" * 50)
    print("🎯 人脸识别系统启动中...")
    print("📍 访问地址: http://localhost:5000")
    print("=" * 50)
    
    load_encodings()
    print(f"[INFO] 已加载 {len(names_list)} 个已训练人员")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)