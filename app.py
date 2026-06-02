from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI, APIError, APIConnectionError, RateLimitError
from dotenv import load_dotenv
from pathlib import Path
import base64
import uuid
import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

load_dotenv()

# Vercel deployment configuration
IS_VERCEL = os.environ.get("VERCEL") is not None
OUTPUT_DIR = Path("/tmp/outputs" if IS_VERCEL else "outputs")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Validate API key on startup
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("❌ ERROR: OPENAI_API_KEY not found in .env file!")
    sys.exit(1)

if not api_key.startswith("sk-"):
    logger.error("❌ ERROR: Invalid API key format!")
    sys.exit(1)

logger.info("✅ API Key loaded successfully")

app = Flask(__name__, static_folder=".", static_url_path="")
client = OpenAI(api_key=api_key)


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


def enhance_prompt(user_prompt):
    """Enhance the user's prompt using ChatGPT"""
    try:
        logger.info("🔄 Enhancing prompt...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are Vixa Studio prompt enhancer. Improve image prompts for cinematic AI image generation. Do not add captions, text, logos, watermark, or random words. Return ONLY the improved prompt, nothing else."
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            max_tokens=200,
            temperature=0.7
        )
        enhanced = response.choices[0].message.content.strip()
        logger.info(f"✅ Enhanced prompt: {enhanced[:100]}...")
        return enhanced
    except Exception as e:
        logger.warning(f"⚠️ Prompt enhancement failed, using original: {str(e)}")
        return user_prompt


@app.route("/generate-image", methods=["POST"])
def generate_image():
    try:
        prompt = request.form.get("prompt", "").strip()
        
        if not prompt:
            logger.warning("⚠️ Empty prompt received")
            return jsonify({"success": False, "error": "Prompt missing"}), 400

        logger.info(f"📝 Received prompt: {prompt[:50]}...")
        
        # Enhance prompt using ChatGPT
        enhanced_prompt = enhance_prompt(prompt)
        
        # Generate image
        logger.info("🎨 Generating image with gpt-image-1...")
        result = client.images.generate(
            model="gpt-image-1",
            prompt=enhanced_prompt,
            size="1024x1024",
            n=1,
            response_format="b64_json"
        )
        
        if not result.data or not result.data[0].b64_json:
            logger.error("❌ No image data returned from OpenAI")
            return jsonify({"success": False, "error": "Image generation failed - no data"}), 500
        
        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)
        
        filename = f"vixa_image_{uuid.uuid4().hex}.png"
        output_path = OUTPUT_DIR / filename
        output_path.write_bytes(image_bytes)
        
        logger.info(f"✅ Image saved: {output_path}")
        
        return jsonify({
            "success": True,
            "prompt": enhanced_prompt,
            "image_url": f"/outputs/{filename}"
        })
        
    except RateLimitError as e:
        error_msg = "Rate limit exceeded. Please wait and try again."
        logger.error(f"❌ {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 429
        
    except APIConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 503
        
    except APIError as e:
        error_msg = f"OpenAI API Error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        if "401" in str(e):
            return jsonify({"success": False, "error": "Invalid API key"}), 401
        return jsonify({"success": False, "error": error_msg}), 500
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/outputs/<filename>")
def outputs(filename):
    return send_from_directory(OUTPUT_DIR, filename)


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api") or request.path.startswith("/outputs"):
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(".", "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "environment": "vercel" if IS_VERCEL else "local"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
