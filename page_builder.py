"""
Page Builder — Converts vision analysis output to Kadence Gutenberg blocks.

Takes the structured layout JSON from GPT-4o Vision and generates
WordPress-ready block markup using Kadence blocks.
"""
import json
from kadence_blocks import (
    row_layout, kb_column, adv_heading, adv_btn, info_box,
    kb_spacer, kb_image, testimonials, icon_list, form_block, _uid
)
from gutenberg_blocks import (
    paragraph, list_block, separator, quote
)


def _placeholder_svg(desc: str = "Placeholder", w: int = 800, h: int = 400) -> str:
    """Generate a data URI SVG placeholder instead of placehold.co."""
    import urllib.parse
    safe_desc = desc[:40].replace('"', "'")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">'
        f'<rect width="100%" height="100%" fill="#e0e0e0"/>'
        f'<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" '
        f'font-family="Arial,sans-serif" font-size="16" fill="#666">{safe_desc}</text>'
        f'</svg>'
    )
    encoded = urllib.parse.quote(svg)
    return f"data:image/svg+xml,{encoded}"


def sanitize_norwegian(text: str) -> str:
    """Sanitize Norwegian characters for slugs/filenames."""
    return (text.replace('æ', 'ae').replace('Æ', 'Ae')
                .replace('ø', 'o').replace('Ø', 'O')
                .replace('å', 'a').replace('Å', 'A'))


def build_page_content(layout: dict, uploaded_images: list = None,
                       page_role: str = "generic") -> str:
    """Convert vision analysis layout to Kadence Gutenberg block markup."""
    sections = layout.get("sections", [])
    blocks = []
    img_map = {}

    if uploaded_images:
        for img in uploaded_images:
            img_map[img.get("filename", "")] = img
            if "original_index" in img:
                img_map[img["original_index"]] = img

    for section in sections:
        # Skip footer sections embedded in page layouts
        if section.get("type") == "footer":
            continue
        block = _build_section(section, img_map, page_role)
        if block:
            blocks.append(block)

    return "\n\n".join(blocks)


def build_footer_content(layout: dict) -> str:
    """Build footer content from Footer.json layout."""
    sections = layout.get("sections", [])
    if not sections:
        return ""
    
    # The footer layout typically has one section
    section = sections[0]
    content = section.get("content", [])
    bg_color = "#4b250d"
    bg = section.get("background", {})
    if bg.get("value", "").startswith("#"):
        bg_color = bg["value"]
    elif section.get("background_color", "").startswith("#"):
        bg_color = section["background_color"]

    inner_blocks = []
    
    # Check if there's a columns item in content
    columns_item = None
    top_items = []
    for item in content:
        if item.get("type") == "columns":
            columns_item = item
        else:
            top_items.append(item)
    
    # Build top-level items (like main heading)
    for item in top_items:
        inner_blocks.append(_build_content_item(item, {}))
    
    if columns_item:
        # Build multi-column footer
        items = columns_item.get("items", [])
        col_blocks = []
        for col_item in items:
            col_inner = []
            for c in col_item.get("content", []):
                col_inner.append(_build_content_item(c, {}))
            col_blocks.append(kb_column(col_inner))
        
        inner_blocks.append(row_layout(
            col_blocks,
            columns=len(col_blocks),
            col_layout="equal",
            padding=[20, 20, 30, 30],
        ))
    
    # Wrap everything in a footer row
    if not columns_item:
        col = kb_column(inner_blocks, text_align="center")
        return row_layout(
            [col], columns=1,
            bg_color=bg_color,
            padding=[40, 40, 30, 30],
        )
    else:
        # Put the heading + columns layout together
        col = kb_column(inner_blocks)
        return row_layout(
            [col], columns=1,
            bg_color=bg_color,
            padding=[40, 40, 30, 30],
        )


