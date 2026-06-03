#好人脸识别系统 

基于 Face Recognition 库的人脸识别系统，支持照片训练和实时摄像头测试。

## 功能特性

- 📷 **摄像头实时识别** - 调用本地摄像头实时检测并识别出人脸
- 👤 **照片训练** - 上传单张照片并输入姓名标签进行模型训练
- 📊 **人脸数据库管理** - 查看已训练的人脸标签列表
- 🗑️ **一键清空** - 清空整个人脸数据库和训练好的模型

## 技术栈

- Python 3.8+
- face_recognition（基于 dlib）
- OpenCV
- Flask Web界面
- SQLite（存储人脸特征）

## 安装步骤

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行（首次运行会自动下载 dlib 模型约60MB）
python app.py
```

## 使用方法

### 1. 训练人脸
- 点击"添加人员"按钮
- 上传单张照片（建议正面、清晰、光照均匀）
- 输入姓名标签
- 点击"开始训练"

### 2. 摄像头测试
- 点击"打开摄像头"按钮
- 系统会自动检测画面中的人脸
- 识别成功后在对应人脸框上显示姓名标签
- 识别失败显示"Unknown"

### 3. 清空数据库
- 点击"清空数据库"按钮
- 确认后删除所有训练数据和模型

## 运行

```bash
python app.py
```

然后打开浏览器访问 http://localhost:5000

## 项目结构

```
face_recognition_system/
├── app.py              # Flask主应用
├── requirements.txt    # 依赖列表
├── README.md           # 说明文档
├── templates/          # HTML模板
│   └── index.html
├── static/            # 静态文件
│   └── style.css
├── dataset/          # 训练照片目录(自动创建)
├── train.py           # 人脸训练模块
└── recognizer.py      # 人脸识别模块
```

## 注意事项

- 首次运行会自动下载 dlib 人脸检测模型（约60MB）
- 建议使用清晰、正面、光照均匀的照片进行训练
- 支持 JPG/PNG 格式
- 摄像头测试需要电脑有可用摄像头

---

_Made with ❤️ by 俞 + OpenClaw_