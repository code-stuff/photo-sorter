# Photo Sorter

Lightweight, no-fuss photo categorization tool. Point it at a folder and sort photos one at a time using keyboard shortcuts. No database, no server — just a flat JSON/CSV output.

## Install

```bash
pip install pillow
```

Python 3.9+ and Tkinter (bundled with Python on most platforms) are required.

## Usage

```bash
# Point at a folder (or get a folder picker dialog)
python photo_sorter.py /path/to/photos

# Custom category names
python photo_sorter.py /path/to/photos --categories "Ceremony,Reception,Family"

# Try the bundled demo images
python photo_sorter.py --demo
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1` | Category 1 (default: Common) |
| `2` | Category 2 (default: Groom side) |
| `3` | Category 3 (default: Bride side) |
| `R` | Reject / skip |
| `←` | Go back to previous photo |
| `Esc` | Quit |

## Output

Results are written to the source folder continuously as you sort:

- `photo_sort_results.csv` — `filename, category` for every decided photo
- `photo_sort_results.json` — same data as JSON

Rejected photos appear with category `rejected`, not silently dropped.

## Session Resume

Close and reopen anytime — the app resumes from the first undecided photo. State is stored in `.photo_sorter_state.json` alongside your photos.

## Categories

Default categories are `Common`, `Groom side`, `Bride side` (wedding context). Override with `--categories`:

```bash
python photo_sorter.py /photos --categories "Keynote,Workshop,Social,Reject"
```

Up to 9 categories are supported (mapped to keys 1–9).

## Phase 2 (coming)

- SharePoint folder input
- Swipe gesture support
- Config file for persistent category names
