import os
import uuid
import json
import logging
import threading

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS

import config
from pipeline.video_processor import extract_audio, extract_frames
from pipeline.audio_transcriber import transcribe_audio
from pipeline.frame_describer import describe_all_frames
from pipeline.text_chunker import create_chunks
from pipeline.embedding import EmbeddingModel
from pipeline.vector_store import VectorStore
from utils.qa_engine import answer_questions
from utils.document_export import generate_document

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask 应用
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
CORS(app)

# 全局状态存储
processing_status = {}

# 全局嵌入模型（延迟加载）
_embedding_model = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel(config.EMBEDDING_MODEL_NAME)
    return _embedding_model


def update_status(session_id, stage, progress, error=None, results=None, doc_path=None):
    """更新处理状态"""
    processing_status[session_id] = {
        "stage": stage,
        "progress": progress,
        "error": error,
        "results": results,
        "doc_path": doc_path
    }


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


def process_video_pipeline(session_id, video_path, questions, language=None):
    """主处理流水线（在后台线程中运行）"""
    session_dir = os.path.join(config.PROCESSING_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    try:
        # Stage 1: 提取音频和关键帧
        update_status(session_id, "正在提取音频和关键帧...", 10)
        audio_path = os.path.join(session_dir, "audio.wav")
        frames_dir = os.path.join(session_dir, "frames")

        extract_audio(video_path, audio_path)
        frames = extract_frames(video_path, frames_dir, config.FRAME_INTERVAL_SECONDS)

        # Stage 2: 语音识别
        update_status(session_id, "正在进行语音识别...", 25)
        whisper_language = language or config.WHISPER_LANGUAGE
        segments = transcribe_audio(
            audio_path,
            model_size=config.WHISPER_MODEL_SIZE,
            language=whisper_language
        )

        # 保存转写结果
        with open(os.path.join(session_dir, "transcription.json"), "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)

        # Stage 3: 帧描述
        update_status(session_id, "正在分析视频画面...", 45)
        frame_descriptions = describe_all_frames(
            frames_dir,
            ollama_url=config.OLLAMA_BASE_URL,
            model=config.OLLAMA_VISION_MODEL,
            timeout=config.FRAME_DESCRIBE_TIMEOUT,
            max_retries=config.FRAME_DESCRIBE_MAX_RETRIES,
            similarity_threshold=config.FRAME_SIMILARITY_THRESHOLD
        )

        # 保存帧描述
        with open(os.path.join(session_dir, "descriptions.json"), "w", encoding="utf-8") as f:
            json.dump(frame_descriptions, f, ensure_ascii=False, indent=2)

        # Stage 4: 文本分块
        update_status(session_id, "正在构建文本块...", 65)
        chunks = create_chunks(
            segments,
            frame_descriptions,
            frame_interval=config.FRAME_INTERVAL_SECONDS,
            chunk_duration=config.CHUNK_DURATION_SECONDS,
            chunk_overlap=config.CHUNK_OVERLAP_SECONDS
        )

        # Stage 5: 构建向量索引
        update_status(session_id, "正在构建向量数据库...", 75)
        embedding_model = get_embedding_model()
        chunk_texts = [c["text"] for c in chunks]
        embeddings = embedding_model.encode(chunk_texts)

        vector_store = VectorStore(dimension=embedding_model.dimension)
        vector_store.build(chunks, embeddings)
        vector_store.save(session_dir)

        # Stage 6: 问答
        update_status(session_id, "正在生成答案...", 85)
        results = answer_questions(
            questions,
            vector_store,
            embedding_model,
            ollama_url=config.OLLAMA_BASE_URL,
            model=config.OLLAMA_TEXT_MODEL,
            top_k=config.TOP_K_RETRIEVAL
        )

        # Stage 7: 导出文档
        update_status(session_id, "正在生成文档...", 95)
        doc_path = generate_document(session_id, results, config.RESULTS_DIR)

        # 保存结果
        with open(os.path.join(session_dir, "results.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        # 完成
        update_status(session_id, "completed", 100, results=results, doc_path=doc_path)
        logger.info(f"Session {session_id} processing completed")

    except Exception as e:
        logger.error(f"Session {session_id} processing failed: {e}", exc_info=True)
        update_status(session_id, "error", 0, error=str(e))


# ========== 路由 ==========

@app.route('/')
def index():
    """前端页面"""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_video():
    """接收视频文件和问题列表"""
    # 检查视频文件
    if 'video' not in request.files:
        return jsonify({"error": "未上传视频文件"}), 400

    video_file = request.files['video']
    if video_file.filename == '':
        return jsonify({"error": "未选择文件"}), 400

    if not allowed_file(video_file.filename):
        return jsonify({"error": f"不支持的文件格式，支持: {', '.join(config.ALLOWED_EXTENSIONS)}"}), 400

    # 获取问题列表
    questions_text = request.form.get('questions', '')
    if not questions_text.strip():
        return jsonify({"error": "请提供至少一个问题"}), 400

    # 解析问题（每行一个问题）
    questions = [q.strip() for q in questions_text.strip().split('\n') if q.strip()]
    if not questions:
        return jsonify({"error": "请提供至少一个问题"}), 400

    # 获取语言设置
    language = request.form.get('language', '').strip() or None

    # 生成 session_id
    session_id = str(uuid.uuid4())[:8]

    # 保存视频文件
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    ext = video_file.filename.rsplit('.', 1)[1].lower()
    video_path = os.path.join(config.UPLOAD_DIR, f"{session_id}.{ext}")
    video_file.save(video_path)

    # 初始化状态
    update_status(session_id, "已接收，准备处理...", 5)

    # 启动后台处理线程
    thread = threading.Thread(
        target=process_video_pipeline,
        args=(session_id, video_path, questions, language),
        daemon=True
    )
    thread.start()

    return jsonify({
        "session_id": session_id,
        "questions_count": len(questions),
        "message": "视频已上传，开始处理"
    })


@app.route('/api/status/<session_id>', methods=['GET'])
def get_status(session_id):
    """获取处理状态"""
    status = processing_status.get(session_id)
    if not status:
        return jsonify({"error": "会话不存在"}), 404

    return jsonify({
        "stage": status["stage"],
        "progress": status["progress"],
        "error": status["error"]
    })


@app.route('/api/results/<session_id>', methods=['GET'])
def get_results(session_id):
    """获取问答结果"""
    status = processing_status.get(session_id)
    if not status:
        return jsonify({"error": "会话不存在"}), 404

    if status["stage"] != "completed":
        return jsonify({"error": "处理尚未完成"}), 400

    return jsonify({
        "results": status["results"]
    })


@app.route('/api/download/<session_id>', methods=['GET'])
def download_document(session_id):
    """下载问答结果文档"""
    status = processing_status.get(session_id)
    if not status:
        return jsonify({"error": "会话不存在"}), 404

    if status["stage"] != "completed" or not status.get("doc_path"):
        return jsonify({"error": "文档尚未生成"}), 400

    doc_path = status["doc_path"]
    if not os.path.exists(doc_path):
        return jsonify({"error": "文档文件不存在"}), 404

    return send_file(
        doc_path,
        as_attachment=True,
        download_name=f"video_qa_{session_id}.docx",
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


if __name__ == '__main__':
    # 确保必要目录存在
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    os.makedirs(config.PROCESSING_DIR, exist_ok=True)
    os.makedirs(config.RESULTS_DIR, exist_ok=True)

    logger.info("Starting RAG Video QA Server...")
    logger.info(f"Ollama URL: {config.OLLAMA_BASE_URL}")
    logger.info(f"Text Model: {config.OLLAMA_TEXT_MODEL}")
    logger.info(f"Vision Model: {config.OLLAMA_VISION_MODEL}")

    app.run(host='0.0.0.0', port=5000, debug=True)
