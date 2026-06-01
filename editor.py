import os
import subprocess
import uuid

from ai_engine import (
    analyze_scenes,
    build_ai_edit_plan,
    detect_silence,
    fallback_captions,
    ffprobe_duration,
    has_audio_stream,
    transcribe_video,
    understand_prompt,
    write_ass_captions,
)
from media_tools import ffmpeg_executable
from prompt_ai import parse_prompt

try:
    import cv2
except ImportError:
    cv2 = None


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
RUNTIME_DIR = "/tmp" if os.environ.get("VERCEL") else BASE_DIR
OUTPUT_DIR = os.environ.get("VIXA_OUTPUT_DIR", os.path.join(RUNTIME_DIR, "outputs"))


def _build_filters(settings, actions):
    filters = []

    if actions["aspect_ratio"] == "9:16" or settings["reel"]:
        filters.append("scale=1080:1920:force_original_aspect_ratio=increase")
        filters.append("crop=1080:1920")
    elif actions["aspect_ratio"] == "1:1":
        filters.append("scale=1080:1080:force_original_aspect_ratio=increase")
        filters.append("crop=1080:1080")
    else:
        filters.append("scale=1280:720:force_original_aspect_ratio=decrease")
        filters.append("pad=1280:720:(ow-iw)/2:(oh-ih)/2")

    grade = f"{actions.get('color_grade', '')} {actions.get('style', '')}".lower()
    if settings["cinematic"] or "cinematic" in grade:
        filters.append("eq=contrast=1.18:saturation=1.22:brightness=-0.02")
    if settings["dramatic"] or "dramatic" in grade or "moody" in grade:
        filters.append("eq=contrast=1.34:saturation=0.86")
    if settings["anime"] or "anime" in grade:
        filters.append("eq=saturation=1.45:contrast=1.2")
    return ",".join(filters)


def _caption_for_time(captions, seconds):
    for caption in captions:
        if caption["start"] <= seconds <= caption["end"]:
            return caption["text"]
    return ""


def _wrap_text(text, max_chars=28):
    words = text.split()
    lines = []
    line = []
    for word in words:
        if len(" ".join(line + [word])) > max_chars and line:
            lines.append(" ".join(line))
            line = [word]
        else:
            line.append(word)
    if line:
        lines.append(" ".join(line))
    return lines[:2]


def _burn_captions_cv2(video_path, captions, ffmpeg):
    if cv2 is None or not captions:
        return video_path, False

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if not width or not height:
        cap.release()
        return video_path, False

    temp_video = os.path.join(OUTPUT_DIR, f"caption_video_{uuid.uuid4().hex[:10]}.mp4")
    final_video = os.path.join(OUTPUT_DIR, f"captioned_{uuid.uuid4().hex[:10]}.mp4")
    writer = cv2.VideoWriter(temp_video, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    frame_index = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        seconds = frame_index / fps
        text = _caption_for_time(captions, seconds)
        if text:
            lines = _wrap_text(text, max(18, width // 38))
            font = cv2.FONT_HERSHEY_SIMPLEX
            scale = max(0.8, min(2.0, width / 760))
            thickness = max(2, int(width / 420))
            line_height = int(48 * scale)
            block_height = line_height * len(lines) + 32
            y0 = height - block_height - int(height * 0.08)
            overlay = frame.copy()
            cv2.rectangle(overlay, (40, y0), (width - 40, y0 + block_height), (0, 0, 0), -1)
            frame = cv2.addWeighted(overlay, 0.62, frame, 0.38, 0)
            for index, line in enumerate(lines):
                size = cv2.getTextSize(line.upper(), font, scale, thickness)[0]
                x = max(24, (width - size[0]) // 2)
                y = y0 + 46 + index * line_height
                cv2.putText(frame, line.upper(), (x + 2, y + 2), font, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
                cv2.putText(frame, line.upper(), (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)
        writer.write(frame)
        frame_index += 1

    cap.release()
    writer.release()

    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            temp_video,
            "-i",
            video_path,
            "-map",
            "0:v:0",
            "-map",
            "1:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "copy",
            "-shortest",
            final_video,
        ],
        capture_output=True,
        text=True,
    )
    try:
        os.remove(temp_video)
    except OSError:
        pass
    if result.returncode != 0:
        return video_path, False
    return final_video, True


def process_video(video_path, prompt):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    settings = parse_prompt(prompt)
    actions = understand_prompt(prompt)
    duration = ffprobe_duration(video_path)
    scene_analysis = analyze_scenes(video_path)
    silence_segments = detect_silence(video_path) if actions["remove_silence"] else []
    captions = []
    caption_source = None
    caption_path = None

    if actions["captions"]:
        if has_audio_stream(video_path):
            captions, caption_source = transcribe_video(video_path)
        else:
            caption_source = "fallback-no-audio"
        if not captions:
            captions = fallback_captions(duration, prompt)
        caption_name = f"captions_{uuid.uuid4().hex[:10]}.ass"
        caption_path = os.path.join(OUTPUT_DIR, caption_name)
        width, height = (1080, 1920) if actions["aspect_ratio"] == "9:16" or settings["reel"] else (1280, 720)
        write_ass_captions(captions, caption_path, width=width, height=height)

    plan = build_ai_edit_plan(prompt, actions, duration, scene_analysis, silence_segments, captions)

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
    filters = _build_filters(settings, actions)

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

    caption_burned = False
    if captions:
        output_path, caption_burned = _burn_captions_cv2(output_path, captions, ffmpeg)
        output_name = os.path.basename(output_path)

    return {
        "status": "rendered",
        "message": "AI edit rendered with prompt understanding and captions." if captions else "AI edit rendered with prompt understanding.",
        "plan": plan,
        "ai": {
            "actions": actions,
            "caption_source": caption_source,
            "captions_generated": len(captions),
            "captions_burned": caption_burned,
            "scene_source": scene_analysis.get("source"),
            "scene_count": scene_analysis.get("scene_count"),
            "highlights": scene_analysis.get("highlights", []),
            "silence_segments": len(silence_segments),
        },
        "output_url": f"/outputs/{output_name}",
    }
