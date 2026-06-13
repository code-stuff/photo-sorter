#!/usr/bin/env python3
"""
Photo Sorter — Phase 2 ingest script

Scans a local folder, creates web-friendly JPEG thumbnails for every photo
(including RAW and HEIC via embedded preview extraction), and writes a
manifest.json that the mobile web UI reads.

Usage:
    python ingest.py <source_folder> [--out <output_dir>] [--size 800] [--serve] [--port 8765]

    --out     Output directory (default: <source_folder>/.photo_sorter_web)
    --size    Max thumbnail dimension in pixels (default: 800)
    --serve   Launch a local web server after ingest so phones can connect
    --port    Port for --serve (default: 8765)

Supported formats:
    JPEG / PNG / WebP / GIF     — via Pillow (always available)
    HEIC / HEIF                 — via pillow-heif if installed, else skipped
    RAW (ARW/CR2/CR3/NEF/DNG/…) — embedded JPEG preview via rawpy if installed,
                                   or via exiftool if on PATH, else skipped
"""

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required. Install with: pip install pillow")
    sys.exit(1)

# --- optional RAW / HEIC support ---
try:
    import rawpy  # type: ignore
    HAS_RAWPY = True
except ImportError:
    HAS_RAWPY = False

try:
    from pillow_heif import register_heif_opener  # type: ignore
    register_heif_opener()
    HAS_HEIF = True
except ImportError:
    HAS_HEIF = False

HAS_EXIFTOOL = shutil.which("exiftool") is not None

# File extensions handled by each path
NATIVE_EXTS   = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
HEIC_EXTS     = {".heic", ".heif"}
RAW_EXTS      = {
    ".arw", ".cr2", ".cr3", ".nef", ".nrw", ".dng",
    ".orf", ".raf", ".rw2", ".pef", ".srw", ".x3f",
    ".erf", ".mrw", ".3fr", ".mef", ".kdc", ".dcr",
}
ALL_EXTS = NATIVE_EXTS | HEIC_EXTS | RAW_EXTS


def _thumb_path(out_dir: Path, rel_key: str) -> Path:
    safe = hashlib.md5(rel_key.encode()).hexdigest()[:12] + ".jpg"
    return out_dir / "thumbs" / safe


def _extract_raw_preview_rawpy(src: Path, dest: Path) -> bool:
    try:
        with rawpy.imread(str(src)) as raw:
            thumb = raw.extract_thumb()
        if thumb.format == rawpy.ThumbFormat.JPEG:
            dest.write_bytes(thumb.data)
            return True
        # Bitmap fallback — convert via Pillow
        img = Image.fromarray(thumb.data)
        img.save(str(dest), "JPEG", quality=85)
        return True
    except Exception:
        return False


def _extract_raw_preview_exiftool(src: Path, dest: Path) -> bool:
    try:
        result = subprocess.run(
            ["exiftool", "-b", "-PreviewImage", str(src)],
            capture_output=True, timeout=30
        )
        if result.returncode == 0 and result.stdout:
            dest.write_bytes(result.stdout)
            return True
    except Exception:
        pass
    return False


def make_thumbnail(src: Path, dest: Path, max_size: int) -> bool:
    """
    Create a JPEG thumbnail at dest from src.
    Returns True on success, False if the format is unsupported/decode fails.
    """
    ext = src.suffix.lower()
    dest.parent.mkdir(parents=True, exist_ok=True)

    # --- RAW ---
    if ext in RAW_EXTS:
        tmp = dest.with_suffix(".raw_preview.jpg")
        ok = False
        if HAS_RAWPY:
            ok = _extract_raw_preview_rawpy(src, tmp)
        if not ok and HAS_EXIFTOOL:
            ok = _extract_raw_preview_exiftool(src, tmp)
        if not ok:
            return False
        src_for_thumb = tmp
    else:
        src_for_thumb = src

    # --- HEIC (if not handled by pillow-heif already registered) ---
    try:
        img = Image.open(src_for_thumb)
        img = img.convert("RGB")
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        img.save(str(dest), "JPEG", quality=85, optimize=True)
    except Exception as e:
        if src_for_thumb != src:
            src_for_thumb.unlink(missing_ok=True)
        return False
    finally:
        if src_for_thumb != src:
            src_for_thumb.unlink(missing_ok=True)

    return True


