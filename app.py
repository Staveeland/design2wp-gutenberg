"""
Design2WP Dashboard — FastAPI Web UI
"""
import os
import sys
import json
import hashlib
import sqlite3
import subprocess
import traceback
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# Add project dir to path
sys.path.insert(0, str(Path(__file__).parent))

from vision_analyzer import analyze_design
from converter import convert_layout
from wp_publisher import WPPublisher

app = FastAPI(title="Design2WP Dashboard")

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "projects.db"
UPLOAD_DIR = BASE_DIR / "uploads"
CACHE_DIR = BASE_DIR / "cache"
UPLOAD_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


# ─── Database ───

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            wp_url TEXT NOT NULL,
            wp_user TEXT NOT NULL,
            wp_pass TEXT NOT NULL,
            footer_status TEXT DEFAULT 'pending',
            footer_wp_id INTEGER,
            header_status TEXT DEFAULT 'pending',
            header_wp_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            slug TEXT,
            svg_path TEXT,
            png_path TEXT,
            analysis_json TEXT,
            blocks_html TEXT,
            status TEXT DEFAULT 'pending',
            wp_id INTEGER,
            wp_url TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
    """)
    conn.commit()
    conn.close()


init_db()


# ─── Helpers ───

def svg_to_png(svg_path: str) -> str:
    """Convert SVG to PNG using rsvg-convert or qlmanage."""
    png_path = svg_path.rsplit(".", 1)[0] + ".png"
    # Try rsvg-convert first (best quality)
    try:
        subprocess.run(
            ["rsvg-convert", "-w", "2000", "-o", png_path, svg_path],
            capture_output=True, check=True
        )
        return png_path
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    # Fallback to qlmanage (macOS)
    try:
        subprocess.run(
            ["qlmanage", "-t", "-s", "2000", "-o", os.path.dirname(png_path), svg_path],
            capture_output=True, check=True
        )
        # qlmanage adds .png to the original filename
        ql_path = svg_path + ".png"
        if os.path.exists(ql_path):
            os.rename(ql_path, png_path)
        return png_path
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    raise RuntimeError(f"Could not convert SVG to PNG: {svg_path}")


def file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def cached_analyze(png_path: str) -> dict:
    """Analyze with caching based on file hash."""
    fhash = file_hash(png_path)
    cache_file = CACHE_DIR / f"{fhash}.json"
    if cache_file.exists():
        print(f"[cache] Hit for {fhash[:12]}...")
        return json.loads(cache_file.read_text())

    result = analyze_design(png_path)
    cache_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"[cache] Saved {fhash[:12]}...")
    return result


def get_wp(project: dict) -> WPPublisher:
    return WPPublisher(project["wp_url"], project["wp_user"], project["wp_pass"])


def save_upload(upload: UploadFile, project_id: int, prefix: str) -> str:
    """Save uploaded file and return path."""
    proj_dir = UPLOAD_DIR / str(project_id)
    proj_dir.mkdir(exist_ok=True)
    ext = Path(upload.filename).suffix or ".svg"
    path = proj_dir / f"{prefix}{ext}"
    content = upload.file.read()
    path.write_bytes(content)
    return str(path)


# ─── API Routes ───

@app.get("/", response_class=HTMLResponse)
async def index():
    html = (BASE_DIR / "templates" / "index.html").read_text()
    return HTMLResponse(html)


@app.post("/api/projects")
async def create_project(
    name: str = Form(...),
    wp_url: str = Form(...),
    wp_user: str = Form(...),
    wp_pass: str = Form(...)
):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO projects (name, wp_url, wp_user, wp_pass) VALUES (?, ?, ?, ?)",
        (name, wp_url, wp_user, wp_pass)
    )
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return {"id": pid, "name": name}


@app.get("/api/projects")
async def list_projects():
    conn = get_db()
    rows = conn.execute("SELECT id, name, created_at FROM projects ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/projects/{pid}")
async def get_project(pid: int):
    conn = get_db()
    proj = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    if not proj:
        raise HTTPException(404, "Project not found")
    pages = conn.execute(
        "SELECT id, name, slug, status, wp_id, wp_url, analysis_json IS NOT NULL as has_analysis FROM pages WHERE project_id = ? ORDER BY id",
        (pid,)
    ).fetchall()
    conn.close()
    result = dict(proj)
    result["pages"] = [dict(p) for p in pages]
    # Don't send password to frontend
    result.pop("wp_pass", None)
    return result


@app.post("/api/projects/{pid}/footer")
async def build_footer(pid: int, file: UploadFile = File(...)):
    conn = get_db()
    proj = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    if not proj:
        raise HTTPException(404)

    try:
        svg_path = save_upload(file, pid, "footer")
        png_path = svg_to_png(svg_path)
        analysis = cached_analyze(png_path)
        blocks_html = convert_layout(analysis)

        # Publish as reusable block
        wp = get_wp(dict(proj))
        wp_id = wp.create_reusable_block("Footer", blocks_html)

        conn.execute(
            "UPDATE projects SET footer_status = 'done', footer_wp_id = ? WHERE id = ?",
            (wp_id, pid)
        )
        conn.commit()
        return {"status": "done", "wp_id": wp_id, "sections": len(analysis.get("sections", []))}
    except Exception as e:
        conn.execute("UPDATE projects SET footer_status = 'error' WHERE id = ?", (pid,))
        conn.commit()
        traceback.print_exc()
        raise HTTPException(500, str(e))
    finally:
        conn.close()


@app.post("/api/projects/{pid}/header")
async def build_header(
    pid: int,
    file: UploadFile = File(None),
    title: str = Form(None),
    menu_items: str = Form(None)
):
    conn = get_db()
    proj = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    if not proj:
        raise HTTPException(404)

    try:
        wp = get_wp(dict(proj))

        if file and file.filename:
            svg_path = save_upload(file, pid, "header")
            png_path = svg_to_png(svg_path)
            analysis = cached_analyze(png_path)
            blocks_html = convert_layout(analysis)
        else:
            # Manual header: simple navigation block
            items = json.loads(menu_items) if menu_items else []
            links = "".join(f'<!-- wp:navigation-link {{"label":"{it["title"]}","url":"{it.get("url","#")}","kind":"custom"}} /-->' for it in items)
            blocks_html = f'<!-- wp:navigation -->{links}<!-- /wp:navigation -->'

        result = wp.create_kadence_header(title=title or proj["name"], content=blocks_html)

        wp_id = result.get("id", 0)
        conn.execute(
            "UPDATE projects SET header_status = 'done', header_wp_id = ? WHERE id = ?",
            (wp_id, pid)
        )
        conn.commit()
        return {"status": "done", "wp_id": wp_id}
    except Exception as e:
        conn.execute("UPDATE projects SET header_status = 'error' WHERE id = ?", (pid,))
        conn.commit()
        traceback.print_exc()
        raise HTTPException(500, str(e))
    finally:
        conn.close()


@app.post("/api/projects/{pid}/pages")
async def add_page(
    pid: int,
    name: str = Form(...),
    file: UploadFile = File(None)
):
    conn = get_db()
    proj = conn.execute("SELECT id FROM projects WHERE id = ?", (pid,)).fetchone()
    if not proj:
        raise HTTPException(404)

    slug = name.lower().replace(" ", "-").replace("æ", "ae").replace("ø", "o").replace("å", "a")
    svg_path = None
    png_path = None

    if file and file.filename:
        ext = Path(file.filename).suffix.lower()
        saved_path = save_upload(file, pid, f"page-{slug}")
        if ext in ('.png', '.jpg', '.jpeg'):
            # Image uploaded directly — no conversion needed
            svg_path = None
            png_path = saved_path
        else:
            # SVG — try to convert
            svg_path = saved_path
            pre_png = Path(saved_path).with_suffix(".png")
            if pre_png.exists():
                png_path = str(pre_png)
            else:
                try:
                    png_path = svg_to_png(saved_path)
                except Exception as ex:
                    print(f"[warn] SVG→PNG failed: {ex}. Will need manual PNG.")
                    png_path = None
    else:
        # Check if files already exist on disk (pre-copied)
        upload_dir = UPLOAD_DIR / str(pid)
        for ext in [".png", ".svg"]:
            candidate = upload_dir / f"page-{slug}{ext}"
            if candidate.exists():
                if ext == ".svg":
                    svg_path = str(candidate)
                    png_candidate = upload_dir / f"page-{slug}.png"
                    png_path = str(png_candidate) if png_candidate.exists() else svg_to_png(svg_path)
                else:
                    png_path = str(candidate)
                break

    cur = conn.execute(
        "INSERT INTO pages (project_id, name, slug, svg_path, png_path) VALUES (?, ?, ?, ?, ?)",
        (pid, name, slug, svg_path, png_path)
    )
    conn.commit()
    page_id = cur.lastrowid
    conn.close()
    return {"id": page_id, "name": name, "slug": slug, "has_png": png_path is not None}


@app.post("/api/projects/{pid}/pages/{page_id}/analyze")
async def analyze_page(pid: int, page_id: int, file: UploadFile = File(None)):
    conn = get_db()
    page = conn.execute("SELECT * FROM pages WHERE id = ? AND project_id = ?", (page_id, pid)).fetchone()
    if not page:
        raise HTTPException(404)

    try:
        # If new file uploaded, save it
        if file and file.filename:
            svg_path = save_upload(file, pid, f"page-{page['slug']}")
            png_path = svg_to_png(svg_path)
            conn.execute("UPDATE pages SET svg_path = ?, png_path = ? WHERE id = ?", (svg_path, png_path, page_id))
            conn.commit()
        else:
            png_path = page["png_path"]

        if not png_path or not Path(png_path).exists():
            raise HTTPException(400, "No SVG/PNG file available. Upload one first.")

        analysis = cached_analyze(png_path)
        blocks_html = convert_layout(analysis)

        conn.execute(
            "UPDATE pages SET analysis_json = ?, blocks_html = ?, status = 'analyzed' WHERE id = ?",
            (json.dumps(analysis, ensure_ascii=False), blocks_html, page_id)
        )
        conn.commit()
        return {"status": "analyzed", "analysis": analysis, "sections_count": len(analysis.get("sections", []))}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, str(e))
    finally:
        conn.close()


@app.post("/api/projects/{pid}/pages/{page_id}/publish")
async def publish_page(pid: int, page_id: int):
    conn = get_db()
    page = conn.execute("SELECT * FROM pages WHERE id = ? AND project_id = ?", (page_id, pid)).fetchone()
    proj = conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()
    if not page or not proj:
        raise HTTPException(404)

    if not page["blocks_html"]:
        raise HTTPException(400, "Page not analyzed yet. Run analysis first.")

    try:
        wp = get_wp(dict(proj))

        # Check if page exists
        existing = wp.find_page_by_slug(page["slug"])
        if existing:
            result = wp.update_page(existing["id"], page["blocks_html"], title=page["name"])
        else:
            result = wp.create_page(page["name"], page["blocks_html"], slug=page["slug"])

        wp_id = result.get("id")
        wp_url = result.get("link", "")

        conn.execute(
            "UPDATE pages SET status = 'published', wp_id = ?, wp_url = ? WHERE id = ?",
            (wp_id, wp_url, page_id)
        )
        conn.commit()
        return {"status": "published", "wp_id": wp_id, "wp_url": wp_url}
    except Exception as e:
        conn.execute("UPDATE pages SET status = 'error' WHERE id = ?", (page_id,))
        conn.commit()
        traceback.print_exc()
        raise HTTPException(500, str(e))
    finally:
        conn.close()


@app.get("/api/projects/{pid}/pages/{page_id}/preview")
async def preview_page(pid: int, page_id: int):
    conn = get_db()
    page = conn.execute("SELECT blocks_html, analysis_json FROM pages WHERE id = ? AND project_id = ?", (page_id, pid)).fetchone()
    conn.close()
    if not page:
        raise HTTPException(404)
    return {
        "html": page["blocks_html"] or "",
        "analysis": json.loads(page["analysis_json"]) if page["analysis_json"] else None
    }


# ─── Main ───

if __name__ == "__main__":
    print("🚀 Design2WP Dashboard → http://localhost:8080")
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port, h11_max_incomplete_event_size=100 * 1024 * 1024)
