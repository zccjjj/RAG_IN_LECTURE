import os
import time
import base64
import logging
import hashlib
import requests
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def image_hash(image_path):
    """计算图片的感知哈希（用于判断相似帧）"""
    img = Image.open(image_path).convert('L').resize((8, 8))
    pixels = np.array(img)
    avg = pixels.mean()
    return ''.join('1' if p > avg else '0' for p in pixels.flatten())


def frames_similar(hash1, hash2, threshold=0.95):
    """比较两个帧的相似度"""
    if not hash1 or not hash2:
        return False
    same_bits = sum(a == b for a, b in zip(hash1, hash2))
    return (same_bits / len(hash1)) >= threshold


def describe_frame(image_path, ollama_url="http://localhost:11434", model="llava:7b",
                   timeout=90, max_retries=2):
    """使用 Ollama 多模态模型描述单帧画面内容，带重试机制。"""
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": "请用中文简要描述这张教学视频截图中的内容，重点关注文字、图表、公式或关键视觉信息。限50字以内。",
                    "images": [img_b64],
                    "stream": False
                },
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()["response"]
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                wait = 3 * (attempt + 1)
                logger.warning(f"Frame description attempt {attempt+1} failed, retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                logger.warning(f"Frame description failed after {max_retries+1} attempts: {image_path}: {e}")
                return ""


def describe_all_frames(frames_dir, ollama_url="http://localhost:11434", model="llava:7b",
                        timeout=90, max_retries=2, similarity_threshold=0.95):
    """对目录中的所有帧进行描述，跳过相似帧以提升速度。"""
    frame_files = sorted([
        f for f in os.listdir(frames_dir)
        if f.endswith('.jpg')
    ])

    descriptions = []
    total = len(frame_files)
    prev_hash = None
    skipped = 0

    for i, frame_file in enumerate(frame_files):
        frame_path = os.path.join(frames_dir, frame_file)

        # 计算帧哈希，跳过相似帧
        curr_hash = image_hash(frame_path)
        if frames_similar(prev_hash, curr_hash, similarity_threshold):
            skipped += 1
            descriptions.append({
                "index": i,
                "path": frame_path,
                "description": descriptions[-1]["description"] if descriptions else ""
            })
            continue

        prev_hash = curr_hash
        logger.info(f"Describing frame {i+1}/{total}: {frame_file}")
        desc = describe_frame(frame_path, ollama_url, model, timeout, max_retries)
        descriptions.append({
            "index": i,
            "path": frame_path,
            "description": desc
        })

    logger.info(f"Frame description complete: {total} frames, {skipped} skipped (similar)")
    return descriptions