def _get_image_url(img_map: dict, description: str = "", index: int = -1,
                   fallback_w: int = 800, fallback_h: int = 400) -> tuple:
    """Try to find uploaded image, return (url, wp_id)."""
    if index in img_map:
        return img_map[index]["url"], img_map[index].get("id", 0)
    desc_lower = description.lower() if description else ""
    for key, img in img_map.items():
        if isinstance(key, str) and any(w in key.lower() for w in desc_lower.split()[:2] if len(w) > 3):
            return img["url"], img.get("id", 0)
    return _placeholder_svg(description, fallback_w, fallback_h), 0


def _build_section(section: dict, img_map: dict, page_role: str) -> str:
    """Build a single section as Kadence blocks."""
    t = section.get("type", "generic")

    if t == "hero":
        return _build_hero(section, img_map)
    elif t in ("columns", "features", "stats", "services", "team", "about-team"):
        return _build_columns_section(section, img_map)
    elif t in ("text-section", "content"):
        return _build_text_section(section, img_map)
    elif t == "media-text":
        return _build_media_text(section, img_map)
    elif t in ("quote", "testimonial"):
        return _build_testimonial(section)
    elif t in ("cta", "call-to-action"):
        return _build_cta(section, img_map)
    elif t in ("image-gallery", "gallery", "properties-grid"):
        return _build_gallery(section, img_map)
    elif t in ("contact", "contact-form"):
        return _build_contact(section)
    elif t == "map":
        return _build_map(section)
    else:
        return _build_generic(section, img_map)


def _build_hero(section: dict, img_map: dict) -> str:
    bg = section.get("background", {})
    content = section.get("content", [])

    inner_blocks = []
    for item in content:
        inner_blocks.append(_build_content_item(item, img_map))

    bg_img_url = None
    bg_color = None

    if bg.get("type") == "image":
        bg_img_url, _ = _get_image_url(img_map, bg.get("value", "hero background"), 0, 1920, 800)
    elif bg.get("type") == "color":
        bg_color = bg.get("value", "#1a1a2e")
    elif bg.get("value", "").startswith("#"):
        bg_color = bg["value"]
    
    if not bg_color and not bg_img_url:
        bg_color = "#1a1a2e"

    col = kb_column(inner_blocks, text_align=section.get("align", "center"))

    return row_layout(
        [col],
        columns=1,
        bg_img=bg_img_url,
        bg_color=bg_color,
        overlay_color=bg.get("overlay_color", "#000000") if bg_img_url else None,
        overlay_opacity=bg.get("overlay_opacity", 50) / 100 if bg_img_url else None,
        min_height=section.get("min_height", 600),
        padding=[80, 80, 30, 30],
    )


def _build_columns_section(section: dict, img_map: dict) -> str:
    items = section.get("items", [])
    num_cols = section.get("columns", len(items) or 3)
    bg_color = section.get("background_color")

    col_blocks = []
    for item in items:
        inner = []
        for c in item.get("content", []):
            inner.append(_build_content_item(c, img_map))
        col_blocks.append(kb_column(inner, text_align="center"))

    return row_layout(
        col_blocks,
        columns=num_cols,
        col_layout="equal",
        bg_color=bg_color,
        padding=[60, 60, 30, 30],
    )


def _build_text_section(section: dict, img_map: dict) -> str:
    content = section.get("content", [])
    inner = [_build_content_item(c, img_map) for c in content]

    col = kb_column(inner, text_align=section.get("align", "center"))

    return row_layout(
        [col],
        columns=1,
        bg_color=section.get("background_color"),
        padding=[60, 60, 30, 30],
    )


def _build_media_text(section: dict, img_map: dict) -> str:
    content = section.get("content", [])
    inner = [_build_content_item(c, img_map) for c in content]

    media_desc = section.get("media_description", "image")
    img_url, wp_id = _get_image_url(img_map, media_desc, -1, 600, 400)
    pos = section.get("media_position", "left")

    img_col = kb_column([kb_image(img_url, wp_id=wp_id, alt=media_desc)])
    text_col = kb_column(inner)

    cols = [img_col, text_col] if pos == "left" else [text_col, img_col]

    return row_layout(
        cols,
        columns=2,
        col_layout="equal",
        padding=[60, 60, 30, 30],
    )


