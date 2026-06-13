# Photo Sorter

Lightweight photo categorization tool — sort photos into buckets one at a time with a single keystroke or tap. No database, no server, no cloud.

Two modes:

| | **Desktop (Phase 1)** | **Mobile web (Phase 2)** |
|---|---|---|
| Stack | Python + Tkinter | Ingest script + HTML/JS |
| Device | Mac / Windows / Linux | Phone / tablet / browser |
| Input | Local folder | Local folder → thumbnails |
| Output | CSV + JSON (written live) | Download CSV + JSON |
| State | JSON sidecar file | localStorage |

---

## Phase 1 — Desktop app

### Install

```bash
pip install pillow
```

Python 3.9+ and Tkinter (bundled with Python on most platforms) are required.

### Usage

```bash
# Point at a folder (or get a folder picker dialog)
python photo_sorter.py /path/to/photos

# Custom category names
python photo_sorter.py /path/to/photos --categories "Ceremony,Reception,Family"

# Run with bundled demo images
python photo_sorter.py --demo
```

### Keyboard shortcuts

| Key | Action |
|-----|--------|
| `1` | Category 1 (default: Common) |
| `2` | Category 2 (default: Groom side) |
| `3` | Category 3 (default: Bride side) |
| `R` | Reject / skip |
| `←` | Go back |
| `Esc` | Quit |

---

## Phase 2 — Mobile web app

Sort photos on your phone. Run the ingest script on your laptop, then open the URL on any device on the same Wi-Fi network.

### Install

```bash
pip install pillow
# For RAW files (ARW/CR2/CR3/NEF/DNG/…):
pip install rawpy
# For HEIC/HEIF:
pip install pillow-heif
```

### Usage

```bash
# Ingest a folder and launch a local web server
python ingest.py /path/to/photos --serve

# Custom categories
python ingest.py /path/to/photos --categories "Ceremony,Reception,Family" --serve

# Demo
python ingest.py --demo --serve
```

Open `http://<your-laptop-ip>:8765/` on your phone (same Wi-Fi network).

### What the ingest step does

1. Scans the source folder recursively for all images (JPEG, PNG, WebP, GIF, HEIC, RAW)
2. Extracts the embedded JPEG preview from RAW files (no heavy demosaicing) and normalises HEIC
3. Creates small JPEG thumbnails — never touches the originals
4. Writes `manifest.json` + copies `index.html` into the output directory

The web UI reads the manifest and lets you tap buttons (or swipe left/right when ≤3 categories) to sort. Decisions persist in the browser via `localStorage` so you can close and resume.

### Mobile controls

| Action | Gesture / Key |
|--------|--------------|
| Assign category | Tap button **or** keyboard `1`/`2`/`3` |
| Swipe shortcut (≤3 cats) | Swipe left → cat 1, swipe right → cat 2 |
| Reject | Tap **Reject** button or `R` |
| Go back | Tap **← Back** or `←` |
| Export | Tap **Export CSV** / **Export JSON** |

### Output

- `photo_sort_results.csv` — `filename, folder, category` grouped by folder
- `photo_sort_results.json` — same data as JSON array
- Rejected photos appear as `rejected`, not omitted

### RAW / HEIC support

| Format | Handled by |
|--------|-----------|
| JPEG / PNG / WebP / GIF | Pillow (always) |
| HEIC / HEIF | `pillow-heif` (optional) |
| Camera RAW (ARW, CR2, CR3, NEF, DNG, …) | `rawpy` (optional) or `exiftool` if on PATH |

If neither rawpy nor exiftool is installed, RAW files are listed in `skipped` in the manifest.

---

## Categories

Default: `Common`, `Groom side`, `Bride side`. Override with `--categories "Cat1,Cat2,Cat3"`. Up to 9 categories supported (mapped to keys 1–9).
