"""
WordPress REST API Publisher

Publishes Gutenberg block markup to WordPress via the REST API.
Supports creating/updating pages, uploading media, managing templates.
"""
import os
import re
import json
import requests
from pathlib import Path


class WPPublisher:
    """Publish pages to WordPress via REST API."""

    def __init__(self, wp_url: str, username: str, password: str):
        self.wp_url = wp_url.rstrip("/")
        self.api_url = f"{self.wp_url}/wp-json/wp/v2"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)

        # Try cookie auth for better permissions
        self._cookie_login(username, password)
        self._verify_connection()

    def _cookie_login(self, username: str, password: str):
        """Login via wp-login.php and get nonce for REST API."""
        print(f"[wp] Logging in to {self.wp_url}...")
        try:
            self.session.get(f"{self.wp_url}/wp-login.php", timeout=15)
            self.session.post(
                f"{self.wp_url}/wp-login.php",
                data={
                    "log": username, "pwd": password,
                    "wp-submit": "Log In",
                    "redirect_to": f"{self.wp_url}/wp-admin/",
                    "testcookie": "1"
                },
                allow_redirects=True, timeout=15,
            )
            r = self.session.get(
                f"{self.wp_url}/wp-admin/admin-ajax.php?action=rest-nonce",
                timeout=10
            )
            if r.status_code == 200 and len(r.text.strip()) < 20 and r.text.strip() != "0":
                self.session.headers.update({"X-WP-Nonce": r.text.strip()})
                print(f"[wp] Got nonce: {r.text.strip()[:8]}...")
                return
        except Exception:
            pass
        print("[wp] Warning: Could not get REST nonce, using basic auth")

    def _verify_connection(self):
        try:
            r = self.session.get(f"{self.api_url}/users/me", timeout=10)
            if r.status_code == 200:
                print(f"[wp] Connected as: {r.json().get('name', 'unknown')}")
            else:
                print(f"[wp] Warning: Auth check returned {r.status_code}")
        except Exception as e:
            print(f"[wp] Warning: Connection check failed: {e}")

    def create_page(self, title: str, content: str, status: str = "publish",
                    slug: str = None, template: str = None, meta: dict = None) -> dict:
        data = {"title": title, "content": content, "status": status}
        if slug:
            data["slug"] = slug
        if template:
            data["template"] = template
        # Hide theme's page title header and footer — our content has its own
        default_meta = {
            "_kad_post_title": "hide",
            "_kad_post_footer": True,
            "_kad_post_content_style": "unboxed",
        }
        if meta:
            default_meta.update(meta)
        data["meta"] = default_meta

        print(f"[wp] Creating page: {title}...")
        r = self.session.post(f"{self.api_url}/pages", json=data, timeout=30)
        r.raise_for_status()
        result = r.json()
        print(f"[wp] ✓ Created page #{result['id']}: {result.get('link', '')}")
        return result

    def update_page(self, page_id: int, content: str, title: str = None,
                    status: str = None, meta: dict = None) -> dict:
        data = {"content": content}
        if title:
            data["title"] = title
        if status:
            data["status"] = status
        if meta:
            data["meta"] = meta

        r = self.session.post(f"{self.api_url}/pages/{page_id}", json=data, timeout=30)
        r.raise_for_status()
        print(f"[wp] ✓ Updated page #{page_id}")
        return r.json()

    def find_page_by_slug(self, slug: str) -> dict:
        r = self.session.get(f"{self.api_url}/pages", params={"slug": slug}, timeout=10)
        if r.status_code == 200:
            pages = r.json()
            if pages:
                return pages[0]
        return None

    def delete_page(self, page_id: int, force: bool = True) -> bool:
        r = self.session.delete(
            f"{self.api_url}/pages/{page_id}",
            params={"force": force}, timeout=10
        )
        if r.status_code == 200:
            print(f"[wp] ✓ Deleted page #{page_id}")
            return True
        print(f"[wp] Warning: Delete page #{page_id} returned {r.status_code}")
        return False

    def upload_media(self, file_path: str, alt_text: str = None) -> dict:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        mime_types = {
            ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".gif": "image/gif", ".webp": "image/webp",
        }
        mime = mime_types.get(path.suffix.lower(), "application/octet-stream")

        # Sanitize filename for Norwegian chars
        safe_name = path.name
        for old, new in [('æ', 'ae'), ('ø', 'o'), ('å', 'a'), ('Æ', 'Ae'), ('Ø', 'O'), ('Å', 'A')]:
            safe_name = safe_name.replace(old, new)

        # Use ASCII-safe filename in Content-Disposition header
        ascii_name = safe_name.encode('ascii', 'replace').decode('ascii')
        headers = {
            "Content-Disposition": f'attachment; filename="{ascii_name}"',
            "Content-Type": mime,
        }
        data = path.read_bytes()

        print(f"[wp] Uploading {safe_name} ({len(data)//1024}KB)...")
        r = self.session.post(f"{self.api_url}/media", data=data, headers=headers, timeout=120)
        r.raise_for_status()
        result = r.json()
        print(f"[wp] ✓ Uploaded #{result['id']}: {result['source_url']}")

        if alt_text:
            self.session.post(f"{self.api_url}/media/{result['id']}",
                              json={"alt_text": alt_text}, timeout=10)

        return {"id": result["id"], "url": result["source_url"]}

    def set_front_page(self, page_id: int) -> bool:
        r = self.session.post(
            f"{self.wp_url}/wp-json/wp/v2/settings",
            json={"show_on_front": "page", "page_on_front": page_id},
            timeout=10
        )
        if r.status_code == 200:
            print(f"[wp] ✓ Set page #{page_id} as front page")
            return True
        print(f"[wp] Warning: Could not set front page: {r.status_code}")
        return False

    def create_reusable_block(self, title: str, content: str) -> int:
        """Create a reusable block (wp_block). Returns block ID or None."""
        # Check if exists
        r = self.session.get(f"{self.api_url}/blocks", params={"search": title}, timeout=10)
        if r.status_code == 200:
            blocks = r.json()
            for b in blocks:
                if b.get("title", {}).get("raw", "") == title:
                    # Update existing
                    r2 = self.session.post(
                        f"{self.api_url}/blocks/{b['id']}",
                        json={"content": content, "status": "publish"},
                        timeout=30
                    )
                    if r2.status_code == 200:
                        print(f"[wp] ✓ Updated reusable block #{b['id']}: {title}")
                        return b['id']

        r = self.session.post(
            f"{self.api_url}/blocks",
            json={"title": title, "content": content, "status": "publish"},
            timeout=30
        )
        if r.status_code in (200, 201):
            block_id = r.json().get("id")
            print(f"[wp] ✓ Created reusable block #{block_id}: {title}")
            return block_id
        print(f"[wp] Warning: Could not create reusable block: {r.status_code} {r.text[:200]}")
        return None

    def create_kadence_header(self, title: str, content: str) -> dict:
        """Create a Kadence Header via kadence_header CPT."""
        # Check existing
        r = self.session.get(f"{self.api_url}/kadence_header", params={"search": title}, timeout=10)
        existing_id = None
        if r.status_code == 200:
            headers = r.json()
            for h in headers:
                if title.lower() in h.get("title", {}).get("rendered", "").lower():
                    existing_id = h["id"]
                    break

        data = {
            "title": title,
            "content": content,
            "status": "publish",
            "meta": {
                "_kad_header_autoload": "default",
            }
        }

        if existing_id:
            r = self.session.post(f"{self.api_url}/kadence_header/{existing_id}", json=data, timeout=30)
        else:
            r = self.session.post(f"{self.api_url}/kadence_header", json=data, timeout=30)

        if r.status_code in (200, 201):
            result = r.json()
            header_id = result.get("id", "?")
            print(f"[wp] ✓ {'Updated' if existing_id else 'Created'} Kadence header #{header_id}")
            
            # Set as active header in Kadence theme options
            self._set_kadence_header_active(header_id)
            return result
        
        print(f"[wp] Warning: Kadence header creation failed: {r.status_code} {r.text[:200]}")
        return {}

    def _set_kadence_header_active(self, header_id: int):
        """Try to set the Kadence header as active via theme options."""
        # Kadence stores header settings in theme_mods
        # Try via customizer settings API
        try:
            r = self.session.post(
                f"{self.wp_url}/wp-json/wp/v2/settings",
                json={
                    "kadence_header_layout": "custom",
                    "kadence_custom_header": header_id,
                },
                timeout=10
            )
        except Exception:
            pass
        
        # Also try via option update (requires custom endpoint or direct DB)
        # For now the header is created - user may need to activate in Kadence > Header
        print(f"[wp] Note: Kadence header #{header_id} created. May need manual activation in Appearance > Kadence > Header.")

    def set_rank_math_meta(self, page_id: int, title: str, description: str) -> bool:
        meta = {
            "rank_math_title": title,
            "rank_math_description": description,
        }
        r = self.session.post(
            f"{self.api_url}/pages/{page_id}",
            json={"meta": meta},
            timeout=10
        )
        if r.status_code == 200:
            print(f"[wp] ✓ Set SEO meta for page #{page_id}")
            return True
        print(f"[wp] Warning: SEO meta for page #{page_id} returned {r.status_code}")
        return False

    def set_menu(self, menu_items: list) -> bool:
        r = self.session.post(
            f"{self.wp_url}/wp-json/wp/v2/menus",
            json={"name": "Hovedmeny", "slug": "hovedmeny"},
            timeout=10
        )
        if r.status_code in (200, 201):
            menu_id = r.json().get("id")
            for item in menu_items:
                self.session.post(
                    f"{self.wp_url}/wp-json/wp/v2/menu-items",
                    json={
                        "menus": menu_id,
                        "title": item["title"],
                        "url": item.get("url", "#"),
                        "status": "publish",
                    },
                    timeout=10
                )
            print(f"[wp] ✓ Created menu with {len(menu_items)} items")
            return True
        return False
