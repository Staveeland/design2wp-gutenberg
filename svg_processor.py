"""
SVG Processor — Extract images and convert SVG to PNG for vision analysis.
"""
import re
import base64
import hashlib
import subprocess
from pathlib import Path
from typing import Optional


def extract_embedded_images(svg_path: str, output_dir: str) -> list[dict]:
    """Extract base64-encoded images from SVG file.
    Returns list of {path, mime, hash, index}."""
    svg_path = Path(svg_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(svg_path, "r", errors="replace") as f:
        content = f.read()

    pattern = r'href="data:image/(png|jpeg|jpg|gif|webp);base64,([^"]+)"'
    matches = re.findall(pattern, content)

    results = []
    stem = svg_path.stem.replace(" ", "_")
    # Sanitize Norwegian chars
    for old, new in [('æ', 'ae'), ('ø', 'o'), ('å', 'a'), ('Æ', 'Ae'), ('Ø', 'O'), ('Å', 'A')]:
        stem = stem.replace(old, new)

    for i, (img_type, b64_data) in enumerate(matches):
        ext = "jpg" if img_type in ("jpeg", "jpg") else img_type
        try:
            data = base64.b64decode(b64_data)
        except Exception as e:
            print(f"  [!] Failed to decode image {i}: {e}")
            continue

        img_hash = hashlib.md5(data).hexdigest()[:8]
        filename = f"{stem}_{i}_{img_hash}.{ext}"
        out_path = output_dir / filename

        if not out_path.exists():
            out_path.write_bytes(data)

        results.append({
            "path": str(out_path),
            "filename": filename,
            "mime": f"image/{img_type}",
            "hash": img_hash,
            "index": i,
            "size": len(data),
        })

    print(f"  [svg] Extracted {len(results)} images from {svg_path.name}")
    return results


def svg_to_png(svg_path: str, output_path: str, width: int = 1440) -> str:
    """Convert SVG to PNG using cairosvg. Returns output path."""
    import cairosvg

    svg_path = Path(svg_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"  [svg] Converting {svg_path.name} to PNG (width={width})...")

    try:
        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(output_path),
            output_width=width,
        )
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  [svg] PNG created: {output_path.name} ({size_mb:.1f}MB)")
    except Exception as e:
        print(f"  [svg] cairosvg failed: {e}, trying rsvg-convert...")
        # Fallback to rsvg-convert if available
        try:
            subprocess.run(
                ["rsvg-convert", "-w", str(width), "-o", str(output_path), str(svg_path)],
                check=True, capture_output=True
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            print(f"  [svg] rsvg-convert also failed. Using sips...")
            # macOS fallback: convert via sips (limited but available)
            subprocess.run(
                ["sips", "-s", "format", "png", str(svg_path), "--out", str(output_path)],
                check=True, capture_output=True
            )

    return str(output_path)


def split_png_for_vision(png_path: str, max_height: int = 4000) -> list[str]:
    """Split tall PNGs into chunks for vision API (which has size limits).
    Returns list of chunk file paths."""
    from PIL import Image

    img = Image.open(png_path)
    w, h = img.size

    if h <= max_height:
        return [png_path]

    chunks = []
    path = Path(png_path)
    num_chunks = (h + max_height - 1) // max_height

    for i in range(num_chunks):
        top = i * max_height
        bottom = min((i + 1) * max_height, h)
        # Add overlap for context
        if i > 0:
            top = max(0, top - 200)

        chunk = img.crop((0, top, w, bottom))
        chunk_path = path.with_name(f"{path.stem}_chunk{i}{path.suffix}")
        chunk.save(str(chunk_path), optimize=True, quality=85)
        chunks.append(str(chunk_path))

    print(f"  [svg] Split {path.name} into {len(chunks)} chunks")
    return chunks


def identify_pages(svg_dir: str) -> list[dict]:
    """Scan SVG directory and identify pages with their roles."""
    svg_dir = Path(svg_dir).expanduser()
    if not svg_dir.exists():
        raise FileNotFoundError(f"SVG directory not found: {svg_dir}")

    # Page role mapping
    # Order matters - more specific patterns first
    role_patterns = [
        ("single_property", ["single eiendom", "single property"]),
        ("properties", ["våre eiendommer", "eiendommer", "properties", "portfolio"]),
        ("frontpage", ["fremside", "forside", "front", "home", "hjem"]),
        ("about", ["om oss", "about"]),
        ("contact", ["kontakt", "contact"]),
        ("footer", ["footer", "bunntekst"]),
        ("header", ["header", "topptekst"]),
    ]

    pages = []
    for svg_file in sorted(svg_dir.glob("*.svg")):
        name = svg_file.stem.lower()
        role = "generic"
        for r, patterns in role_patterns:
            if any(p in name for p in patterns):
                role = r
                break

        pages.append({
            "name": svg_file.stem,
            "path": str(svg_file),
            "role": role,
            "size_mb": svg_file.stat().st_size / (1024 * 1024),
        })

    print(f"[svg] Found {len(pages)} SVG files:")
    for p in pages:
        print(f"  - {p['name']} ({p['role']}, {p['size_mb']:.1f}MB)")

    return pages
