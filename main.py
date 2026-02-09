#!/usr/bin/env python3
"""
Design2WP Gutenberg — Multi-Page Pipeline

Converts Figma SVG designs to complete WordPress websites using:
- SVG → PNG conversion for GPT-4o Vision analysis
- Embedded image extraction from SVGs
- Kadence/Gutenberg block generation
- WordPress REST API publishing
- Rank Math SEO meta generation
- Kadence Header + Reusable Footer block

Usage:
  python3 main.py --project haugli \
    --svg-dir "~/Documents/figma test/" \
    --wp-url http://kvilhaugsvik.no.datasenter.no \
    --wp-user zocialas --wp-pass Pajero_333

  python3 main.py --project haugli --svg-dir "~/Documents/figma test/" --from-cache
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from svg_processor import identify_pages, extract_embedded_images, svg_to_png, split_png_for_vision
from vision_analyzer import analyze_design
from page_builder import (
    build_page_content, build_footer_content, generate_seo_meta, sanitize_norwegian
)
from kadence_blocks import row_layout, kb_column, adv_heading, adv_btn, _uid


# ─── Page config ───

PAGE_CONFIG = {
    "frontpage": {
        "wp_title": "Hjem",
        "wp_slug": "hjem",
        "is_front_page": True,
        "menu_order": 0,
    },
    "about": {
        "wp_title": "Om oss",
        "wp_slug": "om-oss",
        "menu_order": 1,
    },
    "properties": {
        "wp_title": "Vare eiendommer",
        "wp_slug": "vare-eiendommer",
        "menu_order": 2,
    },
    "single_property": {
        "wp_title": "Eiendom",
        "wp_slug": "eiendom",
        "menu_order": 3,
    },
    "contact": {
        "wp_title": "Kontakt oss",
        "wp_slug": "kontakt-oss",
        "menu_order": 4,
    },
}


def run_pipeline(args):
    """Main pipeline: SVG → Analysis → Blocks → WordPress."""
    svg_dir = Path(args.svg_dir).expanduser()
    project = args.project or "site"
    output_dir = Path(args.output_dir or f"output/{project}")
    output_dir.mkdir(parents=True, exist_ok=True)

    images_dir = Path(args.images_dir).expanduser() if args.images_dir else None

    print(f"\n{'='*60}")
    print(f"  Design2WP — {project}")
    print(f"{'='*60}\n")

    # ── Step 1: Identify pages ──
    print("[1/9] Scanning SVG directory...")
    pages = identify_pages(str(svg_dir))

    content_pages = [p for p in pages if p["role"] not in ("footer", "header")]
    footer_page = next((p for p in pages if p["role"] == "footer"), None)

    print(f"\n  Content pages: {len(content_pages)}")
    if footer_page:
        print(f"  Footer: {footer_page['name']}")

    # ── Step 2: Extract embedded images from SVGs ──
    print(f"\n[2/9] Extracting embedded images...")
    all_extracted = {}
    for page in pages:
        if page["role"] == "footer":
            continue
        extracted = extract_embedded_images(
            page["path"],
            str(output_dir / "images" / sanitize_norwegian(page["name"].replace(" ", "_")))
        )
        all_extracted[page["name"]] = extracted

    existing_images = []
    if images_dir and images_dir.exists():
        for img_file in sorted(images_dir.glob("*")):
            if img_file.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                existing_images.append({"path": str(img_file), "filename": img_file.name})
        print(f"  Found {len(existing_images)} pre-existing images in {images_dir}")

    # ── Step 3: Convert SVGs to PNG for vision analysis ──
    print(f"\n[3/9] Converting SVGs to PNG for vision analysis...")
    png_files = {}
    for page in pages:
        safe_name = sanitize_norwegian(page['name'].replace(' ', '_'))
        png_path = str(output_dir / "png" / f"{safe_name}.png")
        cache_path = output_dir / "png" / f"{safe_name}.png"

        if args.from_cache and cache_path.exists():
            print(f"  [cache] Using cached PNG for {page['name']}")
            png_files[page["name"]] = str(cache_path)
        else:
            try:
                png_files[page["name"]] = svg_to_png(page["path"], png_path, width=1440)
            except Exception as e:
                print(f"  [!] Failed to convert {page['name']}: {e}")
                continue

    # ── Step 4: Vision analysis ──
    print(f"\n[4/9] Analyzing designs with GPT-4o Vision...")
    layouts = {}
    for page in pages:
        page_name = page["name"]
        safe_name = sanitize_norwegian(page_name.replace(' ', '_'))
        cache_file = output_dir / "layouts" / f"{safe_name}.json"
        
        # Also try original name for backwards compat
        orig_cache = output_dir / "layouts" / f"{page_name.replace(' ', '_')}.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        if args.from_cache and (cache_file.exists() or orig_cache.exists()):
            actual_cache = cache_file if cache_file.exists() else orig_cache
            print(f"  [cache] Loading cached layout for {page_name}")
            with open(actual_cache) as f:
                layouts[page_name] = json.load(f)
            continue

        if page_name not in png_files:
            print(f"  [!] No PNG for {page_name}, skipping analysis")
            continue

        png_path = png_files[page_name]
        chunks = split_png_for_vision(png_path, max_height=4000)

        if len(chunks) == 1:
            try:
                layout = analyze_design(chunks[0], model=args.model)
                layouts[page_name] = layout
            except Exception as e:
                print(f"  [!] Vision analysis failed for {page_name}: {e}")
                continue
        else:
            all_sections = []
            for ci, chunk in enumerate(chunks):
                print(f"  [vision] Analyzing {page_name} chunk {ci+1}/{len(chunks)}...")
                try:
                    chunk_layout = analyze_design(chunk, model=args.model)
                    all_sections.extend(chunk_layout.get("sections", []))
                except Exception as e:
                    print(f"  [!] Chunk {ci} failed: {e}")
                time.sleep(1)

            layouts[page_name] = {
                "page_title": page_name,
                "sections": all_sections,
            }

        with open(cache_file, "w") as f:
            json.dump(layouts[page_name], f, indent=2, ensure_ascii=False)
        print(f"  [cache] Saved layout for {page_name}")

        if not args.analyze_only:
            time.sleep(2)

    if args.analyze_only:
        print(f"\n[✓] Analysis complete. Layouts saved to {output_dir}/layouts/")
        return

    # ── Step 5: Upload images to WordPress ──
    uploaded_images = {}

    if args.wp_url:
        print(f"\n[5/9] Uploading images to WordPress...")
        from wp_publisher import WPPublisher
        wp = WPPublisher(args.wp_url, args.wp_user, args.wp_pass)

        for page_name, images in all_extracted.items():
            uploaded = []
            for img in images:
                try:
                    result = wp.upload_media(img["path"], alt_text=f"{project} - {page_name}")
                    result["filename"] = img["filename"]
                    result["original_index"] = img["index"]
                    uploaded.append(result)
                except Exception as e:
                    print(f"  [!] Upload failed for {img['filename']}: {e}")
            uploaded_images[page_name] = uploaded

        if existing_images:
            uploaded_existing = []
            for img in existing_images:
                try:
                    result = wp.upload_media(img["path"], alt_text=f"{project}")
                    result["filename"] = img["filename"]
                    uploaded_existing.append(result)
                except Exception as e:
                    print(f"  [!] Upload failed for {img['filename']}: {e}")
            uploaded_images["_existing"] = uploaded_existing
    else:
        print(f"\n[5/9] Skipping upload (no --wp-url)")

    # ── Step 6: Generate block markup ──
    print(f"\n[6/9] Generating Kadence/Gutenberg block markup...")
    page_contents = {}

    for page in content_pages:
        page_name = page["name"]
        if page_name not in layouts:
            print(f"  [!] No layout for {page_name}, skipping")
            continue

        layout = layouts[page_name]
        role = page["role"]

        page_images = uploaded_images.get(page_name, [])
        page_images += uploaded_images.get("_existing", [])

        markup = build_page_content(layout, page_images, role)

        safe_name = sanitize_norwegian(page_name.replace(' ', '_'))
        html_file = output_dir / "html" / f"{safe_name}.html"
        html_file.parent.mkdir(parents=True, exist_ok=True)
        with open(html_file, "w") as f:
            f.write(markup)
        print(f"  ✓ {page_name} → {html_file.name} ({len(markup)} bytes)")

        page_contents[page_name] = {
            "markup": markup,
            "layout": layout,
            "role": role,
        }

    # Build footer markup from Footer.json
    footer_markup = None
    if footer_page and footer_page["name"] in layouts:
        footer_layout = layouts[footer_page["name"]]
        footer_markup = build_footer_content(footer_layout)
        print(f"  ✓ Footer ({len(footer_markup)} bytes)")

    # ── Step 7-9: Publish to WordPress ──
    if args.wp_url and not args.no_publish:
        print(f"\n[7/9] Publishing to WordPress...")
        _publish_all(wp, page_contents, footer_markup, project, args, layouts)
    else:
        print(f"\n[7-9] Skipping publish")
        print(f"\n[✓] Block markup saved to {output_dir}/html/")

    print(f"\n{'='*60}")
    print(f"  ✓ Pipeline complete!")
    print(f"{'='*60}\n")


def _publish_all(wp, page_contents: dict, footer_markup: str, project: str, args, layouts: dict):
    """Publish all pages to WordPress."""
    created_pages = {}
    page_urls = {}

    # 1. Create footer as reusable block (wp_block)
    footer_block_id = None
    if footer_markup:
        print("\n  [7a] Creating footer as reusable block...")
        footer_block_id = wp.create_reusable_block(
            f"{project} Footer",
            footer_markup
        )
        if footer_block_id:
            print(f"  ✓ Footer reusable block #{footer_block_id}")

    # 2. Create content pages
    print("\n  [7b] Creating pages...")
    for page_name, data in page_contents.items():
        role = data["role"]
        config = PAGE_CONFIG.get(role, {})
        layout = data["layout"]

        title = config.get("wp_title", page_name)
        slug = config.get("wp_slug",
                          sanitize_norwegian(page_name.lower().replace(" ", "-")))

        # Append footer reference to every page
        markup = data["markup"]
        if footer_block_id:
            markup += f'\n\n<!-- wp:block {{"ref":{footer_block_id}}} /-->'

        existing = wp.find_page_by_slug(slug)
        if existing:
            print(f"  Updating: {title} (#{existing['id']})")
            result = wp.update_page(existing["id"], markup, title=title, status="publish")
        else:
            result = wp.create_page(title, markup, status="publish", slug=slug)

        if result:
            page_id = result.get("id")
            page_url = result.get("link", f"{wp.wp_url}/{slug}/")
            created_pages[role] = page_id
            page_urls[role] = page_url

            # Set as front page
            if config.get("is_front_page"):
                wp.set_front_page(page_id)

    # 3. Create Kadence header
    print("\n  [8] Creating Kadence header...")
    header_markup = _generate_header_markup(project, created_pages, wp.wp_url)
    if header_markup:
        wp.create_kadence_header(f"{project} Header", header_markup)

    # 4. Set SEO metadata
    print("\n  [9] Setting SEO metadata...")
    for page_name, data in page_contents.items():
        role = data["role"]
        if role in created_pages:
            seo = generate_seo_meta(data["layout"], role, project)
            wp.set_rank_math_meta(created_pages[role], seo["rank_math_title"], seo["rank_math_description"])

    # Print summary
    print(f"\n  {'='*50}")
    print(f"  PUBLISHED PAGES:")
    for role, page_id in created_pages.items():
        url = page_urls.get(role, "")
        config = PAGE_CONFIG.get(role, {})
        print(f"    #{page_id} {config.get('wp_title', role)}: {url}")
    if footer_block_id:
        print(f"    Footer block: #{footer_block_id} (reusable)")
    print(f"  {'='*50}")


def _generate_header_markup(project: str, created_pages: dict, wp_url: str) -> str:
    """Generate header with logo and navigation using Kadence blocks."""
    nav_items = []
    for role in ["frontpage", "about", "properties", "contact"]:
        config = PAGE_CONFIG.get(role, {})
        if role in created_pages:
            nav_items.append({
                "text": config.get("wp_title", role.title()),
                "link": f"{wp_url}/{config.get('wp_slug', role)}/",
                "background": "transparent",
                "color": "#ffffff",
            })

    if not nav_items:
        return None

    logo = adv_heading(project, level=3, color="#ffffff", size=24, font_weight="700")
    nav = adv_btn(nav_items, align="right")

    logo_col = kb_column([logo])
    nav_col = kb_column([nav])

    return row_layout(
        [logo_col, nav_col],
        columns=2,
        col_layout="left-golden",
        bg_color="#4b250d",
        padding=[15, 15, 30, 30],
    )


def main():
    parser = argparse.ArgumentParser(description="Design2WP — Multi-Page Pipeline")

    parser.add_argument("--project", "-p", default="site", help="Project name")
    parser.add_argument("--svg-dir", required=True, help="Directory with SVG designs")
    parser.add_argument("--images-dir", help="Directory with pre-existing images")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model")

    parser.add_argument("--wp-url", help="WordPress site URL")
    parser.add_argument("--wp-user", help="WordPress username")
    parser.add_argument("--wp-pass", help="WordPress password")
    parser.add_argument("--no-publish", action="store_true")

    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--from-cache", action="store_true")
    parser.add_argument("--pages", nargs="+", help="Only process specific pages")

    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
