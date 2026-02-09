"""
Design2WP Gutenberg Converter — Core Blocks Only

Converts GPT-5.2 vision-analysis JSON into valid WordPress Gutenberg
block markup using ONLY core blocks with full styling support.

IMPORTANT: HTML output must EXACTLY match what WordPress's save() function
generates, including class order, CSS property order, and attribute order.
"""
import json
import math
from typing import Optional

_J = lambda d: json.dumps(d, separators=(',', ':'))


def _placeholder_svg(desc: str = "Bilde", w: int = 800, h: int = 400) -> str:
    t = desc.replace("'", "").replace("&", "and")[:60]
    return (
        f"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
        f"width='{w}' height='{h}'%3E%3Crect fill='%23ccc' width='{w}' "
        f"height='{h}'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' "
        f"fill='%23666' font-size='20'%3E{t}%3C/text%3E%3C/svg%3E"
    )


def _build_css(*, border_color=None, border_width=None, border_radius=None,
               color=None, background_color=None, min_height=None,
               padding=None, font_size=None) -> str:
    """Build CSS in WordPress's exact property order."""
    parts = []
    if border_color:
        parts.append(f"border-color:{border_color}")
    if border_width:
        parts.append(f"border-width:{border_width}")
    if border_radius:
        parts.append(f"border-radius:{border_radius}")
    if color:
        parts.append(f"color:{color}")
    if background_color:
        parts.append(f"background-color:{background_color}")
    if min_height:
        parts.append(f"min-height:{min_height}")
    if padding:
        for side in ("top", "right", "bottom", "left"):
            if side in padding:
                parts.append(f"padding-{side}:{padding[side]}")
    if font_size:
        parts.append(f"font-size:{font_size}")
    return ";".join(parts)


# ── Atomic block builders ──────────────────────────────────────────

def _heading(text: str, level: int = 2, color: str = None,
             font_size: str = None, align: str = None) -> str:
    attrs = {}
    style = {}

    if color:
        style.setdefault("color", {})["text"] = color
    if font_size:
        style.setdefault("typography", {})["fontSize"] = font_size
    if align:
        attrs["textAlign"] = align
    if level != 2:
        attrs["level"] = level
    if style:
        attrs["style"] = style

    tag = f"h{level}"
    classes = ["wp-block-heading"]
    if color:
        classes.append("has-text-color")
    if align:
        classes.append(f"has-text-align-{align}")

    css = _build_css(color=color, font_size=font_size)
    style_attr = f' style="{css}"' if css else ""
    class_attr = f' class="{" ".join(classes)}"'

    return (
        f'<!-- wp:heading {_J(attrs)} -->\n'
        f'<{tag}{class_attr}{style_attr}>{text}</{tag}>\n'
        f'<!-- /wp:heading -->'
    )


def _paragraph(text: str, color: str = None, font_size: str = None,
               align: str = None) -> str:
    attrs = {}
    style = {}

    if color:
        style.setdefault("color", {})["text"] = color
    if font_size:
        style.setdefault("typography", {})["fontSize"] = font_size
    if align:
        attrs["align"] = align
    if style:
        attrs["style"] = style

    classes = []
    if align:
        classes.append(f"has-text-align-{align}")
    if color:
        classes.append("has-text-color")

    css = _build_css(color=color, font_size=font_size)
    style_attr = f' style="{css}"' if css else ""
    class_attr = f' class="{" ".join(classes)}"' if classes else ""

    html_text = text.replace("\n", "<br>")
    attr_str = f" {_J(attrs)}" if attrs else ""

    return (
        f'<!-- wp:paragraph{attr_str} -->\n'
        f'<p{class_attr}{style_attr}>{html_text}</p>\n'
        f'<!-- /wp:paragraph -->'
    )


def _image(url: str = None, alt: str = "", width: int = 800,
           height: int = 400) -> str:
    src = url or _placeholder_svg(alt or "Bilde", width, height)
    attrs = {"sizeSlug": "large"}
    return (
        f'<!-- wp:image {_J(attrs)} -->\n'
        f'<figure class="wp-block-image size-large">'
        f'<img src="{src}" alt="{alt}"/></figure>\n'
        f'<!-- /wp:image -->'
    )


