import logging
import whisper

logger = logging.getLogger(__name__)


def transcribe_audio(audio_path, model_size="base", language=None):
    """
    使用 Whisper 对音频进行语音识别。

    Args:
        audio_path: 音频文件路径（WAV 格式）
        model_size: Whisper 模型大小 (tiny, base, small, medium, large)
        language: 语言代码，None 为自动检测，"zh" 为中文

    Returns:
        带时间戳的文本段列表: [{"start": float, "end": float, "text": str}, ...]
    """
    logger.info(f"Loading Whisper model: {model_size}")
    model = whisper.load_model(model_size)

    logger.info(f"Transcribing audio: {audio_path}")
    transcribe_options = {"verbose": False}
    if language:
        transcribe_options["language"] = language

    result = model.transcribe(audio_path, **transcribe_options)

    segments = []
    for seg in result["segments"]:
        segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip()
        })

    logger.info(f"Transcription complete: {len(segments)} segments")
    return segments
