"""
FFmpeg utility functions.

Wrappers around FFmpeg CLI for common video processing operations.
All functions use subprocess to call FFmpeg and return structured results.

SECURITY: All user-provided inputs are sanitized before passing to
subprocess. File paths are validated, resolutions are regex-checked,
and all calls go through a single safe wrapper with a timeout.
"""

import json
import logging
import os
import re
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default subprocess timeout (seconds) — prevents hanging on malformed files
DEFAULT_TIMEOUT = 600  # 10 minutes

# Regex patterns for input validation
_RESOLUTION_PATTERN = re.compile(r"^\d{2,5}x\d{2,5}$")
_SAFE_THRESHOLD_PATTERN = re.compile(r"^-?\d{1,3}dB$")


def _validate_file_path(path: str, label: str = "path") -> None:
    """Validate that a file path is safe for subprocess use.

    Checks for shell metacharacters and null bytes that could
    enable command injection.

    Args:
        path: The file path to validate.
        label: Human-readable label for error messages.

    Raises:
        ValueError: If the path contains dangerous characters.
    """
    if not path:
        raise ValueError(f"{label} cannot be empty")
    if "\x00" in path:
        raise ValueError(f"{label} contains null bytes")
    # Reject obvious shell metacharacters
    dangerous_chars = set(";|&$`!><()\n\r")
    found = dangerous_chars.intersection(path)
    if found:
        raise ValueError(
            f"{label} contains unsafe characters: {found}"
        )


def _validate_resolution(resolution: str) -> tuple[str, str]:
    """Validate and parse a resolution string.

    Args:
        resolution: Resolution in 'WxH' format (e.g., '1080x1920').

    Returns:
        A tuple of (width, height) as validated strings.

    Raises:
        ValueError: If the resolution format is invalid.
    """
    if not _RESOLUTION_PATTERN.match(resolution):
        raise ValueError(
            f"Invalid resolution format: '{resolution}'. "
            f"Expected format: 'WIDTHxHEIGHT' (e.g., '1080x1920')"
        )
    width, height = resolution.split("x")
    # Sanity check: reject absurd dimensions
    if int(width) > 7680 or int(height) > 7680:
        raise ValueError(f"Resolution exceeds maximum (7680x7680): {resolution}")
    return width, height


def _run_ffmpeg(
    args: List[str],
    check: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
) -> subprocess.CompletedProcess:
    """Execute an FFmpeg command safely.

    All FFmpeg calls MUST go through this wrapper. It enforces
    a timeout, captures output, and avoids shell execution.

    Args:
        args: List of command-line arguments (without 'ffmpeg' prefix).
        check: If True, raise CalledProcessError on non-zero exit.
        timeout: Maximum execution time in seconds.

    Returns:
        The completed process result.

    Raises:
        subprocess.CalledProcessError: If FFmpeg exits with error and check=True.
        subprocess.TimeoutExpired: If the process exceeds the timeout.
        FileNotFoundError: If FFmpeg is not installed.
    """
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args
    logger.debug("Running FFmpeg: %s", " ".join(cmd))
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=check,
        timeout=timeout,
        shell=False,  # Explicit: never use shell
    )


def _run_ffprobe(
    args: List[str],
    timeout: int = 60,
) -> subprocess.CompletedProcess:
    """Execute an FFprobe command safely.

    Args:
        args: List of command-line arguments (without 'ffprobe' prefix).
        timeout: Maximum execution time in seconds.

    Returns:
        The completed process result.

    Raises:
        subprocess.TimeoutExpired: If the process exceeds the timeout.
    """
    cmd = ["ffprobe", "-hide_banner"] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
        shell=False,
    )


