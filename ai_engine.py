import json
import os
import re
import subprocess
from functools import lru_cache

from media_tools import ffmpeg_executable
from prompt_ai import parse_prompt

try:
    import cv2
except ImportError:
    cv2 = None


def _bool(value):
    return bool(value) if value is not None else False


def _fallback_actions(prompt):
    settings = parse_prompt(prompt)
    tone = "anime vivid" if settings["anime"] else "moody dramatic" if settings["dramatic"] else "cinematic" if settings["cinematic"] else "clean creator"
    return {
        "style": "anime" if settings["anime"] else "viral" if settings["viral"] else "cinematic" if settings["cinematic"] else "clean",
        "aspect_ratio": "9:16" if settings["reel"] else "16:9",
        "captions": settings["captions"],
        "remove_silence": settings["silence"],
        "background_music": settings["music"],
        "color_grade": tone,
        "zoom_style": "punch-in" if settings["viral"] else "slow push-in" if settings["cinematic"] else "subtle",
        "pace": "fast" if settings["viral"] else "smooth",
        "caption_style": "bold kinetic" if settings["viral"] else "premium minimal",
        "source": "local-ai-parser",
    }


def understand_prompt(prompt):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return _fallback_actions(prompt)

    try:
        from openai import OpenAI
    except ImportError:
        actions = _fallback_actions(prompt)
        actions["source"] = "local-ai-parser-openai-package-missing"
        return actions

    schema_hint = {
        "style": "cinematic|viral|anime|dramatic|clean|product",
        "aspect_ratio": "16:9|9:16|1:1",
        "captions": True,
        "remove_silence": True,
        "background_music": False,
        "color_grade": "short phrase",
        "zoom_style": "short phrase",
        "pace": "slow|smooth|fast",
        "caption_style": "short phrase",
    }

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You convert video editing prompts into JSON actions. "
                        "Return only valid JSON with these keys: "
                        + ", ".join(schema_hint.keys())
                    ),
                },
                {
                    "role": "user",
                    "content": f"Prompt: {prompt}\nJSON shape: {json.dumps(schema_hint)}",
                },
            ],
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content.strip().removeprefix("```json").removesuffix("```").strip())
        fallback = _fallback_actions(prompt)
        fallback.update({
            "style": str(data.get("style") or fallback["style"]),
            "aspect_ratio": str(data.get("aspect_ratio") or fallback["aspect_ratio"]),
            "captions": _bool(data.get("captions")),
            "remove_silence": _bool(data.get("remove_silence")),
            "background_music": _bool(data.get("background_music")),
            "color_grade": str(data.get("color_grade") or fallback["color_grade"]),
            "zoom_style": str(data.get("zoom_style") or fallback["zoom_style"]),
            "pace": str(data.get("pace") or fallback["pace"]),
            "caption_style": str(data.get("caption_style") or fallback["caption_style"]),
            "source": "openai",
        })
        return fallback
    except Exception as error:
        actions = _fallback_actions(prompt)
        actions["source"] = f"local-ai-parser-openai-error: {error.__class__.__name__}"
        return actions


def ffprobe_duration(video_path):
    ffmpeg = ffmpeg_executable()
    if not ffmpeg:
        return 30.0
    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True,
            text=True,
            check=False,
        )
        return max(1.0, float(result.stdout.strip()))
    except Exception:
        return 30.0


def has_audio_stream(video_path):
    ffmpeg = ffmpeg_executable()
    if not ffmpeg:
        return False
    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
            capture_output=True,
            text=True,
            check=False,
        )
        return "audio" in result.stdout.lower()
    except Exception:
        return False


def _clean_caption(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:82]


def _format_ass_time(seconds):
    seconds = max(0, float(seconds or 0))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"


def write_ass_captions(captions, output_path, width=1080, height=1920):
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,64,&H00FFFFFF,&H00C56FFF,&HAA000000,&HAA000000,-1,0,0,0,100,100,0,0,1,4,1,2,70,70,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for caption in captions:
        text = _clean_caption(caption.get("text"))
        if not text:
            continue
        text = text.replace("{", "").replace("}", "").replace("\n", "\\N")
        lines.append(
            f"Dialogue: 0,{_format_ass_time(caption.get('start'))},{_format_ass_time(caption.get('end'))},Default,,0,0,0,,{text}\n"
        )
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.writelines(lines)


@lru_cache(maxsize=1)
def _whisper_model():
    import whisper

    return whisper.load_model(os.environ.get("WHISPER_MODEL", "base"))


def transcribe_video(video_path):
    try:
        model = _whisper_model()
        result = model.transcribe(video_path, fp16=False)
    except Exception as error:
        return [], f"whisper-unavailable: {error.__class__.__name__}"

    captions = []
    for segment in result.get("segments", [])[:80]:
        text = _clean_caption(segment.get("text"))
        if text:
            captions.append({
                "start": float(segment.get("start", 0)),
                "end": float(segment.get("end", 0)),
                "text": text,
            })
    return captions, "whisper"


def fallback_captions(duration, prompt):
    duration = max(8.0, duration)
    lines = [
        "AI generated opening hook",
        "Main moment highlighted",
        "Clean cinematic edit",
        "Final beat ready to share",
    ]
    if "product" in (prompt or "").lower():
        lines = ["Product showcase", "Premium details", "Feature highlight", "Ready to launch"]
    step = duration / len(lines)
    return [
        {"start": index * step, "end": min(duration, (index + 1) * step - 0.15), "text": text}
        for index, text in enumerate(lines)
    ]


