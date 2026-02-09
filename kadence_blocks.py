"""
Kadence Blocks Generator

Generates valid Kadence Gutenberg blocks. 
IMPORTANT: Kadence blocks use dynamic/server-side rendering.
The HTML between block comments must match the block's save() output exactly.
For most Kadence blocks, save() returns null or minimal markup.
The actual rendering is done by PHP on the server.
"""
import json
import random
import string
import html as html_lib


def _uid(prefix: str = "") -> str:
    """Generate Kadence-style uniqueID like '_a1b2c3'."""
    chars = string.ascii_lowercase + string.digits
    rand = ''.join(random.choices(chars, k=6))
    return f"_{prefix}{rand}"


def _esc(text: str) -> str:
    return html_lib.escape(text) if text else ""


def _attrs(d: dict) -> str:
    clean = {k: v for k, v in d.items() if v is not None}
    if not clean:
        return ""
    return " " + json.dumps(clean, ensure_ascii=False, separators=(',', ':'))


# ─── Kadence Row Layout (Section) ───
# save() returns: <div class="wp-block-kadence-rowlayout alignX kb-row-layout-idUID"><InnerBlocks.Content/></div>

def row_layout(inner_blocks: list[str], unique_id: str = None,
               columns: int = 1, col_layout: str = "equal",
               bg_color: str = None, bg_img: str = None,
               overlay_opacity: float = None, overlay_color: str = None,
               padding: list = None, margin: list = None,
               min_height: int = None, align: str = "full",
               max_width: int = None, vertical_align: str = "middle") -> str:
    uid = unique_id or _uid("r")
    attrs = {
        "uniqueID": uid,
        "columns": columns,
        "colLayout": col_layout,
    }
    if bg_color:
        attrs["bgColor"] = bg_color
    if bg_img:
        attrs["bgImg"] = [{"bgImg": bg_img, "bgImgSize": "cover", "bgImgPosition": "center center"}]
    if overlay_opacity is not None:
        attrs["overlayOpacity"] = overlay_opacity
    if overlay_color:
        attrs["overlay"] = overlay_color
    if padding:
        attrs["topPadding"] = padding[0]
        attrs["bottomPadding"] = padding[1] if len(padding) > 1 else padding[0]
        if len(padding) > 2:
            attrs["leftPadding"] = padding[2]
        if len(padding) > 3:
            attrs["rightPadding"] = padding[3]
    if margin:
        attrs["topMargin"] = margin[0]
        attrs["bottomMargin"] = margin[1] if len(margin) > 1 else margin[0]
    if min_height:
        attrs["minHeight"] = min_height
        attrs["minHeightUnit"] = "px"
    if align:
        attrs["align"] = align
    if max_width:
        attrs["maxWidth"] = max_width
    if vertical_align:
        attrs["verticalAlignment"] = vertical_align

    inner = "\n".join(inner_blocks)
    
    # rowlayout save() returns null — it's fully dynamic
    # Inner blocks go between the comments with no wrapper HTML
    return (
        f'<!-- wp:kadence/rowlayout{_attrs(attrs)} -->\n'
        f'{inner}\n'
        f'<!-- /wp:kadence/rowlayout -->'
    )


# ─── Kadence Column ───
# save() returns: <div class="wp-block-kadence-column kadence-columnUID"><div class="kt-inside-inner-col"><InnerBlocks.Content/></div></div>

def kb_column(inner_blocks: list[str], unique_id: str = None,
              bg_color: str = None, padding: list = None,
              text_color: str = None, text_align: str = None) -> str:
    uid = unique_id or _uid("c")
    attrs = {"uniqueID": uid, "id": 1}
    if bg_color:
        attrs["background"] = bg_color
    if text_color:
        attrs["textColor"] = text_color
    if text_align:
        attrs["textAlign"] = [text_align, "", ""]
    if padding:
        attrs["topPadding"] = padding[0]
        attrs["bottomPadding"] = padding[1] if len(padding) > 1 else padding[0]
        if len(padding) > 2:
            attrs["leftPadding"] = padding[2]
        if len(padding) > 3:
            attrs["rightPadding"] = padding[3]

    inner = "\n".join(inner_blocks)

    # column save() returns the wrapper divs with InnerBlocks.Content inside
    return (
        f'<!-- wp:kadence/column{_attrs(attrs)} -->\n'
        f'<div class="wp-block-kadence-column kadence-column{uid}"><div class="kt-inside-inner-col">{inner}</div></div>\n'
        f'<!-- /wp:kadence/column -->'
    )


