import os
import base64
import logging
import requests

logger = logging.getLogger(__name__)


def describe_frame(image_path, ollama_url="http://localhost:11434", model="llava:7b"):
    """
    使用 Ollama 多模态模型描述单帧画面内容。

    Args:
        image_path: 图片文件路径
        ollama_url: Ollama 服务地址
        model: 多模态模型名称

    Returns:
        画面描述文本
    """
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model,
                "prompt": "请用中文简要描述这张教学视频截图中的内容，重点关注文字、图表、公式或关键视觉信息。",
                "images": [img_b64],
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.RequestException as e:
        logger.warning(f"Frame description failed for {image_path}: {e}")
        return ""


def describe_all_frames(frames_dir, ollama_url="http://localhost:11434", model="llava:7b"):
    """
    对目录中的所有帧进行描述。

    Args:
        frames_dir: 帧图片目录
        ollama_url: Ollama 服务地址
        model: 多模态模型名称

    Returns:
        帧描述列表: [{"index": int, "path": str, "description": str}, ...]
    """
    frame_files = sorted([
        f for f in os.listdir(frames_dir)
        if f.endswith('.jpg')
    ])

    descriptions = []
    total = len(frame_files)

    for i, frame_file in enumerate(frame_files):
        frame_path = os.path.join(frames_dir, frame_file)
        logger.info(f"Describing frame {i+1}/{total}: {frame_file}")
        desc = describe_frame(frame_path, ollama_url, model)
        descriptions.append({
            "index": i,
            "path": frame_path,
            "description": desc
        })

    logger.info(f"Frame description complete: {len(descriptions)} frames")
    return descriptions
