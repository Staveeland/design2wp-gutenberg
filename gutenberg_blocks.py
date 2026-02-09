"""
Gutenberg Block Markup Generator

Generates valid WordPress Gutenberg block markup (HTML comments with JSON attributes).
Supports core blocks: heading, paragraph, columns, column, image, cover, buttons, button,
group, spacer, separator, list, quote, media-text.
"""
import json
import html as html_lib


def _attrs(block_attrs: dict) -> str:
    """Serialize block attributes to JSON for the comment tag."""
    if not block_attrs:
        return ""
    # Remove None values
    clean = {k: v for k, v in block_attrs.items() if v is not None}
    if not clean:
        return ""
    return " " + json.dumps(clean, ensure_ascii=False)


def _esc(text: str) -> str:
    return html_lib.escape(text) if text else ""


# ─── Core Block Generators ───

def heading(text: str, level: int = 2, text_align: str = None,
            text_color: str = None, background_color: str = None,
            font_size: str = None, style: dict = None) -> str:
    attrs = {}
    if level != 2:
        attrs["level"] = level
    if text_align:
        attrs["textAlign"] = text_align
    if text_color:
        attrs["textColor"] = text_color
    if background_color:
        attrs["backgroundColor"] = background_color
    if font_size:
        attrs["fontSize"] = font_size
    if style:
        attrs["style"] = style

    tag = f"h{level}"
    classes = []
    if text_align:
        classes.append(f"has-text-align-{text_align}")
    if text_color:
        classes.append(f"has-{text_color}-color has-text-color")
    if background_color:
        classes.append(f"has-{background_color}-background-color has-background")
    if font_size:
        classes.append(f"has-{font_size}-font-size")

    class_attr = f' class="{" ".join(classes)}"' if classes else ""
    inline = ""
    if style:
        parts = []
        sp = style.get("spacing", {})
        for prop in ("padding", "margin"):
            vals = sp.get(prop, {})
            for side, val in vals.items():
                parts.append(f"{prop}-{side}:{val}")
        typo = style.get("typography", {})
        if "fontSize" in typo:
            parts.append(f"font-size:{typo['fontSize']}")
        if "lineHeight" in typo:
            parts.append(f"line-height:{typo['lineHeight']}")
        color = style.get("color", {})
        if "text" in color:
            parts.append(f"color:{color['text']}")
        if "background" in color:
            parts.append(f"background-color:{color['background']}")
        if parts:
            inline = f' style="{";".join(parts)}"'

    return (
        f"<!-- wp:heading{_attrs(attrs)} -->\n"
        f"<{tag}{class_attr}{inline}>{_esc(text)}</{tag}>\n"
        f"<!-- /wp:heading -->"
    )


def paragraph(text: str, align: str = None, text_color: str = None,
              background_color: str = None, font_size: str = None,
              drop_cap: bool = False, style: dict = None) -> str:
    attrs = {}
    if align:
        attrs["align"] = align
    if text_color:
        attrs["textColor"] = text_color
    if background_color:
        attrs["backgroundColor"] = background_color
    if font_size:
        attrs["fontSize"] = font_size
    if drop_cap:
        attrs["dropCap"] = True
    if style:
        attrs["style"] = style

    classes = []
    if align:
        classes.append(f"has-text-align-{align}")
    if text_color:
        classes.append(f"has-{text_color}-color has-text-color")
    if background_color:
        classes.append(f"has-{background_color}-background-color has-background")
    if font_size:
        classes.append(f"has-{font_size}-font-size")
    if drop_cap:
        classes.append("has-drop-cap")

    class_attr = f' class="{" ".join(classes)}"' if classes else ""
    return (
        f"<!-- wp:paragraph{_attrs(attrs)} -->\n"
        f"<p{class_attr}>{_esc(text)}</p>\n"
        f"<!-- /wp:paragraph -->"
    )


