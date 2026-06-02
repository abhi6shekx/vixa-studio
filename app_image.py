from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import base64
import uuid
import os

load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/generate-image", methods=["POST"])
def generate_image():
    prompt = request.form.get("prompt", "")

    if not prompt:
        return jsonify({"error": "Prompt missing"}), 400

    enhanced_prompt = enhance_prompt(prompt)

    result = client.images.generate(
        model="gpt-image-1",
        prompt=enhanced_prompt,
        size="1024x1024"
    )

    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    filename = f"vixa_image_{uuid.uuid4().hex}.png"
    output_path = OUTPUT_DIR / filename
    output_path.write_bytes(image_bytes)

    return jsonify({
        "success": True,
        "prompt": enhanced_prompt,
        "image_url": f"/outputs/{filename}"
    })


def enhance_prompt(user_prompt):
    response = client.responses.create(
        model="gpt-5-mini",
        input=f"""
You are Vixa Studio prompt enhancer.
Improve this image prompt for cinematic AI image generation.
Do not add captions, text, logos, watermark, or random words.
User prompt: {user_prompt}
"""
    )

    return response.output_text


@app.route("/outputs/<filename>")
def outputs(filename):
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True)
