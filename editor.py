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


def _target_dimensions(settings, actions):
    if actions["aspect_ratio"] == "9:16" or settings["reel"]:
        return 1080, 1920
    if actions["aspect_ratio"] == "1:1":
        return 1080, 1080
    return 1280, 720


def _build_filters(settings, actions):
    filters = []
    target_width, target_height = _target_dimensions(settings, actions)

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
    if actions.get("zoom_style") and actions.get("zoom_style") != "none":
        filters.append("crop=iw*0.94:ih*0.94:(iw-iw*0.94)/2:(ih-ih*0.94)/2")
        filters.append(f"scale={target_width}:{target_height}")
    return ",".join(filters)


def _keep_ranges_from_silence(duration, silence_segments):
    ranges = []
    cursor = 0.0
    for segment in silence_segments:
        start = max(0.0, float(segment.get("start", 0)))
        end = min(duration, float(segment.get("end", 0)))
        if start > cursor + 0.08:
            ranges.append((round(cursor, 3), round(start, 3)))
        cursor = max(cursor, end)
    if cursor < duration - 0.08:
        ranges.append((round(cursor, 3), round(duration, 3)))
    return [(start, end) for start, end in ranges if end > start]


def _remove_silence_render(video_path, duration, silence_segments, ffmpeg):
    keep_ranges = _keep_ranges_from_silence(duration, silence_segments)
    if not keep_ranges or len(keep_ranges) > 24:
        return video_path, False

    output_path = os.path.join(OUTPUT_DIR, f"silence_cut_{uuid.uuid4().hex[:10]}.mp4")
    filters = []
    concat_inputs = []
    for index, (start, end) in enumerate(keep_ranges):
        filters.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{index}]")
        filters.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{index}]")
        concat_inputs.append(f"[v{index}][a{index}]")
    filters.append(f"{''.join(concat_inputs)}concat=n={len(keep_ranges)}:v=1:a=1[outv][outa]")

    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            video_path,
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[outv]",
            "-map",
            "[outa]",
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
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return video_path, False
    return output_path, True


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


def process_video(video_path, prompt, user_options=None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    user_options = user_options or {}
    settings = parse_prompt(prompt)
    actions = understand_prompt(prompt)
    if "captions" in user_options:
        actions["captions"] = bool(user_options["captions"])
    if "remove_silence" in user_options:
        actions["remove_silence"] = bool(user_options["remove_silence"])
    if "background_music" in user_options:
        actions["background_music"] = bool(user_options["background_music"])
    if "auto_zoom" in user_options:
        actions["zoom_style"] = "slow push-in" if user_options["auto_zoom"] else "none"
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

    silence_removed = False
    if silence_segments:
        output_path, silence_removed = _remove_silence_render(output_path, duration, silence_segments, ffmpeg)
        output_name = os.path.basename(output_path)

    caption_burned = False
    if captions:
        output_path, caption_burned = _burn_captions_cv2(output_path, captions, ffmpeg)
        output_name = os.path.basename(output_path)

    enabled_tools = []
    if actions.get("zoom_style") != "none":
        enabled_tools.append("auto zoom")
    if silence_removed:
        enabled_tools.append("silence removal")
    if captions:
        enabled_tools.append("captions")

    return {
        "status": "rendered",
        "message": f"AI edit rendered with {', '.join(enabled_tools)}." if enabled_tools else "AI edit rendered.",
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
            "silence_removed": silence_removed,
            "auto_zoom": actions.get("zoom_style") != "none",
        },
        "output_url": f"/outputs/{output_name}",
    }