def find_all_images(folder: Path) -> list[Path]:
    found = []
    for ext in ALL_EXTS:
        found.extend(folder.rglob(f"*{ext}"))
        found.extend(folder.rglob(f"*{ext.upper()}"))
    return sorted(set(found))


def ingest(source: Path, out_dir: Path, max_size: int, categories: list[str]) -> dict:
    thumbs_dir = out_dir / "thumbs"
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    images = find_all_images(source)
    entries = []
    skipped = []

    total = len(images)
    for idx, img_path in enumerate(images, 1):
        rel_key = str(img_path.relative_to(source))
        thumb_dest = _thumb_path(out_dir, rel_key)

        if thumb_dest.exists():
            # Already ingested — skip re-generation
            entries.append({
                "key": rel_key,
                "thumb": "thumbs/" + thumb_dest.name,
                "folder": str(Path(rel_key).parent) if Path(rel_key).parent != Path(".") else "",
            })
            print(f"  [{idx}/{total}] (cached) {rel_key}")
            continue

        print(f"  [{idx}/{total}] {rel_key} ...", end=" ", flush=True)
        ok = make_thumbnail(img_path, thumb_dest, max_size)
        if ok:
            entries.append({
                "key": rel_key,
                "thumb": "thumbs/" + thumb_dest.name,
                "folder": str(Path(rel_key).parent) if Path(rel_key).parent != Path(".") else "",
            })
            print("ok")
        else:
            skipped.append(rel_key)
            print("skipped (unsupported format — install rawpy or pillow-heif)")

    manifest = {
        "source": str(source),
        "categories": categories,
        "images": entries,
        "skipped": skipped,
    }

    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest photos into web-friendly thumbnails + manifest for Photo Sorter mobile UI"
    )
    parser.add_argument("source", nargs="?", help="Source photo folder")
    parser.add_argument("--out", help="Output directory (default: <source>/.photo_sorter_web)")
    parser.add_argument("--size", type=int, default=800, help="Max thumbnail dimension (default: 800)")
    parser.add_argument(
        "--categories",
        default="Common,Groom side,Bride side",
        help="Comma-separated category names",
    )
    parser.add_argument("--serve", action="store_true", help="Launch web server after ingest")
    parser.add_argument("--port", type=int, default=8765, help="Port for --serve (default: 8765)")
    parser.add_argument("--demo", action="store_true", help="Use bundled demo images as source")
    args = parser.parse_args()

    if args.demo:
        source = Path(__file__).parent / "demo_images"
    elif args.source:
        source = Path(args.source)
    else:
        parser.print_help()
        sys.exit(1)

    if not source.is_dir():
        print(f"Error: '{source}' is not a directory")
        sys.exit(1)

    out_dir = Path(args.out) if args.out else source.parent / ".photo_sorter_web"
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]

    # Copy the web UI into the output dir
    web_src = Path(__file__).parent / "web" / "index.html"
    if web_src.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(web_src, out_dir / "index.html")

    print(f"Source : {source}")
    print(f"Output : {out_dir}")
    print(f"Formats: native={HAS_RAWPY and 'rawpy' or ''} heic={'yes' if HAS_HEIF else 'no'} raw={'rawpy' if HAS_RAWPY else 'exiftool' if HAS_EXIFTOOL else 'none'}")
    print()

    manifest = ingest(source, out_dir, args.size, categories)

    n = len(manifest["images"])
    s = len(manifest["skipped"])
    print()
    print(f"Done: {n} photos ingested, {s} skipped")
    print(f"Open: {out_dir / 'index.html'}")

    if args.serve:
        import http.server
        import socket
        import threading

        os.chdir(out_dir)

        # Show LAN IP so users can open on phone
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            lan_ip = sock.getsockname()[0]
            sock.close()
        except Exception:
            lan_ip = "localhost"

        print(f"\nServing at http://{lan_ip}:{args.port}/")
        print(f"Open this URL on your phone (same Wi-Fi network)")
        print("Press Ctrl-C to stop\n")

        handler = http.server.SimpleHTTPRequestHandler
        httpd = http.server.HTTPServer(("0.0.0.0", args.port), handler)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
