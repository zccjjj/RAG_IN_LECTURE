import os
import subprocess
import logging

logger = logging.getLogger(__name__)


def extract_audio(video_path, output_audio_path):
    """从视频中提取音频为 16kHz 单声道 WAV 文件（Whisper 所需格式）"""
    cmd = [
        'ffmpeg', '-i', video_path,
        '-ar', '16000', '-ac', '1',
        '-f', 'wav', '-y',
        output_audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed: {result.stderr}")
    logger.info(f"Audio extracted to {output_audio_path}")
    return output_audio_path


def extract_frames(video_path, output_dir, interval_seconds=5):
    """按指定时间间隔从视频中提取关键帧"""
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f'fps=1/{interval_seconds}',
        '-q:v', '2',
        os.path.join(output_dir, 'frame_%04d.jpg'),
        '-y'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed: {result.stderr}")

    # 返回所有提取的帧文件路径（按文件名排序）
    frames = sorted([
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.endswith('.jpg')
    ])
    logger.info(f"Extracted {len(frames)} frames to {output_dir}")
    return frames


def get_video_duration(video_path):
    """获取视频时长（秒）"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return float(result.stdout.strip())