# ─── Kadence Advanced Heading ───
# save() returns: <TAG class="kt-adv-headingUID wp-block-kadence-advancedheading" data-kb-block="kb-adv-headingUID">TEXT</TAG>

def adv_heading(text: str, unique_id: str = None, level: int = 2,
                color: str = None, size: int = None, align: str = None,
                font_weight: str = None, line_height: float = None,
                letter_spacing: float = None, margin: list = None,
                padding: list = None, font_family: str = None) -> str:
    uid = unique_id or _uid("h")
    attrs = {
        "uniqueID": uid,
        "level": level,
    }
    if color:
        attrs["color"] = color
    if size:
        attrs["fontSize"] = [size, "", ""]
    if align:
        attrs["align"] = align
    if font_weight:
        attrs["fontWeight"] = font_weight
    if line_height:
        attrs["lineHeight"] = [line_height, "", ""]
    if letter_spacing:
        attrs["letterSpacing"] = letter_spacing
    if margin:
        attrs["margin"] = margin
    if padding:
        attrs["padding"] = padding
    if font_family:
        attrs["typography"] = font_family

    tag = f"h{level}"
    # save() outputs data-kb-block attribute, NO inline style
    return (
        f'<!-- wp:kadence/advancedheading{_attrs(attrs)} -->\n'
        f'<{tag} class="kt-adv-heading{uid} wp-block-kadence-advancedheading" data-kb-block="kb-adv-heading{uid}">{_esc(text)}</{tag}>\n'
        f'<!-- /wp:kadence/advancedheading -->'
    )


# ─── Kadence Advanced Button ───
# save() returns: <div class="wp-block-kadence-advancedbtn kb-buttons-wrap kb-btnsUID kt-btn-align-X kt-btns-wrap kt-btnsUID"><InnerBlocks.Content/></div>

def adv_btn(buttons_data: list[dict], unique_id: str = None, align: str = "center") -> str:
    uid = unique_id or _uid("b")

    btn_blocks = []
    for btn in buttons_data:
        btn_uid = _uid("sb")
        btn_attrs = {
            "uniqueID": btn_uid,
            "text": btn.get("text", "Button"),
            "sizePreset": btn.get("size", "medium"),
        }
        if btn.get("link"):
            btn_attrs["link"] = btn["link"]
        if btn.get("color"):
            btn_attrs["color"] = btn["color"]
        if btn.get("background"):
            btn_attrs["background"] = btn["background"]
        if btn.get("border_radius"):
            btn_attrs["borderRadius"] = btn["border_radius"]

        # singlebtn save() returns null (dynamic block)
        btn_blocks.append(
            f'<!-- wp:kadence/singlebtn{_attrs(btn_attrs)} /-->'
        )

    attrs = {"uniqueID": uid, "hAlign": align}
    inner = "\n".join(btn_blocks)
    return (
        f'<!-- wp:kadence/advancedbtn{_attrs(attrs)} -->\n'
        f'<div class="wp-block-kadence-advancedbtn kb-buttons-wrap kb-btns{uid} kt-btn-align-{align} kt-btns-wrap kt-btns{uid}">\n'
        f'{inner}\n</div>\n'
        f'<!-- /wp:kadence/advancedbtn -->'
    )


# ─── Kadence Info Box ───

