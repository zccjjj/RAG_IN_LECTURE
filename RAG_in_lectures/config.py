import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PROCESSING_DIR = os.path.join(BASE_DIR, "processing")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Flask
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mkv', 'mov', 'webm'}

# Video Processing
FRAME_INTERVAL_SECONDS = 10  # Extract 1 frame per N seconds (10s for better performance)
WHISPER_MODEL_SIZE = "base"  # tiny, base, small, medium, large
WHISPER_LANGUAGE = None  # None for auto-detect, "zh" for Chinese, "en" for English

# Frame Description
FRAME_DESCRIBE_TIMEOUT = 90  # Timeout per frame (seconds)
FRAME_DESCRIBE_MAX_RETRIES = 2  # Max retries per frame
FRAME_SIMILARITY_THRESHOLD = 0.95  # Skip frames with similarity above this

# Chunking
CHUNK_DURATION_SECONDS = 30  # Each chunk covers 30 seconds of video
CHUNK_OVERLAP_SECONDS = 10   # Overlap between consecutive chunks

# Embedding
EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5"  # Chinese embedding model
EMBEDDING_DIMENSION = 512

# FAISS
TOP_K_RETRIEVAL = 4  # Number of chunks to retrieve per question

# Ollama
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_TEXT_MODEL = "qwen2.5:7b"
OLLAMA_VISION_MODEL = "llava:7b"
OLLAMA_TIMEOUT = 120
OLLAMA_MAX_RETRIES = 3  # Max retries for Ollama API calls

# LLM Parameters
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 1024