def _button(text: str, url: str = "#", bg_color: str = None,
            text_color: str = None, style_type: str = "fill",
            border_radius: str = None) -> str:
    attrs = {}
    style = {}
    link_classes = ["wp-block-button__link"]
    outer_classes = ["wp-block-button"]

    if style_type == "outline":
        outer_classes.append("is-style-outline")
        if bg_color:
            # For outline, bg_color is used as border/text color
            style.setdefault("border", {})["width"] = "2px"
            style["border"]["color"] = bg_color
            style.setdefault("color", {})["text"] = bg_color
            link_classes.append("has-text-color")
            link_classes.append("has-border-color")
            css = _build_css(border_color=bg_color, border_width="2px", color=bg_color)
        else:
            css = ""
    else:
        css_parts = {}
        if bg_color:
            style.setdefault("color", {})["background"] = bg_color
            link_classes.append("has-background")
            css_parts["background_color"] = bg_color
        if text_color:
            style.setdefault("color", {})["text"] = text_color
            link_classes.append("has-text-color")
            css_parts["color"] = text_color
        if border_radius:
            style.setdefault("border", {})["radius"] = border_radius
            css_parts["border_radius"] = border_radius
        css = _build_css(**css_parts)

    # wp-element-button is always added by WP
    link_classes.append("wp-element-button")

    if style:
        attrs["style"] = style

    link_style = f' style="{css}"' if css else ""
    attr_str = f" {_J(attrs)}" if attrs else ""

    return (
        f'<!-- wp:button{attr_str} -->\n'
        f'<div class="{" ".join(outer_classes)}">'
        f'<a class="{" ".join(link_classes)}" href="{url}"{link_style}>{text}</a>'
        f'</div>\n'
        f'<!-- /wp:button -->'
    )


def _buttons(inner: list[str], align: str = None) -> str:
    attrs = {}
    classes = ["wp-block-buttons"]
    if align:
        attrs["layout"] = {"type": "flex", "justifyContent": align}
    content = "\n".join(inner)
    attr_str = f" {_J(attrs)}" if attrs else ""
    return (
        f'<!-- wp:buttons{attr_str} -->\n'
        f'<div class="{" ".join(classes)}">\n{content}\n</div>\n'
        f'<!-- /wp:buttons -->'
    )


def _spacer(height: int = 40) -> str:
    return (
        f'<!-- wp:spacer {_J({"height":f"{height}px"})} -->\n'
        f'<div style="height:{height}px" aria-hidden="true" '
        f'class="wp-block-spacer"></div>\n'
        f'<!-- /wp:spacer -->'
    )


def _separator() -> str:
    return (
        '<!-- wp:separator -->\n'
        '<hr class="wp-block-separator has-alpha-channel-opacity"/>\n'
        '<!-- /wp:separator -->'
    )


def _gallery(images: list[dict], columns: int = 3, crop: bool = True) -> str:
    """WordPress native gallery block — proper grid with captions."""
    img_blocks = []
    for img in images:
        src = img.get("url") or _placeholder_svg(img.get("alt", "Bilde"), 600, 400)
        alt = img.get("alt", "")
        caption = img.get("caption", "")
        img_attrs = {"sizeSlug": "large"}
        caption_html = f"<figcaption class=\"wp-element-caption\">{caption}</figcaption>" if caption else ""
        img_blocks.append(
            f'<!-- wp:image {_J(img_attrs)} -->\n'
            f'<figure class="wp-block-image size-large">'
            f'<img src="{src}" alt="{alt}"/>{caption_html}</figure>\n'
            f'<!-- /wp:image -->'
        )
    
    attrs = {"columns": columns, "linkTo": "none"}
    if crop:
        attrs["imageCrop"] = True
    
    inner = "\n\n".join(img_blocks)
    return (
        f'<!-- wp:gallery {_J(attrs)} -->\n'
        f'<figure class="wp-block-gallery has-nested-images columns-{columns} is-cropped">\n'
        f'{inner}\n'
        f'</figure>\n'
        f'<!-- /wp:gallery -->'
    )


