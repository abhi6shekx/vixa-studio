import os
import shutil
import subprocess
import uuid
import wave

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    import cv2
except ImportError:
    cv2 = None
try:
    import numpy as np
except ImportError:
    np = None
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from ai_engine import ai_health, understand_prompt
from editor import process_video
from media_tools import ffmpeg_executable, has_ffmpeg


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if load_dotenv:
    load_dotenv(os.path.join(BASE_DIR, ".env"))

RUNTIME_DIR = "/tmp" if os.environ.get("VERCEL") else BASE_DIR
UPLOAD_DIR = os.path.join(RUNTIME_DIR, "uploads")
OUTPUT_DIR = os.path.join(RUNTIME_DIR, "outputs")

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_uploaded_file(file):
    safe_name = secure_filename(file.filename)
    name, ext = os.path.splitext(safe_name)
    filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
    upload_path = os.path.join(UPLOAD_DIR, filename)
    file.save(upload_path)
    return upload_path


def _has_ffmpeg():
    return has_ffmpeg()


def _target_size(aspect_ratio):
    if aspect_ratio == "9:16":
        return 1080, 1920
    if aspect_ratio == "1:1":
        return 1080, 1080
    return 1280, 720


def _photo_motion_filter(width, height, motion, duration, fps):
    total_frames = max(1, int(duration * fps))
    base = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    if motion == "pan-left":
        motion_filter = f"zoompan=z='1.12':x='iw*0.08-(iw*0.16*on/{total_frames})':y='ih*0.03':d={total_frames}:s={width}x{height}:fps={fps}"
    elif motion == "pan-right":
        motion_filter = f"zoompan=z='1.12':x='iw*0.02+(iw*0.16*on/{total_frames})':y='ih*0.03':d={total_frames}:s={width}x{height}:fps={fps}"
    elif motion == "parallax":
        motion_filter = f"zoompan=z='1+0.16*sin(on/18)':x='iw*0.04*sin(on/20)':y='ih*0.04*cos(on/24)':d={total_frames}:s={width}x{height}:fps={fps}"
    elif motion == "anime":
        motion_filter = f"zoompan=z='1+0.08*floor(on/8)':x='iw*0.02*sin(on/8)':y='ih*0.02*cos(on/8)':d={total_frames}:s={width}x{height}:fps={fps},eq=saturation=1.45:contrast=1.18"
    elif motion == "product":
        motion_filter = f"zoompan=z='1.04+0.10*on/{total_frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps},eq=contrast=1.08:saturation=1.12"
    elif motion == "cinematic":
        motion_filter = f"zoompan=z='1.05+0.18*on/{total_frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps},eq=contrast=1.22:saturation=1.18:brightness=-0.025"
    else:
        motion_filter = f"zoompan=z='1.03+0.14*on/{total_frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}"
    return f"{base},{motion_filter},format=yuv420p"


