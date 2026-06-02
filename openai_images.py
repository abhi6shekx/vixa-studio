import os
import io
import json
import base64
from datetime import date
try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None

ASSETS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "assets")
USAGE_FILE = os.path.join(ASSETS_DIR, ".vixa_image_usage.json")

def _ensure_assets():
    try:
        os.makedirs(ASSETS_DIR, exist_ok=True)
    except Exception:
        pass


def _load_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None, "no_api_key"
    try:
        from openai import OpenAI
    except Exception:
        return None, "package_missing"
    return OpenAI(api_key=api_key), None


def _read_usage():
    _ensure_assets()
    if not os.path.exists(USAGE_FILE):
        return {}
    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_usage(data):
    _ensure_assets()
    try:
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def can_generate(user_id="local_user", quality="medium"):
    # Cost guard rules: free users limited per-day
    free_limit = int(os.environ.get("VIXA_FREE_DAILY_IMAGES", "5"))
    is_pro = os.environ.get("VIXA_PRO_USER", "false").lower() in {"1", "true", "yes", "on"}
    if is_pro:
        return True, None

    today = date.today().isoformat()
    usage = _read_usage()
    user_usage = usage.get(user_id, {})
    day_count = user_usage.get(today, 0)
    if day_count >= free_limit:
        return False, f"free-daily-limit-reached:{free_limit}"
    # Enforce quality cap for free users
    if quality.lower() in {"ultra", "hd"} and not is_pro:
        return False, "quality-restricted-for-free"
    return True, None


def is_pro_user(user_id="local_user"):
    return os.environ.get("VIXA_PRO_USER", "false").lower() in {"1", "true", "yes", "on"}


def get_quota(user_id="local_user"):
    free_limit = int(os.environ.get("VIXA_FREE_DAILY_IMAGES", "5"))
    is_pro = is_pro_user(user_id)
    if is_pro:
        return {"is_pro": True, "limit": None, "used_today": 0, "remaining": None}
    usage = _read_usage()
    today = date.today().isoformat()
    user_usage = usage.get(user_id, {})
    used = int(user_usage.get(today, 0))
    return {"is_pro": False, "limit": free_limit, "used_today": used, "remaining": max(0, free_limit - used)}


def list_recent(user_id="local_user", limit=12):
    _ensure_assets()
    try:
        files = [f for f in os.listdir(ASSETS_DIR) if not f.startswith('.')]
        files = sorted(files, key=lambda n: os.path.getmtime(os.path.join(ASSETS_DIR, n)), reverse=True)
        return files[:limit]
    except Exception:
        return []