def image(url: str, alt: str = "", caption: str = None, align: str = None,
          width: int = None, height: int = None, link: str = None,
          size_slug: str = "large", wp_id: int = None) -> str:
    attrs = {"sizeSlug": size_slug}
    if wp_id:
        attrs["id"] = wp_id
    if align:
        attrs["align"] = align
    if link:
        attrs["linkDestination"] = "custom"
    if width:
        attrs["width"] = f"{width}px"
    if height:
        attrs["height"] = f"{height}px"

    classes = [f"size-{size_slug}"]
    if wp_id:
        classes.append(f"wp-image-{wp_id}")
    if align:
        classes = [f"align{align}"] + classes

    fig_class = f"wp-block-image"
    if align:
        fig_class += f" align{align}"
    fig_class += f" size-{size_slug}"

    img_tag = f'<img src="{url}" alt="{_esc(alt)}"'
    if width:
        img_tag += f' width="{width}"'
    if height:
        img_tag += f' height="{height}"'
    if wp_id:
        img_tag += f' class="wp-image-{wp_id}"'
    img_tag += "/>"

    if link:
        img_tag = f'<a href="{link}">{img_tag}</a>'

    caption_html = ""
    if caption:
        caption_html = f"<figcaption class=\"wp-element-caption\">{_esc(caption)}</figcaption>"

    return (
        f"<!-- wp:image{_attrs(attrs)} -->\n"
        f"<figure class=\"{fig_class}\">{img_tag}{caption_html}</figure>\n"
        f"<!-- /wp:image -->"
    )


def columns(inner_blocks: list[str], align: str = None, style: dict = None) -> str:
    attrs = {}
    if align:
        attrs["align"] = align
    if style:
        attrs["style"] = style

    classes = "wp-block-columns"
    if align:
        classes += f" align{align}"

    inner = "\n".join(inner_blocks)
    return (
        f"<!-- wp:columns{_attrs(attrs)} -->\n"
        f"<div class=\"{classes}\">\n{inner}\n</div>\n"
        f"<!-- /wp:columns -->"
    )


def column(inner_blocks: list[str], width: str = None, style: dict = None) -> str:
    attrs = {}
    if width:
        attrs["width"] = width
    if style:
        attrs["style"] = style

    style_attr = f' style="flex-basis:{width}"' if width else ""
    inner = "\n".join(inner_blocks)
    return (
        f"<!-- wp:column{_attrs(attrs)} -->\n"
        f"<div class=\"wp-block-column\"{style_attr}>\n{inner}\n</div>\n"
        f"<!-- /wp:column -->"
    )


def cover(url: str, inner_blocks: list[str], overlay_color: str = None,
          overlay_opacity: int = 50, min_height: int = None,
          dim_ratio: int = None, align: str = "full",
          focal_point: dict = None) -> str:
    attrs = {"url": url}
    if overlay_color:
        attrs["overlayColor"] = overlay_color
    if dim_ratio is not None:
        attrs["dimRatio"] = dim_ratio
    if min_height:
        attrs["minHeight"] = min_height
    if align:
        attrs["align"] = align
    if focal_point:
        attrs["focalPoint"] = focal_point

    classes = "wp-block-cover"
    if align:
        classes += f" align{align}"

    min_h = f"min-height:{min_height}px;" if min_height else ""
    inner = "\n".join(inner_blocks)
    return (
        f"<!-- wp:cover{_attrs(attrs)} -->\n"
        f"<div class=\"{classes}\" style=\"{min_h}\">"
        f"<span aria-hidden=\"true\" class=\"wp-block-cover__background has-background-dim\"></span>"
        f"<img class=\"wp-block-cover__image-background\" alt=\"\" src=\"{url}\" data-object-fit=\"cover\"/>"
        f"<div class=\"wp-block-cover__inner-container\">\n{inner}\n</div></div>\n"
        f"<!-- /wp:cover -->"
    )


def buttons(inner_blocks: list[str], layout: dict = None, align: str = None) -> str:
    attrs = {}
    if layout:
        attrs["layout"] = layout
    if align:
        attrs["align"] = align

    inner = "\n".join(inner_blocks)
    return (
        f"<!-- wp:buttons{_attrs(attrs)} -->\n"
        f"<div class=\"wp-block-buttons\">\n{inner}\n</div>\n"
        f"<!-- /wp:buttons -->"
    )


def button(text: str, url: str = None, background_color: str = None,
           text_color: str = None, style: dict = None, class_name: str = None) -> str:
    attrs = {}
    if background_color:
        attrs["backgroundColor"] = background_color
    if text_color:
        attrs["textColor"] = text_color
    if style:
        attrs["style"] = style
    if class_name:
        attrs["className"] = class_name

    classes = ["wp-block-button__link wp-element-button"]
    if background_color:
        classes.append(f"has-{background_color}-background-color has-background")
    if text_color:
        classes.append(f"has-{text_color}-color has-text-color")

    class_str = " ".join(classes)
    if url:
        link = f'<a class="{class_str}" href="{url}">{_esc(text)}</a>'
    else:
        link = f'<a class="{class_str}">{_esc(text)}</a>'

    outer_classes = "wp-block-button"
    if class_name:
        outer_classes += f" {class_name}"

    return (
        f"<!-- wp:button{_attrs(attrs)} -->\n"
        f"<div class=\"{outer_classes}\">{link}</div>\n"
        f"<!-- /wp:button -->"
    )


