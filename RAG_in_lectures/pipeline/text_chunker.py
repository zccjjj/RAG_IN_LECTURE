import logging

logger = logging.getLogger(__name__)


def format_time(seconds):
    """将秒数格式化为 MM:SS"""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


def create_chunks(transcript_segments, frame_descriptions, frame_interval=5,
                  chunk_duration=30, chunk_overlap=10):
    """
    将语音转写文本和帧描述按时间窗口合并为文本块。

    Args:
        transcript_segments: Whisper 输出的文本段 [{"start", "end", "text"}, ...]
        frame_descriptions: 帧描述列表 [{"index", "description"}, ...]
        frame_interval: 帧提取间隔（秒）
        chunk_duration: 每个块覆盖的时间长度（秒）
        chunk_overlap: 相邻块的重叠时间（秒）

    Returns:
        chunks 列表: [{"text": str, "start": float, "end": float}, ...]
    """
    if not transcript_segments:
        logger.warning("No transcript segments provided")
        return []

    # 计算视频总时长
    video_duration = max(seg["end"] for seg in transcript_segments)

    chunks = []
    start = 0.0

    while start < video_duration:
        end = min(start + chunk_duration, video_duration)

        # 收集该时间窗口内的语音文本
        audio_texts = []
        for seg in transcript_segments:
            if seg["start"] >= start and seg["start"] < end:
                audio_texts.append(seg["text"])
            elif seg["end"] > start and seg["start"] < end:
                audio_texts.append(seg["text"])

        audio_text = " ".join(audio_texts).strip()

        # 收集该时间窗口内的帧描述
        visual_texts = []
        for frame_desc in frame_descriptions:
            frame_time = frame_desc["index"] * frame_interval
            if start <= frame_time < end and frame_desc["description"]:
                visual_texts.append(frame_desc["description"])

        visual_text = " ".join(visual_texts).strip()

        # 组合成完整的 chunk 文本
        chunk_text = f"[时间段 {format_time(start)}-{format_time(end)}]\n"
        if audio_text:
            chunk_text += f"语音内容: {audio_text}\n"
        if visual_text:
            chunk_text += f"画面内容: {visual_text}"

        chunk_text = chunk_text.strip()

        if audio_text or visual_text:  # 跳过空 chunk
            chunks.append({
                "text": chunk_text,
                "start": start,
                "end": end
            })

        start += (chunk_duration - chunk_overlap)

    logger.info(f"Created {len(chunks)} text chunks")
    return chunks
