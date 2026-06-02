Vixa Studio — OpenAI Image features

This project adds a lightweight OpenAI image generation workflow with cost-guards and a simple UI.

Features
- Text → Image: `/api/image/create` (form-data)
- Image Edit: `/api/image/edit` (form-data)
- Prompt Enhancer: `/api/image/enhance` (JSON)
- Quota endpoint: `/api/image/quota` (GET)
- Recent assets: `/api/image/recent` (GET)
- Outputs saved to `/assets/` and served at `/assets/<filename>`
- UI shows per-quality cost estimates, daily quota meter, and a quick demo button.

Cost & Safety
- Free users limited by `VIXA_FREE_DAILY_IMAGES` (default 5/day).
- Free images are watermarked by default. Set `VIXA_PRO_USER=true` to lift limits.
- `quality=fast` is the default for low-cost testing.
- Image model controlled by `OPENAI_IMAGE_MODEL` in `.env` (default `gpt-image-1`).

How to test locally
1. Ensure `.env` has a valid `OPENAI_API_KEY` and `USE_OPENAI=true`.
2. Install dependencies and start the Flask app:

```bash
pip install -r requirements.txt
export FLASK_APP=app.py
flask run
```

3. Open the Vixa UI and go to "Image" or call endpoints directly with `curl`.

Notes
- The code uses the OpenAI Python SDK shape expected in this repo; SDK responses may differ by version — adjust parsing if needed.
- Watermarking requires Pillow (`PIL`). If missing, watermark step is skipped.
- The implementation favors simplicity and safety for a small-scale desktop/local setup; for multi-user deployments, replace `user_id` handling and usage-store with a proper DB and authentication.