def group(inner_blocks: list[str], layout: dict = None, background_color: str = None,
          text_color: str = None, style: dict = None, align: str = None,
          tag_name: str = None) -> str:
    attrs = {}
    if layout:
        attrs["layout"] = layout
    if background_color:
        attrs["backgroundColor"] = background_color
    if text_color:
        attrs["textColor"] = text_color
    if style:
        attrs["style"] = style
    if align:
        attrs["align"] = align
    if tag_name:
        attrs["tagName"] = tag_name

    classes = ["wp-block-group"]
    if background_color:
        classes.append(f"has-{background_color}-background-color has-background")
    if text_color:
        classes.append(f"has-{text_color}-color has-text-color")

    class_str = " ".join(classes)
    inner = "\n".join(inner_blocks)
    return (
        f"<!-- wp:group{_attrs(attrs)} -->\n"
        f"<div class=\"{class_str}\">\n{inner}\n</div>\n"
        f"<!-- /wp:group -->"
    )


def spacer(height: int = 40) -> str:
    attrs = {"height": f"{height}px"}
    return (
        f"<!-- wp:spacer{_attrs(attrs)} -->\n"
        f"<div style=\"height:{height}px\" aria-hidden=\"true\" class=\"wp-block-spacer\"></div>\n"
        f"<!-- /wp:spacer -->"
    )


def separator(style_type: str = "default", color: str = None) -> str:
    attrs = {}
    classes = ["wp-block-separator has-alpha-channel-opacity"]
    if style_type == "wide":
        attrs["className"] = "is-style-wide"
        classes.append("is-style-wide")
    elif style_type == "dots":
        attrs["className"] = "is-style-dots"
        classes.append("is-style-dots")
    if color:
        attrs["backgroundColor"] = color

    return (
        f"<!-- wp:separator{_attrs(attrs)} -->\n"
        f"<hr class=\"{' '.join(classes)}\"/>\n"
        f"<!-- /wp:separator -->"
    )


def list_block(items: list[str], ordered: bool = False) -> str:
    attrs = {}
    if ordered:
        attrs["ordered"] = True

    tag = "ol" if ordered else "ul"
    li_html = "\n".join(
        f"<!-- wp:list-item -->\n<li>{_esc(item)}</li>\n<!-- /wp:list-item -->"
        for item in items
    )

    return (
        f"<!-- wp:list{_attrs(attrs)} -->\n"
        f"<{tag}>\n{li_html}\n</{tag}>\n"
        f"<!-- /wp:list -->"
    )


def quote(text: str, citation: str = None, align: str = None) -> str:
    attrs = {}
    if align:
        attrs["align"] = align

    cite = f"\n<cite>{_esc(citation)}</cite>" if citation else ""
    return (
        f"<!-- wp:quote{_attrs(attrs)} -->\n"
        f"<blockquote class=\"wp-block-quote\">\n"
        f"<p>{_esc(text)}</p>{cite}\n"
        f"</blockquote>\n"
        f"<!-- /wp:quote -->"
    )


def media_text(media_url: str, inner_blocks: list[str], media_position: str = "left",
               media_type: str = "image", media_width: int = 50,
               align: str = None, wp_id: int = None) -> str:
    attrs = {"mediaType": media_type, "mediaPosition": media_position,
             "mediaUrl": media_url, "mediaWidth": media_width}
    if wp_id:
        attrs["mediaId"] = wp_id
    if align:
        attrs["align"] = align

    classes = "wp-block-media-text"
    if align:
        classes += f" align{align}"
    if media_position == "right":
        classes += " has-media-on-the-right"

    grid_cols = f"{media_width}% auto" if media_position == "left" else f"auto {media_width}%"
    inner = "\n".join(inner_blocks)

    return (
        f"<!-- wp:media-text{_attrs(attrs)} -->\n"
        f"<div class=\"{classes}\" style=\"grid-template-columns:{grid_cols}\">"
        f"<figure class=\"wp-block-media-text__media\">"
        f"<img src=\"{media_url}\" alt=\"\"/></figure>"
        f"<div class=\"wp-block-media-text__content\">\n{inner}\n</div></div>\n"
        f"<!-- /wp:media-text -->"
    )