def render_photo_video(image_paths, prompt, motion, duration, aspect_ratio):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ffmpeg = ffmpeg_executable()
    if not ffmpeg:
        return {
            "status": "error",
            "message": "FFmpeg is required for real Photo to Video rendering.",
            "output_url": None,
        }

    safe_duration = min(max(int(duration or 5), 5), 30)
    fps = 30
    width, height = _target_size(aspect_ratio)
    per_image_duration = max(1.0, safe_duration / max(1, len(image_paths)))
    temp_clips = []

    try:
        for image_path in image_paths:
            clip_name = f"photo_clip_{uuid.uuid4().hex[:10]}.mp4"
            clip_path = os.path.join(OUTPUT_DIR, clip_name)
            command = [
                ffmpeg,
                "-y",
                "-loop",
                "1",
                "-t",
                str(per_image_duration),
                "-i",
                image_path,
                "-vf",
                _photo_motion_filter(width, height, motion, per_image_duration, fps),
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "22",
                "-pix_fmt",
                "yuv420p",
                clip_path,
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0:
                return {
                    "status": "render-error",
                    "message": result.stderr[-1200:] or "Photo motion render failed.",
                    "output_url": None,
                }
            temp_clips.append(clip_path)

        output_name = f"photo_video_{uuid.uuid4().hex[:10]}.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_name)

        if len(temp_clips) == 1:
            os.replace(temp_clips[0], output_path)
            temp_clips = []
        else:
            concat_path = os.path.join(OUTPUT_DIR, f"concat_{uuid.uuid4().hex[:10]}.txt")
            with open(concat_path, "w", encoding="utf-8") as handle:
                for clip_path in temp_clips:
                    handle.write(f"file '{clip_path}'\n")
            result = subprocess.run(
                [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", concat_path, "-c", "copy", output_path],
                capture_output=True,
                text=True,
            )
            try:
                os.remove(concat_path)
            except OSError:
                pass
            if result.returncode != 0:
                return {
                    "status": "render-error",
                    "message": result.stderr[-1200:] or "Photo video combine failed.",
                    "output_url": None,
                }

        return {
            "status": "rendered",
            "success": True,
            "message": "Photo to Video AI rendered successfully.",
            "output_url": f"/outputs/{output_name}",
            "download_url": f"/download/{output_name}",
            "meta": {
                "images": len(image_paths),
                "duration": safe_duration,
                "aspect_ratio": aspect_ratio,
                "motion": motion,
                "prompt": prompt,
            },
        }
    finally:
        for clip_path in temp_clips:
            try:
                os.remove(clip_path)
            except OSError:
                pass


def _safe_image_style(style):
    allowed = {
        "voxel": "Voxel / Block World",
        "anime": "Anime",
        "animated-3d": "3D Animation",
        "cinematic": "Cinematic World",
        "cyberpunk": "Cyberpunk",
        "cartoon": "Cartoon",
        "storybook": "Storybook Anime",
        "reference": "Reference Style",
    }
    return style if style in allowed else "cinematic"


def _resize_for_style(image, max_size=1400):
    height, width = image.shape[:2]
    longest = max(width, height)
    if longest <= max_size:
        return image
    scale = max_size / longest
    return cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)


def _stylize_with_reference(base, reference):
    base_lab = cv2.cvtColor(base, cv2.COLOR_BGR2LAB).astype("float32")
    ref_lab = cv2.cvtColor(reference, cv2.COLOR_BGR2LAB).astype("float32")
    for channel in range(3):
        base_mean, base_std = cv2.meanStdDev(base_lab[:, :, channel])
        ref_mean, ref_std = cv2.meanStdDev(ref_lab[:, :, channel])
        base_lab[:, :, channel] = (base_lab[:, :, channel] - base_mean[0][0]) * (ref_std[0][0] / max(base_std[0][0], 1)) + ref_mean[0][0]
    matched = np.clip(base_lab, 0, 255).astype("uint8")
    return cv2.cvtColor(matched, cv2.COLOR_LAB2BGR)


def transform_image_style(image_path, style, prompt="", reference_path=None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    style = _safe_image_style(style)
    output_name = f"style_transform_{uuid.uuid4().hex[:10]}.png"
    output_path = os.path.join(OUTPUT_DIR, output_name)

    if cv2 is None or np is None:
        shutil.copyfile(image_path, output_path)
        return {
            "status": "fallback",
            "success": True,
            "message": "Image saved. Install opencv-python locally for free AI style rendering.",
            "style": style,
            "output_url": f"/outputs/{output_name}",
            "download_url": f"/download/{output_name}",
        }

    image = cv2.imread(image_path)
    if image is None:
        return {"status": "error", "message": "Could not read uploaded image."}

    image = _resize_for_style(image)
    prompt_text = prompt.lower()

    if style == "reference" and reference_path:
        reference = cv2.imread(reference_path)
        if reference is not None:
            styled = _stylize_with_reference(image, _resize_for_style(reference))
        else:
            styled = image.copy()
    elif style == "voxel":
        small = cv2.resize(image, (max(32, image.shape[1] // 18), max(32, image.shape[0] // 18)), interpolation=cv2.INTER_LINEAR)
        styled = cv2.resize(small, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
        styled = cv2.convertScaleAbs(styled, alpha=1.18, beta=8)
    elif style == "anime":
        smooth = cv2.bilateralFilter(image, 9, 100, 100)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 7)
        color = cv2.convertScaleAbs(smooth, alpha=1.2, beta=10)
        styled = cv2.bitwise_and(color, color, mask=edges)
    elif style == "animated-3d":
        smooth = cv2.bilateralFilter(image, 13, 120, 120)
        highlights = cv2.GaussianBlur(smooth, (0, 0), 8)
        styled = cv2.addWeighted(smooth, 1.2, highlights, -0.18, 16)
        styled = cv2.convertScaleAbs(styled, alpha=1.12, beta=8)
    elif style == "cyberpunk":
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.45, 0, 255)
        neon = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        overlay = np.zeros_like(neon)
        overlay[:, :, 0] = 70
        overlay[:, :, 2] = 90
        styled = cv2.addWeighted(neon, 0.78, overlay, 0.22, 10)
    elif style == "cartoon":
        styled = cv2.stylization(image, sigma_s=80, sigma_r=0.35)
    elif style == "storybook":
        warm = cv2.convertScaleAbs(image, alpha=1.08, beta=10)
        overlay = np.full_like(warm, (18, 8, 34))
        styled = cv2.addWeighted(warm, 0.88, overlay, 0.12, 0)
        styled = cv2.bilateralFilter(styled, 9, 90, 90)
    else:
        lut = np.arange(256, dtype="uint8")
        cinematic = cv2.LUT(image, lut)
        overlay = np.zeros_like(cinematic)
        overlay[:, :, 0] = 28
        overlay[:, :, 1] = 10
        overlay[:, :, 2] = 34
        styled = cv2.addWeighted(cinematic, 0.86, overlay, 0.14, -4)
        styled = cv2.convertScaleAbs(styled, alpha=1.14, beta=0)

    if any(word in prompt_text for word in ["rain", "storm", "neon", "glow", "cinematic"]):
        glow = cv2.GaussianBlur(styled, (0, 0), 10)
        styled = cv2.addWeighted(styled, 1.06, glow, 0.16, 0)

    cv2.imwrite(output_path, styled)
    return {
        "status": "rendered",
        "success": True,
        "message": "AI Style Transform generated successfully.",
        "style": style,
        "output_url": f"/outputs/{output_name}",
        "download_url": f"/download/{output_name}",
        "meta": {"prompt": prompt, "reference_used": bool(reference_path)},
    }


def _voice_settings(language, voice):
    language = (language or "english").lower()
    voice = (voice or "narrator").lower()
    mac_voice = {
        "hindi": "Lekha",
        "marathi": "Lekha",
        "japanese": "Kyoko",
        "korean": "Yuna",
        "spanish": "Monica",
        "french": "Thomas",
        "arabic": "Maged",
        "tamil": "Lekha",
    }.get(language, "Samantha")
    rate = {
        "deep": "150",
        "cinematic": "145",
        "anime": "185",
        "robotic": "170",
        "podcast": "165",
        "emotional": "155",
    }.get(voice, "165")
    return mac_voice, rate


def _write_fallback_tone(path, duration=1.4):
    sample_rate = 22050
    frames = int(sample_rate * duration)
    with wave.open(path, "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for index in range(frames):
            value = int(12000 * np.sin(2 * np.pi * 440 * index / sample_rate)) if np is not None else 0
            handle.writeframesraw(value.to_bytes(2, byteorder="little", signed=True))


def generate_tts_audio(text, language, voice, emotion):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not text.strip():
        return {"status": "error", "message": "Voice script is required."}

    base_name = f"voice_{uuid.uuid4().hex[:10]}"
    aiff_path = os.path.join(OUTPUT_DIR, f"{base_name}.aiff")
    mp3_path = os.path.join(OUTPUT_DIR, f"{base_name}.mp3")
    say_bin = shutil.which("say")
    ffmpeg = ffmpeg_executable()
    mac_voice, rate = _voice_settings(language, voice)
    spoken_text = f"{emotion}. {text}" if emotion and emotion != "neutral" else text

    if say_bin:
        result = subprocess.run([say_bin, "-v", mac_voice, "-r", rate, "-o", aiff_path, spoken_text], capture_output=True, text=True)
        if result.returncode != 0:
            result = subprocess.run([say_bin, "-r", rate, "-o", aiff_path, spoken_text], capture_output=True, text=True)
        if result.returncode != 0:
            return {"status": "error", "message": result.stderr[-600:] or "Local TTS failed."}
        output_path = aiff_path
        output_name = os.path.basename(aiff_path)
        if ffmpeg:
            convert = subprocess.run([ffmpeg, "-y", "-i", aiff_path, "-codec:a", "libmp3lame", "-q:a", "3", mp3_path], capture_output=True, text=True)
            if convert.returncode == 0:
                output_path = mp3_path
                output_name = os.path.basename(mp3_path)
    else:
        wav_path = os.path.join(OUTPUT_DIR, f"{base_name}.wav")
        _write_fallback_tone(wav_path)
        output_path = wav_path
        output_name = os.path.basename(wav_path)

    return {
        "status": "rendered",
        "success": True,
        "message": "Free local voiceover generated.",
        "output_url": f"/outputs/{output_name}",
        "download_url": f"/download/{output_name}",
        "meta": {
            "language": language,
            "voice": voice,
            "emotion": emotion,
            "engine": "macos-say" if say_bin else "fallback-tone",
            "filename": os.path.basename(output_path),
        },
    }


def generate_creator_ai_plan(mode, prompt, media_context=""):
    prompt_text = (prompt or "").strip()
    mode = (mode or "copilot").strip()
    combined = f"{mode} {prompt_text} {media_context}".lower()
    actions = understand_prompt(prompt_text or mode)

    mode_titles = {
        "copilot": "AI Copilot Advisor",
        "viral": "Viral Reel AI",
        "highlights": "Auto Highlight AI",
        "beat": "Music Beat AI",
        "tracking": "Face / Object Tracking",
        "background": "Smart Background AI",
        "script": "AI Script Writer",
        "translate": "AI Translator + Dub",
        "thumbnail": "Thumbnail AI",
        "analytics": "AI Analytics",
        "chain": "Prompt Chain AI",
    }

    hook_score = 8 if any(word in combined for word in ["hook", "viral", "short", "reel"]) else 5
    pacing_score = 8 if any(word in combined for word in ["fast", "beat", "cuts", "music"]) else 6
    caption_score = 9 if actions.get("captions") else 5
    total_score = round((hook_score + pacing_score + caption_score) / 3, 1)

    plans = {
        "copilot": [
            "Start with a 2 second hook and remove slow intro footage.",
            "Add punch-in zooms on key words and emotional moments.",
            "Use bold captions with high contrast and short lines.",
            "Export one 9:16 reel and one 1:1 social cut.",
        ],
        "viral": [
            f"Viral score: {total_score}/10 based on hook, pacing, and caption clarity.",
            "First 3 seconds need a clear promise, question, or visual surprise.",
            "Add CTA in the last 4 seconds: follow, save, or comment.",
            "Keep final reel between 22 and 38 seconds for retention.",
        ],
        "highlights": [
            "Detect high-energy audio peaks and visual motion changes.",
            "Keep funny, emotional, or high-contrast moments.",
            "Create 3 short candidates: 15 sec, 30 sec, and 45 sec.",
            "Add captions only on the selected highlight clips.",
        ],
        "beat": [
            "Detect beats from uploaded music waveform.",
            "Place cuts on downbeats and transitions on beat drops.",
            "Use speed ramps before major beat changes.",
            "Sync zoom pulses with kick and snare moments.",
        ],
        "tracking": [
            "Detect primary face or subject in each scene.",
            "Apply auto-center crop for 9:16 reels.",
            "Add smooth subject-follow zoom when the subject moves.",
            "Avoid jumpy tracking by easing between detected positions.",
        ],
        "background": [
            "Separate subject from background where possible.",
            "Add cinematic blur, sky replacement, or neon environment.",
            "Use green-screen style cutout for creator shots.",
            "Keep edge feathering soft around hair and hands.",
        ],
        "script": [
            "Write a hook, 3 punchy points, and a short CTA.",
            "Generate matching voiceover text and caption lines.",
            "Suggest visual shots for each line.",
            "Prepare a 30 second reel structure.",
        ],
        "translate": [
            "Transcribe original speech and detect language.",
            "Translate to target language with short subtitle-safe lines.",
            "Generate dubbed voiceover and align it to caption timings.",
            "Export original subtitles plus dubbed version.",
        ],
        "thumbnail": [
            "Pick the clearest frame with face/action/product visibility.",
            "Add 3 to 5 word high-impact title text.",
            "Use purple/blue contrast and readable mobile scale.",
            "Generate two variants: clean premium and high-energy viral.",
        ],
        "analytics": [
            f"Retention risk: {'medium' if total_score >= 6 else 'high'} unless intro is tightened.",
            "Watch for drop after 8 seconds if the topic is not visually changing.",
            "Caption density should stay under 8 words per line.",
            "Use faster cuts if final output is longer than 40 seconds.",
        ],
        "chain": [
            "Step 1: transform photo/video style based on prompt.",
            "Step 2: create motion video or edited reel.",
            "Step 3: generate captions and voiceover.",
            "Step 4: create thumbnail and export package.",
        ],
    }

    return {
        "status": "ok",
        "success": True,
        "mode": mode,
        "title": mode_titles.get(mode, "AI Creator Plan"),
        "score": total_score,
        "actions": actions,
        "recommendations": plans.get(mode, plans["copilot"]),
        "pipeline": [
            {"step": "Analyze", "detail": "Read prompt, media context, pacing, captions, and style intent."},
            {"step": "Plan", "detail": "Convert creator goal into editing actions and export targets."},
            {"step": "Generate", "detail": "Send tasks to video, image, TTS, subtitles, or thumbnail tools."},
        ],
        "next_tools": ["AI Editor", "Photo to Video", "AI Style Transform", "Voice Studio", "Subtitles"],
    }


def _aspect_label(width, height):
    if not width or not height:
        return "Unknown"
    ratio = width / height
    if ratio < 0.8:
        return "9:16 vertical"
    if 0.9 <= ratio <= 1.12:
        return "1:1 square"
    return "16:9 cinematic"


def _audio_has_beat(video_path):
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=codec_type",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError:
        return False
    return "audio" in result.stdout.lower()


def analyze_reference_style(reference_path, prompt):
    if cv2 is None:
        text = prompt.lower()
        is_fast = any(word in text for word in ["viral", "short", "reel", "fast", "beat"])
        return {
            "color_tone": "Prompt-guided cinematic",
            "speed": "Fast beat cuts" if is_fast else "Smooth cinematic pacing",
            "cuts": "Reference analysis unavailable on lightweight runtime",
            "transitions": "Whip + flash transitions" if is_fast else "Soft dissolve + motion blur",
            "captions_style": "Bold kinetic captions" if is_fast else "Minimal premium subtitles",
            "aspect_ratio": "Prompt-guided",
            "music_beat": "Runtime analysis unavailable",
            "zoom_style": "Punch-in zooms" if is_fast else "Slow push-in zoom",
            "technical": {
                "runtime": "lightweight",
            },
        }

    cap = cv2.VideoCapture(reference_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = frame_count / fps if fps else 0

    samples = []
    histograms = []
    sample_count = min(18, max(1, frame_count))
    for index in range(sample_count):
        frame_number = int((frame_count - 1) * (index / max(1, sample_count - 1))) if frame_count else 0
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ok, frame = cap.read()
        if not ok:
            continue

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        samples.append({
            "brightness": float(hsv[:, :, 2].mean()),
            "saturation": float(hsv[:, :, 1].mean()),
        })
        histogram = cv2.calcHist([hsv], [0], None, [32], [0, 180])
        cv2.normalize(histogram, histogram)
        histograms.append(histogram)
    cap.release()

    brightness = sum(item["brightness"] for item in samples) / len(samples) if samples else 110
    saturation = sum(item["saturation"] for item in samples) / len(samples) if samples else 90
    diffs = [
        cv2.compareHist(histograms[index - 1], histograms[index], cv2.HISTCMP_BHATTACHARYYA)
        for index in range(1, len(histograms))
    ]
    cut_score = sum(1 for diff in diffs if diff > 0.45)
    cuts_per_minute = cut_score / max(duration / 60, 0.2)
    has_audio = _audio_has_beat(reference_path)

    text = prompt.lower()
    is_fast = cuts_per_minute > 18 or any(word in text for word in ["viral", "short", "reel", "fast", "beat"])
    is_anime = saturation > 120 or any(word in text for word in ["anime", "manga", "toon"])
    is_dark = brightness < 95 or any(word in text for word in ["dark", "dramatic", "moody", "intense"])
    is_cinematic = _aspect_label(width, height).startswith("16:9") or any(word in text for word in ["cinematic", "film", "movie", "premium"])

    return {
        "color_tone": "Anime vivid" if is_anime else "Moody cinematic" if is_dark else "Premium teal-purple" if is_cinematic else "Clean creator tone",
        "speed": "Fast beat cuts" if is_fast else "Smooth cinematic pacing",
        "cuts": f"{round(cuts_per_minute)} cuts/min" if cut_score else "Selective clean cuts",
        "transitions": "Whip + flash transitions" if is_fast else "Soft dissolve + motion blur",
        "captions_style": "Bold kinetic captions" if is_fast else "Minimal premium subtitles",
        "aspect_ratio": _aspect_label(width, height),
        "music_beat": "Beat-synced edits" if has_audio and is_fast else "Audio bed detected" if has_audio else "No music bed detected",
        "zoom_style": "Punch-in zooms" if is_fast else "Slow push-in zoom",
        "technical": {
            "duration": round(duration, 2),
            "fps": round(fps, 2),
            "width": width,
            "height": height,
            "brightness": round(brightness, 2),
            "saturation": round(saturation, 2),
        },
    }


@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/editor")
@app.get("/reference-match")
@app.get("/photo-to-video")
@app.get("/style-transform")
@app.get("/copilot")
@app.get("/templates")
@app.get("/projects")
@app.get("/voice")
@app.get("/subtitles")
@app.get("/music")
@app.get("/analytics")
@app.get("/settings")
def app_page():
    return send_from_directory(BASE_DIR, "index.html")


@app.post("/edit")
def edit():
    if "video" not in request.files:
        return jsonify({"status": "error", "message": "No video file uploaded."}), 400

    file = request.files["video"]
    prompt = request.form.get("prompt", "")
    if not file.filename:
        return jsonify({"status": "error", "message": "Empty filename."}), 400

    upload_path = save_uploaded_file(file)

    data = process_video(upload_path, prompt)
    if data.get("output_url"):
        filename = os.path.basename(data["output_url"])
        data["success"] = True
        data["download_url"] = f"/download/{filename}"
    return jsonify(data)


@app.post("/api/edit")
def api_edit():
    response = edit()
    if isinstance(response, tuple):
        return response

    data = response.get_json()
    if data and data.get("output_url"):
        filename = os.path.basename(data["output_url"])
        data["success"] = True
        data["download_url"] = f"/download/{filename}"
    return jsonify(data)


@app.post("/reference-edit")
def reference_edit():
    if "main_video" not in request.files or "reference_video" not in request.files:
        return jsonify({"status": "error", "message": "Upload your video and a reference video."}), 400

    main_video = request.files["main_video"]
    reference_video = request.files["reference_video"]
    prompt = request.form.get("prompt", "")

    if not main_video.filename or not reference_video.filename:
        return jsonify({"status": "error", "message": "Both video files are required."}), 400

    main_path = save_uploaded_file(main_video)
    reference_path = save_uploaded_file(reference_video)
    analysis = analyze_reference_style(reference_path, prompt)
    style_prompt = (
        f"{prompt} cinematic reference match {analysis['color_tone']} "
        f"{analysis['speed']} {analysis['captions_style']} {analysis['aspect_ratio']} {analysis['zoom_style']}"
    )
    render_result = process_video(main_path, style_prompt)

    return jsonify({
        "status": "started",
        "success": True,
        "message": "Reference style editing started",
        "main_video": os.path.basename(main_path),
        "reference_video": os.path.basename(reference_path),
        "analysis": analysis,
        "output_url": render_result.get("output_url"),
        "download_url": f"/download/{os.path.basename(render_result.get('output_url'))}" if render_result.get("output_url") else None,
        "render_status": render_result.get("status"),
    })


@app.post("/api/reference-edit")
def api_reference_edit():
    return reference_edit()


@app.post("/photo-to-video")
def photo_to_video():
    images = request.files.getlist("images")
    if not images:
        return jsonify({"status": "error", "message": "Upload one or more images."}), 400

    saved_images = []
    for image in images[:12]:
        if image.filename:
            saved_images.append(save_uploaded_file(image))

    if not saved_images:
        return jsonify({"status": "error", "message": "No valid image files uploaded."}), 400

    prompt = request.form.get("prompt", "")
    motion = request.form.get("motion", "slow-zoom")
    duration = request.form.get("duration", 5)
    aspect_ratio = request.form.get("aspect_ratio", "16:9")
    return jsonify(render_photo_video(saved_images, prompt, motion, duration, aspect_ratio))


@app.post("/api/photo-to-video")
def api_photo_to_video():
    return photo_to_video()


@app.post("/style-transform")
def style_transform():
    if "image" not in request.files:
        return jsonify({"status": "error", "message": "Upload a photo first."}), 400

    image = request.files["image"]
    if not image.filename:
        return jsonify({"status": "error", "message": "Photo filename is empty."}), 400

    image_path = save_uploaded_file(image)
    reference = request.files.get("reference_image")
    reference_path = save_uploaded_file(reference) if reference and reference.filename else None
    result = transform_image_style(
        image_path=image_path,
        style=request.form.get("style", "cinematic"),
        prompt=request.form.get("prompt", ""),
        reference_path=reference_path,
    )
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@app.post("/api/style-transform")
def api_style_transform():
    return style_transform()


@app.post("/api/tts")
def api_tts():
    data = request.get_json(silent=True) or {}
    result = generate_tts_audio(
        text=data.get("text", ""),
        language=data.get("language", "english"),
        voice=data.get("voice", "narrator"),
        emotion=data.get("emotion", "neutral"),
    )
    code = 200 if result.get("success") else 400
    return jsonify(result), code


@app.post("/api/copilot")
def api_copilot():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    if not prompt.strip():
        return jsonify({"status": "error", "message": "Prompt is required."}), 400
    return jsonify(generate_creator_ai_plan(
        mode=data.get("mode", "copilot"),
        prompt=prompt,
        media_context=data.get("media_context", ""),
    ))


@app.get("/health")
def health():
    ai = ai_health()
    return jsonify({
        "status": "ok",
        "ffmpeg": _has_ffmpeg(),
        "opencv": cv2 is not None,
        "openai": ai["openai"],
        "openai_configured": ai["openai_configured"],
        "use_openai": ai["use_openai"],
        "whisper": ai["whisper"],
        "scene_ai": ai["scene_ai"],
        "silence_ai": ai["silence_ai"],
        "runtime": "vercel" if os.environ.get("VERCEL") else "local",
    })


@app.get("/api/ai/status")
def ai_status():
    ai = ai_health()
    return jsonify({
        "status": "ok",
        "provider": "openai" if ai["openai"] else "local",
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "openai": ai["openai"],
        "openai_configured": ai["openai_configured"],
        "use_openai": ai["use_openai"],
        "whisper": ai["whisper"],
        "scene_ai": ai["scene_ai"],
        "silence_ai": ai["silence_ai"],
        "ffmpeg": _has_ffmpeg(),
    })


@app.post("/api/ai/prompt")
def ai_prompt_preview():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    if not prompt.strip():
        return jsonify({"status": "error", "message": "Prompt is required."}), 400

    actions = understand_prompt(prompt)
    return jsonify({
        "status": "ok",
        "actions": actions,
        "provider": actions.get("source", "local-ai-parser"),
    })


@app.get("/outputs/<path:filename>")
def outputs(filename):
    return send_from_directory(OUTPUT_DIR, filename)


@app.get("/download/<path:filename>")
def download(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
