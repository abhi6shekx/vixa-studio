import os
import subprocess
import uuid

from media_tools import ffmpeg_executable
from prompt_ai import parse_prompt


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
RUNTIME_DIR = "/tmp" if os.environ.get("VERCEL") else BASE_DIR
OUTPUT_DIR = os.environ.get("VIXA_OUTPUT_DIR", os.path.join(RUNTIME_DIR, "outputs"))


def _build_filters(settings):
    filters = []

    if settings["reel"]:
        filters.append("scale=1080:1920:force_original_aspect_ratio=increase")
        filters.append("crop=1080:1920")
    else:
        filters.append("scale=1280:720:force_original_aspect_ratio=decrease")
        filters.append("pad=1280:720:(ow-iw)/2:(oh-ih)/2")

    if settings["cinematic"]:
        filters.append("eq=contrast=1.18:saturation=1.22:brightness=-0.02")
    if settings["dramatic"]:
        filters.append("eq=contrast=1.34:saturation=0.86")
    if settings["anime"]:
        filters.append("eq=saturation=1.45:contrast=1.2")

    return ",".join(filters)


def _plan_from_settings(settings, prompt):
    cuts = [
        {"label": "Hook", "start": 0, "end": 4, "type": "keep"},
        {"label": "Pause cleanup", "start": 4, "end": 6, "type": "cut" if settings["silence"] else "keep"},
        {"label": "Main point", "start": 6, "end": 18, "type": "keep"},
        {"label": "Slow section", "start": 18, "end": 22, "type": "cut" if settings["silence"] else "keep"},
        {"label": "Final beat", "start": 22, "end": 30, "type": "keep"},
    ]
    return {
        "prompt": prompt,
        "style": "Anime highlight" if settings["anime"] else "Viral short" if settings["viral"] else "Vertical reel" if settings["reel"] else "HD landscape",
        "captions": settings["captions"],
        "music": settings["music"],
        "cuts": cuts,
    }


def process_video(video_path, prompt):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    settings = parse_prompt(prompt)
    plan = _plan_from_settings(settings, prompt)

    ffmpeg = ffmpeg_executable()
    if not ffmpeg:
        return {
            "status": "plan-only",
            "message": "ffmpeg was not found, so Vixa Studio created the AI edit plan only.",
            "plan": plan,
            "output_url": None,
        }

    ext = os.path.splitext(video_path)[1] or ".mp4"
    output_name = f"edited_{uuid.uuid4().hex[:10]}{ext}"
    output_path = os.path.join(OUTPUT_DIR, output_name)
    filters = _build_filters(settings)

    command = [
        ffmpeg,
        "-y",
        "-i",
        video_path,
        "-vf",
        filters,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        output_path,
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return {
            "status": "render-error",
            "message": result.stderr[-1200:] or "ffmpeg render failed.",
            "plan": plan,
            "output_url": None,
        }

    return {
        "status": "rendered",
        "message": "AI edit rendered successfully.",
        "plan": plan,
        "output_url": f"/outputs/{output_name}",
    }
