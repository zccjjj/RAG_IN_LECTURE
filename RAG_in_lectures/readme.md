目标：做一个用于教学场景的工具。
工具描述：用户通过一个前端页面上传一段约10分钟的视频素材，然后对视频素材进行提问，工具会根据视频内容回答用户的问题。

工具使用流程：
1. 用户通过前端页面上传视频素材和问题列表。
2. 后端接收视频素材并进行预处理，包括分割视频为多个片段和生成问题列表，包括构造一个向量数据库，便于大模型检索增强生成。
3. 后端使用大模型对视频素材进行理解，并生成答案。
4. 后端将生成的答案返回给前端。
5. 前端展示问题和答案。
6. 后端提供一个下载链接，用户可以下载包含所有问题列表和答案的文档。

工具特点：
1. 基于视频构造向量数据库。
2. 使用纯文本大模型进行检索增强生成。

---

## 技术架构

- 前端：HTML + CSS + JavaScript（无框架）
- 后端：Python Flask
- 向量数据库：FAISS
- 大模型：Ollama 本地托管（qwen2.5:7b 文本 + llava:7b 视觉）
- 语音识别：OpenAI Whisper
- 嵌入模型：sentence-transformers (BAAI/bge-small-zh-v1.5)
- 视频处理：ffmpeg
- 文档导出：python-docx

## 项目结构

```
├── app.py                      # Flask 主入口
├── config.py                   # 配置常量
├── requirements.txt            # Python 依赖
├── pipeline/
│   ├── video_processor.py      # 音频提取、关键帧提取
│   ├── audio_transcriber.py    # Whisper 语音转文字
│   ├── frame_describer.py      # Ollama llava 帧描述
│   ├── text_chunker.py         # 时间对齐文本分块
│   ├── embedding.py            # 向量化模型
│   └── vector_store.py         # FAISS 索引
├── utils/
│   ├── qa_engine.py            # RAG 问答引擎
│   └── document_export.py      # Word 文档导出
├── static/
│   ├── css/style.css
│   └── js/main.js
├── templates/
│   └── index.html
├── uploads/                    # 上传的视频
├── processing/                 # 处理中间产物
└── results/                    # 生成的文档
```

## 环境准备

### 1. 系统依赖

```bash
# 安装 ffmpeg
sudo apt install ffmpeg
```

### 2. Ollama 模型

```bash
# 安装 Ollama（如未安装）
curl -fsSL https://ollama.com/install.sh | sh

# 拉取所需模型
ollama pull qwen2.5:7b      # 文本问答模型
ollama pull llava:7b         # 视觉描述模型
```

### 3. Python 依赖

```bash
pip install -r requirements.txt
```

## 启动方式

```bash
# 确保 Ollama 正在运行
ollama serve

# 启动 Flask 服务
python app.py
```

访问 http://localhost:5000 即可使用。

## 使用方法

1. 打开浏览器访问 http://localhost:5000
2. 上传一个教学视频文件（支持 MP4/AVI/MKV/MOV/WebM）
3. 在文本框中输入问题（每行一个问题）
4. 点击"开始处理"，等待系统完成视频分析
5. 查看生成的答案，或点击"下载文档"获取 Word 文件

## 处理流程说明

1. **音频提取**：使用 ffmpeg 从视频中提取 16kHz 单声道 WAV 音频
2. **关键帧提取**：每 5 秒截取一帧画面
3. **语音识别**：Whisper 模型将音频转为带时间戳的文本
4. **帧描述**：Ollama llava 模型描述每帧的视觉内容
5. **文本分块**：按 30 秒窗口（10 秒重叠）合并音频文本和帧描述
6. **向量索引**：使用 sentence-transformers 向量化，构建 FAISS 索引
7. **问答生成**：对每个问题检索最相关的文本块，送入 LLM 生成答案
8. **文档导出**：将问答结果保存为 Word 文档

## 配置说明

编辑 `config.py` 可调整以下参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| FRAME_INTERVAL_SECONDS | 5 | 帧提取间隔（秒）|
| WHISPER_MODEL_SIZE | "base" | Whisper 模型大小 |
| CHUNK_DURATION_SECONDS | 30 | 文本块时长（秒）|
| CHUNK_OVERLAP_SECONDS | 10 | 块重叠时长（秒）|
| TOP_K_RETRIEVAL | 4 | 每问题检索的块数 |
| OLLAMA_TEXT_MODEL | "qwen2.5:7b" | 文本模型 |
| OLLAMA_VISION_MODEL | "llava:7b" | 视觉模型 |