def _build_testimonial(section: dict) -> str:
    items = []
    text = section.get("text", "")
    citation = section.get("citation", "")
    if section.get("content"):
        for c in section.get("content", []):
            if c.get("type") == "paragraph":
                text = c.get("text", text)
            elif c.get("type") == "heading":
                citation = c.get("text", citation)
    items.append({"text": text, "name": citation, "title": ""})

    col = kb_column([testimonials(items)])
    return row_layout([col], columns=1, padding=[60, 60])


def _build_cta(section: dict, img_map: dict) -> str:
    content = section.get("content", [])
    inner = [_build_content_item(c, img_map) for c in content]

    col = kb_column(inner, text_align="center")
    return row_layout(
        [col],
        columns=1,
        bg_color=section.get("background_color", "#1a1a2e"),
        padding=[80, 80, 30, 30],
    )


def _build_gallery(section: dict, img_map: dict) -> str:
    """Build gallery - can have items (property cards) or content (images)."""
    items = section.get("items", [])
    content = section.get("content", [])
    
    if items:
        # Property card grid
        cols = min(len(items), 4) if items else 3
        col_blocks = []
        for i, item in enumerate(items):
            inner = []
            for c in item.get("content", []):
                inner.append(_build_content_item(c, img_map))
            if not inner:
                img_url, wp_id = _get_image_url(img_map, f"gallery {i}", i)
                inner.append(kb_image(img_url, wp_id=wp_id))
            col_blocks.append(kb_column(inner))

        return row_layout(
            col_blocks,
            columns=cols,
            bg_color=section.get("background_color"),
            padding=[40, 40, 15, 15],
        )
    elif content:
        # Simple image list
        images = [c for c in content if c.get("type") == "image"]
        cols = min(len(images), 4) if images else 3
        col_blocks = []
        for i, img in enumerate(images):
            alt = img.get("alt", f"Bilde {i+1}")
            img_url, wp_id = _get_image_url(img_map, alt, i,
                                             img.get("width", 300), img.get("height", 200))
            col_blocks.append(kb_column([kb_image(img_url, wp_id=wp_id, alt=alt)]))
        
        if col_blocks:
            return row_layout(
                col_blocks,
                columns=cols,
                padding=[40, 40, 15, 15],
            )
    
    return ""


def _build_contact(section: dict) -> str:
    content = section.get("content", [])
    inner = []
    
    form_fields = None
    for c in content:
        if c.get("type") == "form":
            form_fields = c.get("fields", [])
        else:
            inner.append(_build_content_item(c, {}))

    # Build Kadence form with fields from the layout
    if form_fields:
        fields = []
        for f in form_fields:
            label = f.get("label", "")
            ftype = f.get("type", "text")
            if ftype == "tel":
                ftype = "text"
            width = ["100", "", ""]
            if ftype != "textarea":
                width = ["50", "", ""]
            fields.append({
                "label": label,
                "type": ftype,
                "required": f.get("required", False),
                "width": width,
            })
        inner.append(form_block(fields=fields))
    else:
        inner.append(form_block())

    col = kb_column(inner)
    return row_layout([col], columns=1, 
                      bg_color=section.get("background_color"),
                      padding=[60, 60, 30, 30])


def _build_map(section: dict) -> str:
    address = section.get("address", "Haugesund, Norway")
    embed = (
        f'<!-- wp:html -->\n'
        f'<div style="width:100%;height:400px">'
        f'<iframe src="https://maps.google.com/maps?q={address.replace(" ", "+")}&output=embed" '
        f'width="100%" height="400" style="border:0" allowfullscreen loading="lazy"></iframe>'
        f'</div>\n'
        f'<!-- /wp:html -->'
    )
    col = kb_column([embed])
    return row_layout([col], columns=1, padding=[0, 0])


def _build_generic(section: dict, img_map: dict) -> str:
    content = section.get("content", [])
    if not content:
        return ""
    inner = [_build_content_item(c, img_map) for c in content]
    col = kb_column(inner)
    return row_layout([col], columns=1, padding=[40, 40, 30, 30])