def extract_audio(
    video_path: str,
    output_path: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Extract audio track from a video file.

    Args:
        video_path: Path to the input video file.
        output_path: Path for the output audio file. If None,
                     uses the input path with .wav extension.
        timeout: Maximum execution time in seconds.

    Returns:
        Path to the extracted audio file.

    Raises:
        ValueError: If paths contain unsafe characters.
        subprocess.CalledProcessError: If FFmpeg fails.
        subprocess.TimeoutExpired: If the process exceeds the timeout.
    """
    _validate_file_path(video_path, "video_path")
    if output_path is None:
        base = os.path.splitext(video_path)[0]
        output_path = f"{base}.wav"
    _validate_file_path(output_path, "output_path")

    _run_ffmpeg(
        [
            "-i", video_path,
            "-vn",                    # No video
            "-acodec", "pcm_s16le",   # PCM 16-bit for Whisper compatibility
            "-ar", "16000",           # 16kHz sample rate (Whisper standard)
            "-ac", "1",               # Mono
            output_path,
        ],
        timeout=timeout,
    )
    logger.info("Extracted audio: %s -> %s", video_path, output_path)
    return output_path


def cut_video(
    video_path: str,
    timestamps: List[Dict[str, float]],
    output_dir: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> List[str]:
    """Cut a video into clips based on timestamps.

    Args:
        video_path: Path to the input video.
        timestamps: List of dicts with 'start' and 'end' keys (seconds).
        output_dir: Directory for output clips. Defaults to same dir as input.
        timeout: Maximum execution time per clip in seconds.

    Returns:
        List of paths to the generated clips.

    Raises:
        ValueError: If paths contain unsafe characters or timestamps are invalid.
    """
    _validate_file_path(video_path, "video_path")

    if output_dir is None:
        output_dir = os.path.dirname(video_path)
    _validate_file_path(output_dir, "output_dir")
    os.makedirs(output_dir, exist_ok=True)

    output_paths = []
    base_name = os.path.splitext(os.path.basename(video_path))[0]

    for i, ts in enumerate(timestamps):
        start = float(ts["start"])
        end = float(ts["end"])
        if start < 0 or end < 0 or end <= start:
            raise ValueError(f"Invalid timestamp at index {i}: start={start}, end={end}")

        output_path = os.path.join(output_dir, f"{base_name}_clip_{i:03d}.mp4")
        _run_ffmpeg(
            [
                "-i", video_path,
                "-ss", str(start),
                "-to", str(end),
                "-c", "copy",        # Stream copy for speed
                output_path,
            ],
            timeout=timeout,
        )
        output_paths.append(output_path)

    logger.info("Cut video into %d clips: %s", len(output_paths), video_path)
    return output_paths


def detect_silence(
    audio_path: str,
    noise_threshold: str = "-30dB",
    min_duration: float = 0.5,
    timeout: int = DEFAULT_TIMEOUT,
) -> List[Dict[str, float]]:
    """Detect silent segments in an audio file.

    Args:
        audio_path: Path to the audio file.
        noise_threshold: Silence detection threshold (e.g., '-30dB').
        min_duration: Minimum silence duration to detect (seconds).
        timeout: Maximum execution time in seconds.

    Returns:
        List of dicts with 'start' and 'end' keys for each silent segment.

    Raises:
        ValueError: If inputs contain unsafe characters.
    """
    _validate_file_path(audio_path, "audio_path")

    # Validate threshold format to prevent injection
    if not _SAFE_THRESHOLD_PATTERN.match(noise_threshold):
        raise ValueError(
            f"Invalid noise_threshold format: '{noise_threshold}'. "
            f"Expected format like '-30dB'"
        )
    if not (0.01 <= min_duration <= 60):
        raise ValueError(f"min_duration must be between 0.01 and 60, got {min_duration}")

    # Use the shared _run_ffmpeg wrapper (was previously bypassed)
    result = _run_ffmpeg(
        [
            "-i", audio_path,
            "-af", f"silencedetect=noise={noise_threshold}:d={min_duration}",
            "-f", "null", "-",
        ],
        check=False,
        timeout=timeout,
    )

    # Parse silence detection output from stderr
    silences = []
    lines = result.stderr.split("\n")
    start = None

    for line in lines:
        if "silence_start:" in line:
            try:
                start = float(line.split("silence_start:")[1].strip().split()[0])
            except (IndexError, ValueError):
                continue
        elif "silence_end:" in line and start is not None:
            try:
                end = float(line.split("silence_end:")[1].strip().split()[0])
                silences.append({"start": start, "end": end})
                start = None
            except (IndexError, ValueError):
                continue

    logger.info("Detected %d silent segments in %s", len(silences), audio_path)
    return silences


def burn_subtitles(
    video_path: str,
    subtitle_path: str,
    output_path: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Burn (hardcode) subtitles into a video file.

    Args:
        video_path: Path to the input video.
        subtitle_path: Path to the subtitle file (SRT or ASS).
        output_path: Path for the output video. Defaults to appending '_sub'.
        timeout: Maximum execution time in seconds.

    Returns:
        Path to the output video with burned subtitles.

    Raises:
        ValueError: If paths contain unsafe characters.
    """
    _validate_file_path(video_path, "video_path")
    _validate_file_path(subtitle_path, "subtitle_path")

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_sub{ext}"
    _validate_file_path(output_path, "output_path")

    # Escape special characters in subtitle path for FFmpeg filter
    escaped_path = subtitle_path.replace("\\", "/").replace(":", "\\:")

    _run_ffmpeg(
        [
            "-i", video_path,
            "-vf", f"subtitles='{escaped_path}'",
            "-c:a", "copy",
            output_path,
        ],
        timeout=timeout,
    )
    logger.info("Burned subtitles: %s + %s -> %s", video_path, subtitle_path, output_path)
    return output_path


def resize_video(
    video_path: str,
    resolution: str = "1080x1920",
    output_path: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Resize a video to the specified resolution.

    Args:
        video_path: Path to the input video.
        resolution: Target resolution as 'WxH' (e.g., '1080x1920' for 9:16).
        output_path: Path for output. Defaults to appending '_resized'.
        timeout: Maximum execution time in seconds.

    Returns:
        Path to the resized video.

    Raises:
        ValueError: If resolution format is invalid or paths are unsafe.
    """
    _validate_file_path(video_path, "video_path")
    width, height = _validate_resolution(resolution)

    if output_path is None:
        base, ext = os.path.splitext(video_path)
        output_path = f"{base}_resized{ext}"
    _validate_file_path(output_path, "output_path")

    _run_ffmpeg(
        [
            "-i", video_path,
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                   f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-c:a", "copy",
            output_path,
        ],
        timeout=timeout,
    )
    logger.info("Resized video to %s: %s -> %s", resolution, video_path, output_path)
    return output_path


def get_video_info(video_path: str) -> Dict[str, Any]:
    """Get video metadata using FFprobe.

    Args:
        video_path: Path to the video file.

    Returns:
        Dictionary with video metadata (duration, resolution, codec, etc.).

    Raises:
        ValueError: If the path contains unsafe characters.
    """
    _validate_file_path(video_path, "video_path")

    result = _run_ffprobe([
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path,
    ])
    return json.loads(result.stdout)


def get_video_duration(video_path: str) -> float:
    """Get the duration of a video in seconds.

    Args:
        video_path: Path to the video file.

    Returns:
        Duration in seconds.

    Raises:
        ValueError: If the path contains unsafe characters.
    """
    info = get_video_info(video_path)
    return float(info.get("format", {}).get("duration", 0))
