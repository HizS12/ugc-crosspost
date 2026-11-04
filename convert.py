"""Make phone videos (iPhone .mov / HEVC, Android .mp4) safe for every platform: H.264 + AAC .mp4."""

import re
import subprocess

import imageio_ffmpeg


def for_upload(path):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    info = subprocess.run([ff, "-hide_banner", "-i", str(path)], capture_output=True, text=True, errors="replace").stderr
    is_h264 = re.search(r"Video: h264", info) is not None
    audio_ok = "Audio:" not in info or "Audio: aac" in info
    if path.suffix.lower() == ".mp4" and is_h264 and audio_ok:
        return path

    out = path.with_name(f"{path.stem}_upload.mp4")
    video = ["-c:v", "copy"] if is_h264 else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]
    subprocess.run(
        [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(path),
         "-map", "0:v:0", "-map", "0:a:0?", *video, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)],
        check=True,
    )
    return out