def detect_silence(video_path):
    ffmpeg = ffmpeg_executable()
    if not ffmpeg or not has_audio_stream(video_path):
        return []

    result = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            video_path,
            "-af",
            "silencedetect=noise=-34dB:d=0.45",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    text = result.stderr
    starts = [float(match) for match in re.findall(r"silence_start: ([0-9.]+)", text)]
    ends = [float(match) for match in re.findall(r"silence_end: ([0-9.]+)", text)]
    return [
        {"start": start, "end": end, "type": "silence"}
        for start, end in zip(starts, ends)
        if end - start >= 0.45
    ][:30]


def analyze_scenes(video_path):
    duration = ffprobe_duration(video_path)
    if cv2 is None:
        return {
            "source": "fallback",
            "duration": duration,
            "scene_count": 1,
            "cuts": [],
            "highlights": [{"start": 0, "end": min(duration, 8), "score": 0.5, "label": "Opening highlight"}],
            "brightness": None,
            "motion": None,
        }

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    sample_step = max(1, int(fps * 0.5))
    last_hist = None
    cuts = []
    highlights = []
    brightness_values = []
    motion_values = []
    previous_gray = None
    frame_index = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % sample_step:
            frame_index += 1
            continue

        seconds = frame_index / fps
        resized = cv2.resize(frame, (160, 90))
        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        brightness = float(hsv[:, :, 2].mean())
        saturation = float(hsv[:, :, 1].mean())
        brightness_values.append(brightness)

        hist = cv2.calcHist([hsv], [0], None, [32], [0, 180])
        cv2.normalize(hist, hist)
        cut_score = 0.0
        if last_hist is not None:
            cut_score = float(cv2.compareHist(last_hist, hist, cv2.HISTCMP_BHATTACHARYYA))
            if cut_score > 0.48:
                cuts.append({"time": round(seconds, 2), "score": round(cut_score, 3)})
        last_hist = hist

        motion = 0.0
        if previous_gray is not None:
            motion = float(cv2.absdiff(previous_gray, gray).mean())
            motion_values.append(motion)
        previous_gray = gray

        score = (motion / 40) + (saturation / 220) + min(cut_score, 0.8)
        if score > 0.42:
            highlights.append({
                "start": round(max(0, seconds - 1.2), 2),
                "end": round(min(duration, seconds + 2.8), 2),
                "score": round(score, 3),
                "label": "High motion moment" if motion > 10 else "Visual change",
            })
        frame_index += 1

    cap.release()
    highlights = sorted(highlights, key=lambda item: item["score"], reverse=True)[:8]
    highlights = sorted(highlights, key=lambda item: item["start"])
    return {
        "source": "opencv",
        "duration": round(duration, 2),
        "scene_count": max(1, len(cuts) + 1),
        "cuts": cuts[:30],
        "highlights": highlights or [{"start": 0, "end": min(duration, 8), "score": 0.5, "label": "Opening highlight"}],
        "brightness": round(sum(brightness_values) / len(brightness_values), 2) if brightness_values else None,
        "motion": round(sum(motion_values) / len(motion_values), 2) if motion_values else None,
        "frames": frame_count,
    }


def build_ai_edit_plan(prompt, actions, duration, scene_analysis, silence_segments, captions):
    clips = []
    if actions["remove_silence"] and silence_segments:
        cursor = 0.0
        for segment in silence_segments[:12]:
            if segment["start"] > cursor:
                clips.append({"label": "Keep", "start": round(cursor, 2), "end": round(segment["start"], 2), "type": "keep"})
            clips.append({"label": "AI silence cut", "start": round(segment["start"], 2), "end": round(segment["end"], 2), "type": "cut"})
            cursor = max(cursor, segment["end"])
        if cursor < duration:
            clips.append({"label": "Keep", "start": round(cursor, 2), "end": round(duration, 2), "type": "keep"})
    else:
        highlights = scene_analysis.get("highlights", [])
        if actions["pace"] == "fast" and highlights:
            clips = [
                {"label": item["label"], "start": item["start"], "end": item["end"], "type": "keep"}
                for item in highlights[:6]
            ]
        else:
            clips = [
                {"label": "AI hook", "start": 0, "end": min(4, duration), "type": "keep"},
                {"label": "Scene intelligence", "start": min(4, duration), "end": min(max(10, duration * 0.5), duration), "type": "keep"},
                {"label": "Best moment", "start": max(0, duration * 0.5), "end": duration, "type": "keep"},
            ]

    clips = [clip for clip in clips if clip["end"] > clip["start"]]
    return {
        "prompt": prompt,
        "style": actions["style"],
        "aspect_ratio": actions["aspect_ratio"],
        "captions": bool(captions),
        "caption_items": captions or [],
        "music": actions["background_music"],
        "ai_actions": actions,
        "ai_analysis": {
            "scene": scene_analysis,
            "silence": silence_segments,
        },
        "cuts": clips,
    }


def ai_health():
    return {
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "whisper": _module_available("whisper"),
        "opencv": cv2 is not None,
        "scene_ai": cv2 is not None,
        "silence_ai": ffmpeg_executable() is not None,
    }


def _module_available(name):
    try:
        __import__(name)
    except ImportError:
        return False
    return True
