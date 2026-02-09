"""
GPT-4o Vision Analyzer for Design Screenshots

Analyzes design screenshots/PDFs and returns structured layout data
that can be converted to Gutenberg blocks.
"""
import os
import json
import base64
import sys
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("pip install openai")
    sys.exit(1)


ANALYSIS_PROMPT = """You are an expert web developer analyzing a design screenshot to convert it into WordPress Gutenberg blocks.

Analyze this design image and return a JSON structure describing the layout. For each section (top to bottom), identify:

1. **Section type**: hero, text-section, columns, cta, image-gallery, logo-strip, testimonial, contact, features, stats, footer, media-text, quote
2. **Content**: All text content, headings, paragraphs, button labels
3. **Layout**: Number of columns, alignment, spacing
4. **Styling**: Background colors (hex), text colors (hex), approximate font sizes, padding/margins
5. **Images**: Describe what images are shown (placeholder descriptions)

Return ONLY valid JSON in this exact format:
{
  "page_title": "Page title from design",
  "sections": [
    {
      "type": "hero",
      "background": {"type": "image|color|gradient", "value": "#hex or description", "overlay_opacity": 50},
      "min_height": 600,
      "align": "center|left|right",
      "content": [
        {"type": "heading", "text": "...", "level": 1, "color": "#fff", "font_size": "48px"},
        {"type": "paragraph", "text": "...", "color": "#ccc", "font_size": "18px"},
        {"type": "buttons", "items": [{"text": "CTA", "url": "#", "style": "fill|outline", "bg_color": "#hex", "text_color": "#hex"}]}
      ]
    },
    {
      "type": "columns",
      "columns": 3,
      "background_color": "#fff",
      "padding": {"top": "60px", "bottom": "60px"},
      "items": [
        {
          "content": [
            {"type": "image", "alt": "description", "width": 80, "height": 80},
            {"type": "heading", "text": "...", "level": 3},
            {"type": "paragraph", "text": "..."}
          ]
        }
      ]
    },
    {
      "type": "text-section",
      "background_color": "#hex",
      "align": "center",
      "content": [
        {"type": "heading", "text": "...", "level": 2},
        {"type": "paragraph", "text": "..."},
        {"type": "list", "ordered": false, "items": ["item1", "item2"]}
      ]
    },
    {
      "type": "media-text",
      "media_position": "left|right",
      "media_description": "what the image shows",
      "content": [
        {"type": "heading", "text": "..."},
        {"type": "paragraph", "text": "..."}
      ]
    },
    {
      "type": "quote",
      "text": "Quote text...",
      "citation": "Author name"
    }
  ]
}

Be thorough — extract ALL visible text and styling. Use hex colors. Estimate font sizes.
If you see a section with image on one side and text on the other, use media-text type.

LOGO STRIPS:
- When you see a row of company/brand logos (partners, clients, tenants), use type "logo-strip"
- List each logo as a separate image in the "images" array with a description
- Example: {"type": "logo-strip", "content": [{"type": "heading", ...}], "images": [{"description": "Rema 1000 logo"}, {"description": "Circle K logo"}], "layout": {"columns": 6}}

IMPORTANT — Alignment:
- Set "align" on EVERY section: "center", "left", or "right" based on the design.
- Also set "align" on individual content items (heading, paragraph) when they differ from the section.
- If a heading or text is clearly centered in the design, it MUST have "align": "center".
- Cards/columns with centered text should have "align": "center" on the section.
- Left-aligned text (like body copy) should have "align": "left" or omit it (left is default)."""


def encode_image(image_path: str) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_design(image_path: str, api_key: str = None, model: str = "gpt-5.2") -> dict:
    """
    Analyze a design screenshot using GPT-4o Vision.
    Returns structured layout data.
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    b64 = encode_image(image_path)
    ext = path.suffix.lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".gif": "image/gif", ".webp": "image/webp"}.get(ext, "image/png")

    print(f"[vision] Analyzing {path.name} with {model}...")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a web design analyzer. Return only valid JSON."},
            {"role": "user", "content": [
                {"type": "text", "text": ANALYSIS_PROMPT},
                {"type": "image_url", "image_url": {
                    "url": f"data:{mime};base64,{b64}",
                    "detail": "high"
                }}
            ]}
        ],
        max_completion_tokens=4096,
        temperature=0.1,
        timeout=180,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[:-3]

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[vision] Warning: Failed to parse JSON response: {e}")
        print(f"[vision] Raw response:\n{raw[:500]}")
        raise

    sections = result.get("sections", [])
    print(f"[vision] Found {len(sections)} sections: {[s['type'] for s in sections]}")
    return result


def analyze_design_from_url(image_url: str, api_key: str = None, model: str = "gpt-5.2") -> dict:
    """Analyze a design from a URL instead of a local file."""
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)
    print(f"[vision] Analyzing URL with {model}...")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a web design analyzer. Return only valid JSON."},
            {"role": "user", "content": [
                {"type": "text", "text": ANALYSIS_PROMPT},
                {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}}
            ]}
        ],
        max_completion_tokens=4096,
        temperature=0.1,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[:-3]

    return json.loads(raw)