def _apply_watermark(image_path, text="VIXA", opacity=160):
    if Image is None:
        return image_path
    try:
        img = Image.open(image_path).convert("RGBA")
        txt = Image.new("RGBA", img.size, (255,255,255,0))
        draw = ImageDraw.Draw(txt)
        try:
            font = ImageFont.truetype("arial.ttf", max(14, img.size[0] // 30))
        except Exception:
            font = ImageFont.load_default()
        text_w, text_h = draw.textsize(text, font=font)
        margin = 12
        x = img.size[0] - text_w - margin
        y = img.size[1] - text_h - margin
        draw.text((x, y), text, fill=(255,255,255,opacity), font=font)
        out = Image.alpha_composite(img, txt)
        out_path = image_path
        out.convert("RGB").save(out_path, "PNG")
        return out_path
    except Exception:
        return image_path


def record_generation(user_id="local_user"):
    today = date.today().isoformat()
    usage = _read_usage()
    user_usage = usage.get(user_id, {})
    user_usage[today] = user_usage.get(today, 0) + 1
    usage[user_id] = user_usage
    _write_usage(usage)


def enhance_prompt(prompt):
    client, err = _load_openai_client()
    if client is None:
        return {"success": False, "error": err or "no_client"}

    try:
        messages = [
            {"role": "system", "content": "You are a creative image-prompt enhancer. Expand and richly describe short prompts for photorealistic, cinematic, and stylized generation. Return a single improved prompt string."},
            {"role": "user", "content": f"Enhance this prompt for image generation: {prompt}"},
        ]
        resp = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.8,
            max_tokens=200,
        )
        text = resp.choices[0].message.content or prompt
        return {"success": True, "prompt": text.strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _size_for_quality(quality):
    q = (quality or "medium").lower()
    if q == "fast":
        return "512x512"
    if q == "hd":
        return "1024x1024"
    if q == "ultra":
        return "2048x2048"
    return "1024x1024"


def _save_b64_image(b64data, filename):
    _ensure_assets()
    try:
        data = base64.b64decode(b64data)
        path = os.path.join(ASSETS_DIR, filename)
        with open(path, "wb") as fh:
            fh.write(data)
        return path
    except Exception:
        return None


def create_image(prompt, quality="medium", user_id="local_user", reference_path=None, apply_watermark=None):
    ok, reason = can_generate(user_id=user_id, quality=quality)
    if not ok:
        return {"success": False, "error": reason}

    client, err = _load_openai_client()
    if client is None:
        return {"success": False, "error": err or "no_client"}

    size = _size_for_quality(quality)
    try:
        resp = client.images.generate(
            model=os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1"),
            prompt=prompt,
            size=size,
            n=1,
        )
        # response may include base64 data
        b64 = None
        if resp.data and isinstance(resp.data, list) and getattr(resp.data[0], 'b64_json', None):
            b64 = resp.data[0].b64_json
        elif isinstance(resp.data, list) and getattr(resp.data[0], 'url', None):
            # fallback: fetch URL
            import requests
            url = resp.data[0].url
            r = requests.get(url)
            b64 = base64.b64encode(r.content).decode("utf-8")

        if not b64:
            return {"success": False, "error": "no_image_data"}

        filename = f"image_{user_id}_{int(__import__('time').time())}.png"
        path = _save_b64_image(b64, filename)
        if not path:
            return {"success": False, "error": "save_failed"}

        # determine watermark behavior: explicit param overrides default
        if apply_watermark is None:
            apply_wm = not is_pro_user(user_id)
        else:
            apply_wm = bool(apply_watermark)
        if apply_wm:
            wm_text = os.environ.get("VIXA_WATERMARK_TEXT", "VIXA")
            _apply_watermark(path, wm_text)

        record_generation(user_id=user_id)
        return {"success": True, "path": path, "filename": filename}
    except Exception as e:
        return {"success": False, "error": str(e)}


def edit_image(image_path, prompt, quality="medium", user_id="local_user", mask_path=None, apply_watermark=None):
    ok, reason = can_generate(user_id=user_id, quality=quality)
    if not ok:
        return {"success": False, "error": reason}

    client, err = _load_openai_client()
    if client is None:
        return {"success": False, "error": err or "no_client"}

    size = _size_for_quality(quality)
    try:
        # openai client images.edit expects file-like objects for image/mask
        resp = client.images.edit(
            model=os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1"),
            image=open(image_path, "rb"),
            prompt=prompt,
            size=size,
            n=1,
        )

        b64 = None
        if resp.data and isinstance(resp.data, list) and getattr(resp.data[0], 'b64_json', None):
            b64 = resp.data[0].b64_json
        elif isinstance(resp.data, list) and getattr(resp.data[0], 'url', None):
            import requests
            url = resp.data[0].url
            r = requests.get(url)
            b64 = base64.b64encode(r.content).decode("utf-8")

        if not b64:
            return {"success": False, "error": "no_image_data"}

        filename = f"edit_{user_id}_{int(__import__('time').time())}.png"
        path = _save_b64_image(b64, filename)
        if not path:
            return {"success": False, "error": "save_failed"}
        if apply_watermark is None:
            apply_wm = not is_pro_user(user_id)
        else:
            apply_wm = bool(apply_watermark)
        if apply_wm:
            wm_text = os.environ.get("VIXA_WATERMARK_TEXT", "VIXA")
            _apply_watermark(path, wm_text)

        record_generation(user_id=user_id)
        return {"success": True, "path": path, "filename": filename}
    except Exception as e:
        return {"success": False, "error": str(e)}