def info_box(title: str, text: str, unique_id: str = None,
             icon: str = None, media_type: str = "icon",
             img_url: str = None, link: str = None,
             title_color: str = None, text_color: str = None,
             bg_color: str = None, align: str = "center") -> str:
    uid = unique_id or _uid("ib")
    attrs = {
        "uniqueID": uid,
        "mediaType": media_type,
        "hAlign": align,
    }
    if icon:
        attrs["mediaIcon"] = [{"icon": icon}]
    if img_url:
        attrs["mediaImage"] = [{"url": img_url}]
    if link:
        attrs["link"] = link
    if title_color:
        attrs["titleColor"] = title_color
    if text_color:
        attrs["textColor"] = text_color
    if bg_color:
        attrs["containerBackground"] = bg_color

    # Dynamic block — save returns null
    return f'<!-- wp:kadence/infobox{_attrs(attrs)} /-->'


# ─── Kadence Spacer ───

def kb_spacer(height: int = 40, unique_id: str = None) -> str:
    uid = unique_id or _uid("s")
    attrs = {"uniqueID": uid, "spacerHeight": height}
    # Dynamic block
    return f'<!-- wp:kadence/spacer{_attrs(attrs)} /-->'


# ─── Kadence Image ───
# save() returns: <figure class="wp-block-kadence-image kb-imageUID"><img src="URL" alt="ALT"/></figure>

def kb_image(url: str, unique_id: str = None, alt: str = "",
             wp_id: int = None, align: str = None, max_width: int = None) -> str:
    uid = unique_id or _uid("i")
    attrs = {"uniqueID": uid, "imgLink": url}
    if wp_id:
        attrs["id"] = wp_id
    if align:
        attrs["align"] = align
    if max_width:
        attrs["maxWidth"] = max_width

    # save() outputs figure > img with class="kb-img"
    return (
        f'<!-- wp:kadence/image{_attrs(attrs)} -->\n'
        f'<figure class="wp-block-kadence-image kb-image{uid}">'
        f'<img src="{url}" alt="{_esc(alt)}" class="kb-img"/></figure>\n'
        f'<!-- /wp:kadence/image -->'
    )


# ─── Kadence Testimonials ───

def testimonials(items: list[dict], unique_id: str = None,
                 columns: int = 1, style: str = "card") -> str:
    uid = unique_id or _uid("t")
    test_data = []
    for item in items:
        test_data.append({
            "content": item.get("text", ""),
            "name": item.get("name", ""),
            "title": item.get("title", ""),
            "icon": "star",
            "rating": item.get("rating", 5),
        })

    attrs = {
        "uniqueID": uid,
        "testimonials": test_data,
        "columns": [columns, columns, 1],
        "style": style,
    }

    # Dynamic block
    return f'<!-- wp:kadence/testimonials{_attrs(attrs)} /-->'


# ─── Kadence Icon List ───

def icon_list(items: list[dict], unique_id: str = None,
              icon: str = "fe_check", color: str = None) -> str:
    uid = unique_id or _uid("il")

    list_items = []
    for item in items:
        list_items.append({
            "icon": item.get("icon", icon),
            "text": item.get("text", ""),
        })

    attrs = {
        "uniqueID": uid,
        "items": list_items,
    }
    if color:
        attrs["listStyles"] = [{"color": color}]

    # Dynamic block
    return f'<!-- wp:kadence/iconlist{_attrs(attrs)} /-->'


# ─── Kadence Form ───

def form_block(unique_id: str = None, email: str = "post@haugli.no",
               subject: str = "Ny henvendelse fra nettsiden",
               submit_text: str = "Send melding",
               fields: list = None) -> str:
    uid = unique_id or _uid("f")

    if not fields:
        fields = [
            {"label": "Navn", "type": "text", "required": True, "width": ["50", "", ""]},
            {"label": "E-post", "type": "email", "required": True, "width": ["50", "", ""]},
            {"label": "Telefon", "type": "text", "required": False, "width": ["50", "", ""]},
            {"label": "Emne", "type": "text", "required": False, "width": ["50", "", ""]},
            {"label": "Melding", "type": "textarea", "required": True, "width": ["100", "", ""]},
        ]

    attrs = {
        "uniqueID": uid,
        "fields": fields,
        "email": [{"emailTo": email, "subject": subject}],
        "submit": [{"label": submit_text}],
        "actions": ["email"],
    }

    # Dynamic block
    return f'<!-- wp:kadence/form{_attrs(attrs)} /-->'
