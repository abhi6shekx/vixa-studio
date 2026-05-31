def parse_prompt(prompt):
    text = (prompt or "").lower()
    return {
        "cinematic": "cinematic" in text or "movie" in text or "film" in text,
        "dramatic": "dramatic" in text or "intense" in text or "bold" in text,
        "reel": "reel" in text or "short" in text or "tiktok" in text or "vertical" in text,
        "anime": "anime" in text or "manga" in text or "toon" in text,
        "viral": "viral" in text or "shorts" in text or "hook" in text,
        "captions": "caption" in text or "subtitle" in text or "text" in text,
        "music": "music" in text or "song" in text or "beat" in text,
        "silence": "silence" in text or "pause" in text or "boring" in text,
    }