def _build_content_item(item: dict, img_map: dict) -> str:
    """Convert a content item to block markup."""
    t = item.get("type", "")

    if t == "heading":
        return adv_heading(
            item.get("text", ""),
            level=item.get("level", 2),
            color=item.get("color"),
            size=_parse_px(item.get("font_size")),
            align=item.get("align"),
            font_weight=item.get("font_weight"),
        )

    elif t == "paragraph":
        style = {}
        if item.get("color"):
            style["color"] = {"text": item["color"]}
        if item.get("font_size"):
            style["typography"] = {"fontSize": item["font_size"]}
        return paragraph(
            item.get("text", ""),
            align=item.get("align"),
            style=style if style else None,
        )

    elif t == "image":
        url = item.get("url")
        alt = item.get("alt", "Bilde")
        if not url:
            url, _ = _get_image_url(img_map, alt, -1,
                                     item.get("width", 800), item.get("height", 400))
        return kb_image(url, alt=alt)

    elif t == "buttons":
        btn_data = []
        for btn in item.get("items", []):
            btn_data.append({
                "text": btn.get("text", "Knapp"),
                "link": btn.get("url", "#"),
                "background": btn.get("bg_color", "#c8a97e"),
                "color": btn.get("text_color", "#ffffff"),
                "border_radius": btn.get("border_radius", 4),
            })
        return adv_btn(btn_data, align=item.get("align", "center"))

    elif t == "list":
        return list_block(item.get("items", []), ordered=item.get("ordered", False))

    elif t == "spacer":
        return kb_spacer(item.get("height", 40))

    elif t == "separator":
        return separator()

    elif t == "quote":
        return quote(item.get("text", ""), citation=item.get("citation"))

    elif t == "icon_list":
        list_items = [{"text": i} for i in item.get("items", [])]
        return icon_list(list_items)

    elif t == "image-gallery":
        # Nested image gallery within a content array (e.g., logos section)
        images = item.get("images", [])
        if images:
            cols = min(len(images), 6)
            col_blocks = []
            for img in images:
                alt = img.get("alt", "Logo")
                url = _placeholder_svg(alt, img.get("width", 100), img.get("height", 50))
                col_blocks.append(kb_column([kb_image(url, alt=alt)]))
            return row_layout(col_blocks, columns=cols, padding=[20, 20, 15, 15])

    elif t == "columns":
        # Nested columns inside content
        items = item.get("items", [])
        num_cols = item.get("columns", len(items))
        col_blocks = []
        for col_item in items:
            col_inner = []
            for c in col_item.get("content", []):
                col_inner.append(_build_content_item(c, img_map))
            col_blocks.append(kb_column(col_inner))
        return row_layout(col_blocks, columns=num_cols, col_layout="equal",
                         padding=[20, 20, 15, 15])

    return f"<!-- Unknown: {t} -->"


def _parse_px(val) -> int:
    """Parse '48px' or 48 to int."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        return int(val.replace("px", "").replace("em", "").strip() or "0")
    return None


def generate_seo_meta(layout: dict, page_role: str, project_name: str = "") -> dict:
    """Generate Rank Math SEO metadata from page content."""
    title_parts = []
    description_parts = []

    page_title = layout.get("page_title", "")
    if page_title:
        title_parts.append(page_title)

    for section in layout.get("sections", [])[:3]:
        if section.get("type") == "footer":
            continue
        for c in section.get("content", []):
            if c.get("type") == "heading" and c.get("text"):
                if not title_parts:
                    title_parts.append(c["text"])
            elif c.get("type") == "paragraph" and c.get("text"):
                description_parts.append(c["text"])

    role_titles = {
        "frontpage": f"{project_name} — Eiendomsutvikling",
        "about": f"Om oss — {project_name}",
        "contact": f"Kontakt oss — {project_name}",
        "properties": f"Vare eiendommer — {project_name}",
        "single_property": f"Eiendom — {project_name}",
    }

    seo_title = title_parts[0] if title_parts else role_titles.get(page_role, project_name)
    seo_desc = description_parts[0][:160] if description_parts else f"{project_name} — profesjonell eiendomsutvikling."

    return {
        "rank_math_title": seo_title,
        "rank_math_description": seo_desc,
    }
