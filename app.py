import os
import subprocess
import uuid

try:
    import cv2
except ImportError:
    cv2 = None
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from ai_engine import ai_health
from editor import process_video
from media_tools import ffmpeg_executable, has_ffmpeg


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
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


@app.get("/health")
def health():
    ai = ai_health()
    return jsonify({
        "status": "ok",
        "ffmpeg": _has_ffmpeg(),
        "opencv": cv2 is not None,
        "openai": ai["openai"],
        "whisper": ai["whisper"],
        "runtime": "vercel" if os.environ.get("VERCEL") else "local",
    })


@app.get("/outputs/<path:filename>")
def outputs(filename):
    return send_from_directory(OUTPUT_DIR, filename)


@app.get("/download/<path:filename>")
def download(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