def _list_block(items: list[str], ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    # Each li must be wrapped in wp:list-item
    li_blocks = []
    for item in items:
        li_blocks.append(
            f'<!-- wp:list-item -->\n<li>{item}</li>\n<!-- /wp:list-item -->'
        )
    inner = "\n".join(li_blocks)
    attrs = {}
    if ordered:
        attrs["ordered"] = True
    attr_str = f" {_J(attrs)}" if attrs else ""
    return (
        f'<!-- wp:list{attr_str} -->\n'
        f'<{tag}>\n{inner}\n</{tag}>\n'
        f'<!-- /wp:list -->'
    )


# ── Container blocks ───────────────────────────────────────────────

def _group(inner: list[str], bg_color: str = None, text_color: str = None,
           padding: dict = None, min_height: str = None,
           border_radius: str = None, align: str = None,
           layout_type: str = "constrained") -> str:
    attrs = {"layout": {"type": layout_type}}
    style = {}

    if bg_color:
        style.setdefault("color", {})["background"] = bg_color
    if text_color:
        style.setdefault("color", {})["text"] = text_color
    if padding:
        style.setdefault("spacing", {})["padding"] = padding
    if min_height:
        style.setdefault("dimensions", {})["minHeight"] = min_height
    if border_radius:
        style.setdefault("border", {})["radius"] = border_radius
    if align:
        attrs["align"] = align
    if style:
        attrs["style"] = style

    # Classes - WP order: wp-block-group, alignX, has-border-color, has-text-color, has-background
    classes = ["wp-block-group"]
    if align:
        classes.append(f"align{align}")
    if border_radius:
        pass  # no extra class for border-radius
    if text_color:
        classes.append("has-text-color")
    if bg_color:
        classes.append("has-background")

    css = _build_css(
        border_radius=border_radius,
        color=text_color,
        background_color=bg_color,
        min_height=min_height,
        padding=padding,
    )
    style_attr = f' style="{css}"' if css else ""
    content = "\n".join(inner)

    return (
        f'<!-- wp:group {_J(attrs)} -->\n'
        f'<div class="{" ".join(classes)}"{style_attr}>\n'
        f'{content}\n'
        f'</div>\n'
        f'<!-- /wp:group -->'
    )


def _columns(inner: list[str], align: str = "wide") -> str:
    attrs = {}
    classes = ["wp-block-columns"]
    if align:
        attrs["align"] = align
        classes.append(f"align{align}")
    return (
        f'<!-- wp:columns {_J(attrs)} -->\n'
        f'<div class="{" ".join(classes)}">\n'
        f'{"".join(inner)}\n'
        f'</div>\n'
        f'<!-- /wp:columns -->'
    )


def _column(inner: list[str], width: str = None, bg_color: str = None,
            text_color: str = None, padding: dict = None,
            border_radius: str = None, border_color: str = None,
            border_width: str = None) -> str:
    attrs = {}
    style = {}

    if width:
        attrs["width"] = width
    if bg_color:
        style.setdefault("color", {})["background"] = bg_color
    if text_color:
        style.setdefault("color", {})["text"] = text_color
    if padding:
        style.setdefault("spacing", {})["padding"] = padding
    if border_radius:
        style.setdefault("border", {})["radius"] = border_radius
    if border_width:
        style.setdefault("border", {})["width"] = border_width
    if border_color:
        style.setdefault("border", {})["color"] = border_color
    if style:
        attrs["style"] = style

    # Classes - WP order: wp-block-column, has-border-color, has-text-color, has-background
    classes = ["wp-block-column"]
    if border_color or border_width:
        classes.append("has-border-color")
    if text_color:
        classes.append("has-text-color")
    if bg_color:
        classes.append("has-background")

    css = _build_css(
        border_color=border_color,
        border_width=border_width,
        border_radius=border_radius,
        color=text_color,
        background_color=bg_color,
        padding=padding,
    )
    style_attr = f' style="{css}"' if css else ""
    content = "\n".join(inner)

    return (
        f'<!-- wp:column {_J(attrs)} -->\n'
        f'<div class="{" ".join(classes)}"{style_attr}>\n'
        f'{content}\n'
        f'</div>\n'
        f'<!-- /wp:column -->'
    )


def _cover(inner: list[str], bg_image_url: str = None,
           dim_ratio: int = 50, min_height: int = 600,
           overlay_color: str = None, align: str = "full") -> str:
    attrs = {
        "dimRatio": dim_ratio,
        "minHeight": min_height,
        "isDark": True,
    }
    if bg_image_url:
        attrs["url"] = bg_image_url
    if overlay_color:
        attrs["overlayColor"] = overlay_color
    if align:
        attrs["align"] = align

    content = "\n".join(inner)

    # WP rounds dimRatio to nearest 10 for CSS class
    dim_class_val = round(dim_ratio / 10) * 10

    classes = ["wp-block-cover"]
    if align:
        classes.append(f"align{align}")
    classes.append("is-dark")

    # WP puts img first, then span
    img_tag = ""
    if bg_image_url:
        img_tag = (
            f'<img class="wp-block-cover__image-background" alt="" '
            f'src="{bg_image_url}" data-object-fit="cover"/>'
        )

    return (
        f'<!-- wp:cover {_J(attrs)} -->\n'
        f'<div class="{" ".join(classes)}" style="min-height:{min_height}px">'
        f'{img_tag}'
        f'<span aria-hidden="true" class="wp-block-cover__background has-background-dim-{dim_class_val} has-background-dim"></span>'
        f'<div class="wp-block-cover__inner-container">\n'
        f'{content}\n'
        f'</div></div>\n'
        f'<!-- /wp:cover -->'
    )


# ── Content item converter ─────────────────────────────────────────

def _convert_content_item(item: dict) -> str:
    t = item.get("type")

    if t == "heading":
        return _heading(
            item["text"],
            level=item.get("level", 2),
            color=item.get("color"),
            font_size=item.get("font_size"),
            align=item.get("align"),
        )

    elif t == "paragraph":
        return _paragraph(
            item["text"],
            color=item.get("color"),
            font_size=item.get("font_size"),
            align=item.get("align"),
        )

    elif t == "image":
        return _image(
            url=item.get("url"),
            alt=item.get("alt", ""),
            width=item.get("width", 800),
            height=item.get("height", 400),
        )

    elif t == "buttons":
        btns = []
        for b in item.get("items", []):
            btns.append(_button(
                b["text"],
                url=b.get("url", "#"),
                bg_color=b.get("bg_color"),
                text_color=b.get("text_color"),
                style_type=b.get("style", "fill"),
                border_radius=b.get("border_radius"),
            ))
        return _buttons(btns, align=item.get("align"))

    elif t == "list":
        return _list_block(item.get("items", []), ordered=item.get("ordered", False))

    elif t == "spacer":
        return _spacer(item.get("height", 40))

    elif t == "separator":
        return _separator()

    elif t == "columns":
        # Nested columns inside a section (e.g., footer with multi-column layout)
        col_items = item.get("items", [])
        col_blocks = []
        for col_item in col_items:
            col_inner = [_convert_content_item(c) for c in col_item.get("content", [])]
            col_blocks.append(_column(col_inner))
        return _columns(col_blocks, align="wide")

    return f"<!-- unknown content type: {t} -->"


# ── Alignment propagation ──────────────────────────────────────────

def _apply_section_align(content_item: dict, section_align: str = None) -> dict:
    """Propagate section-level align to content items that don't have their own."""
    if not section_align:
        return content_item
    if content_item.get("align"):
        return content_item  # item has its own alignment, respect it
    if content_item.get("type") in ("heading", "paragraph", "buttons"):
        return {**content_item, "align": section_align}
    return content_item


# Default alignment per section type when vision doesn't specify
_DEFAULT_SECTION_ALIGN = {
    "hero": "center",
    "cta": "center",
    "image-gallery": "center",
    "features": "center",
    "stats": "center",
    "testimonial": "center",
    "quote": "center",
    "logo-strip": "center",
}


def _resolve_section_align(section: dict) -> str:
    """Get alignment for a section: explicit > default by type > None."""
    explicit = section.get("align")
    if explicit:
        return explicit
    return _DEFAULT_SECTION_ALIGN.get(section.get("type"))


# ── Section converters ─────────────────────────────────────────────

def _convert_hero(section: dict) -> str:
    bg = section.get("background", {})
    section_align = _resolve_section_align(section) or "center"
    content = [_convert_content_item(_apply_section_align(c, section_align))
               for c in section.get("content", [])]
    min_h = section.get("min_height", 600)

    if bg.get("type") == "image":
        img_url = bg.get("url") or _placeholder_svg("Hero bakgrunn", 1920, 800)
        return _cover(
            content,
            bg_image_url=img_url,
            dim_ratio=bg.get("overlay_opacity", 50),
            min_height=min_h,
            align="full",
        )
    else:
        bg_color = bg.get("value", "#1a1a2e")
        return _group(
            content,
            bg_color=bg_color,
            padding={"top": "80px", "bottom": "80px", "left": "40px", "right": "40px"},
            min_height=f"{min_h}px",
            align="full",
        )


def _convert_columns_section(section: dict) -> str:
    items = section.get("items", [])
    section_align = _resolve_section_align(section)

    col_blocks = []
    for item in items:
        item_align = item.get("align", section_align)
        inner = [_convert_content_item(_apply_section_align(c, item_align))
                 for c in item.get("content", [])]
        cs = item.get("card_style", {})
        section_styling = section.get("styling", {})
        item_bg = cs.get("background_color") or item.get("background_color")
        item_border_color = cs.get("border_color") or item.get("border_color")
        item_border_width = cs.get("border_width") or item.get("border_width")
        # If no background AND no border, add a subtle border so card is visible
        if not item_bg and not item_border_color:
            item_border_color = "#e0e0e0"
            item_border_width = "1px"
        col_blocks.append(_column(
            inner,
            bg_color=item_bg,
            text_color=cs.get("text_color") or item.get("text_color"),
            padding=cs.get("padding") or item.get("padding") or {"top": "20px", "right": "20px", "bottom": "20px", "left": "20px"},
            border_radius=cs.get("border_radius") or item.get("border_radius") or section_styling.get("card_border_radius"),
            border_color=item_border_color,
            border_width=item_border_width,
        ))

    # Section-level heading before columns
    section_content = [_convert_content_item(_apply_section_align(c, section_align))
                       for c in section.get("content", [])]
    cols_html = _columns(col_blocks, align="wide")

    bg = section.get("background_color")
    pad = section.get("padding")
    if bg or pad or section_content:
        return _group(
            section_content + [cols_html],
            bg_color=bg,
            padding=pad,
            align="full",
        )
    return cols_html


def _convert_cta(section: dict) -> str:
    bg = section.get("background", {})
    bg_color = bg.get("value") if isinstance(bg, dict) else section.get("background_color")
    if not bg_color:
        bg_color = section.get("background_color", "#333333")
    # CTA sections should center text by default
    section_align = _resolve_section_align(section) or "center"
    content = [_convert_content_item(_apply_section_align(c, section_align))
               for c in section.get("content", [])]

    styling = section.get("styling", {})
    pad = styling.get("padding") or section.get("padding") or {
        "top": "80px", "bottom": "80px"
    }
    min_h = section.get("min_height")

    return _group(
        content,
        bg_color=bg_color,
        padding={**pad, "left": pad.get("left", "40px"), "right": pad.get("right", "40px")},
        min_height=f"{min_h}px" if min_h else None,
        align="full",
    )


def _convert_image_gallery(section: dict) -> str:
    section_align = _resolve_section_align(section)
    content_blocks = [_convert_content_item(_apply_section_align(c, section_align))
                      for c in section.get("content", [])]

    images = section.get("images", [])
    layout = section.get("layout", {})
    styling = section.get("styling", {})
    num_cols = layout.get("columns", min(len(images), 3))

    # Build gallery images with captions
    gallery_images = []
    for img in images:
        caption_parts = []
        if img.get("caption_title"):
            caption_parts.append(f"<strong>{img['caption_title']}</strong>")
        if img.get("caption_meta"):
            caption_parts.append(img["caption_meta"])
        gallery_images.append({
            "alt": img.get("description", "Bilde"),
            "url": img.get("url"),
            "caption": "<br>".join(caption_parts) if caption_parts else "",
        })

    gallery_block = _gallery(gallery_images, columns=num_cols)

    bg = section.get("background_color")
    pad = section.get("padding")
    all_inner = content_blocks + [gallery_block]

    if bg or pad:
        return _group(all_inner, bg_color=bg, padding=pad, align="full")
    return "\n\n".join(all_inner)


def _convert_logo_strip(section: dict) -> str:
    """Logo strip — row of logos with equal height, centered."""
    section_align = _resolve_section_align(section) or "center"
    content_blocks = [_convert_content_item(_apply_section_align(c, section_align))
                      for c in section.get("content", [])]

    images = section.get("images", [])
    num_logos = len(images) if images else 6

    gallery_images = []
    for img in images:
        gallery_images.append({
            "alt": img.get("description", "Logo"),
            "url": img.get("url"),
            "caption": "",
        })

    # Use wp:gallery with proper image blocks (editable in WP editor)
    gallery_block = _gallery(gallery_images, columns=min(num_logos, 8), crop=False)

    bg = section.get("background_color")
    pad = section.get("padding", {"top": "40px", "bottom": "40px"})
    all_inner = content_blocks + [gallery_block]

    return _group(all_inner, bg_color=bg, padding=pad, align="full")


def _convert_footer(section: dict) -> str:
    bg_obj = section.get("background", {})
    bg = section.get("background_color") or (bg_obj.get("value") if isinstance(bg_obj, dict) else None) or "#333333"
    pad = section.get("padding", {"top": "60px", "bottom": "60px"})
    layout = section.get("layout", {})
    num_cols = layout.get("columns", 1)

    content = section.get("content", [])

    if num_cols > 1:
        col_groups = []
        current = []
        for c in content:
            if c.get("type") == "heading" and current:
                col_groups.append(current)
                current = []
            current.append(c)
        if current:
            col_groups.append(current)

        while len(col_groups) < num_cols:
            col_groups.append([])

        col_blocks = []
        for grp in col_groups:
            inner = [_convert_content_item(c) for c in grp]
            col_blocks.append(_column(inner))

        cols = _columns(col_blocks, align="wide")
        return _group(
            [cols], bg_color=bg,
            padding={**pad, "left": pad.get("left", "40px"), "right": pad.get("right", "40px")},
            align="full",
        )
    else:
        inner = [_convert_content_item(c) for c in content]
        return _group(
            inner, bg_color=bg,
            padding={**pad, "left": pad.get("left", "40px"), "right": pad.get("right", "40px")},
            align="full",
        )


def _convert_generic(section: dict) -> str:
    section_align = _resolve_section_align(section)
    content = [_convert_content_item(_apply_section_align(c, section_align))
               for c in section.get("content", [])]
    bg = section.get("background_color")
    pad = section.get("padding")
    if bg or pad or content:
        return _group(content, bg_color=bg, padding=pad, align="full")
    return ""


# ── Section dispatcher ─────────────────────────────────────────────

def convert_section(section: dict) -> str:
    t = section.get("type", "")

    if t == "hero":
        return _convert_hero(section)
    elif t in ("columns", "features", "stats"):
        return _convert_columns_section(section)
    elif t == "cta":
        return _convert_cta(section)
    elif t == "image-gallery":
        return _convert_image_gallery(section)
    elif t == "logo-strip":
        return _convert_logo_strip(section)
    elif t == "footer":
        return _convert_footer(section)
    else:
        return _convert_generic(section)


# ── Main entry point ───────────────────────────────────────────────

def _theme_override_css() -> str:
    """Inject CSS to hide theme chrome (title header, footer, content padding)."""
    css = (
        ".site-header { display: none !important; }"
        " .site-footer { display: none !important; }"
        " .entry-hero-container-inner { display: none !important; }"
        " .entry-content-wrap { padding: 0 !important; max-width: 100% !important; }"
        " .wp-block-gallery:not(.is-cropped) .wp-block-image img"
        " { max-height: 60px; width: auto; object-fit: contain; }"
    )
    return (
        f'<!-- wp:html -->\n'
        f'<style>{css}</style>\n'
        f'<!-- /wp:html -->'
    )


def convert_layout(layout_data: dict) -> str:
    """
    Convert full layout data (from vision analyzer) to Gutenberg block markup.
    Returns the complete page content as a string.
    """
    sections = layout_data.get("sections", [])
    blocks = [_theme_override_css()]
    for i, section in enumerate(sections):
        block = convert_section(section)
        if block:
            blocks.append(block)
            if i < len(sections) - 1:
                blocks.append(_spacer(30))

    return "\n\n".join(blocks)
