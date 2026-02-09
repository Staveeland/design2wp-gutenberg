# Design2WP Gutenberg

Convert design screenshots (Figma, XD, etc.) to WordPress Gutenberg block markup using GPT-4o Vision.

## How It Works

```
Design Screenshot/PDF
    ↓  GPT-4o Vision API
Structured Layout JSON (sections, content, styling)
    ↓  Converter
Gutenberg Block Markup (HTML comments + JSON attributes)
    ↓  WordPress REST API
Live WordPress Page (draft or published)
```

## Quick Start

```bash
# Demo mode (no API key needed)
python3 main.py --demo --output output/demo.html

# From a design screenshot
export OPENAI_API_KEY=sk-...
python3 main.py --image design.png --output page.html

# From URL
python3 main.py --url https://example.com/design.png --output page.html

# Publish directly to WordPress
python3 main.py --image design.png \
  --wp-url https://mysite.com \
  --wp-user admin \
  --wp-pass "xxxx xxxx xxxx xxxx" \
  --wp-title "New Landing Page" \
  --wp-status draft \
  --publish
```

## Supported Gutenberg Blocks

| Block | Usage |
|-------|-------|
| `core/heading` | h1–h6 with color, size, alignment |
| `core/paragraph` | Text with color, size, alignment, drop cap |
| `core/columns` + `core/column` | Multi-column layouts (auto-width) |
| `core/image` | Images with captions, links, sizes |
| `core/cover` | Hero sections with background image + overlay |
| `core/buttons` + `core/button` | CTA buttons (fill + outline styles) |
| `core/group` | Section wrapper with background, padding, layout |
| `core/spacer` | Vertical spacing |
| `core/separator` | Horizontal rules (default, wide, dots) |
| `core/list` | Ordered/unordered lists |
| `core/quote` | Blockquotes with citations |
| `core/media-text` | Side-by-side image + text layout |

## Styling Support

All blocks support styling via JSON attributes:

- **Colors**: `backgroundColor`, `textColor`, inline `style.color.text/background`
- **Typography**: `fontSize` (preset or custom), `style.typography.fontSize/lineHeight`
- **Spacing**: `style.spacing.padding/margin` (per-side: top/right/bottom/left)
- **Borders**: `style.border.width/color/radius`

## Block Patterns Export

Generate reusable Block Patterns for the WordPress pattern library:

```bash
# Export as PHP (paste into functions.php or plugin)
python3 main.py --demo --pattern-php patterns/my-patterns.php

# Export as JSON (for programmatic use)
python3 main.py --demo --output page.html --pattern
```

The PHP file registers patterns under the "Design2WP Imports" category.

## WordPress Authentication

Two auth methods:

1. **Application Passwords** (recommended): Create at `/wp-admin/profile.php`
   ```
   --wp-user admin --wp-pass "xxxx xxxx xxxx xxxx"
   ```

2. **Cookie auth** (legacy/shared hosting):
   ```
   --wp-user admin --wp-pass password123 --wp-cookie-auth
   ```

## Architecture

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point |
| `vision_analyzer.py` | GPT-4o Vision → structured layout JSON |
| `converter.py` | Layout JSON → Gutenberg block markup |
| `gutenberg_blocks.py` | Individual block generators (low-level API) |
| `wp_publisher.py` | WordPress REST API client |

## Two-Step Workflow

You can split analysis and conversion:

```bash
# Step 1: Analyze design → JSON
python3 main.py --image design.png --json-output layout.json

# Step 2: Edit layout.json if needed, then convert
python3 main.py --json-input layout.json --output page.html --publish ...
```

## Using as a Library

```python
from vision_analyzer import analyze_design
from converter import convert_layout, convert_to_pattern
from wp_publisher import WPPublisher

# Analyze
layout = analyze_design("design.png")

# Convert
markup = convert_layout(layout)

# Publish
wp = WPPublisher("https://site.com", "admin", "app-password")
wp.create_page("My Page", markup, status="draft")

# Or export as pattern
pattern = convert_to_pattern(layout)
```

## Requirements

- Python 3.9+
- `openai` — GPT-4o Vision API
- `requests` — WordPress REST API

```bash
pip install openai requests
```

## Evolved From

This is the Gutenberg successor to [Design2WP v3](../design2wp-v3/) which generated WPBakery/Impreza shortcodes. Same pipeline concept, modern output format.

---

**Zocial AS** / Workflows — Web design automation pipeline.
