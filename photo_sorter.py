#!/usr/bin/env python3
"""
Photo Sorter — Phase 1
Lightweight tool to categorize photos from a local folder into buckets.

Usage:
    python photo_sorter.py <folder_path> [--categories "Cat1,Cat2,Cat3"] [--demo]

Keys:
    1       = Category 1
    2       = Category 2
    3       = Category 3
    r       = Reject/Skip
    Left    = Go back to previous photo
    Escape  = Quit
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    from PIL import Image, ImageTk
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install pillow")
    sys.exit(1)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
STATE_FILE_SUFFIX = ".photo_sorter_state.json"

DEFAULT_CATEGORIES = ["Common", "Groom side", "Bride side"]


def find_images(folder: Path) -> list[Path]:
    images = []
    for ext in SUPPORTED_EXTENSIONS:
        images.extend(folder.rglob(f"*{ext}"))
        images.extend(folder.rglob(f"*{ext.upper()}"))
    return sorted(set(images))


def load_state(folder: Path) -> dict:
    state_file = folder / STATE_FILE_SUFFIX
    if state_file.exists():
        try:
            with open(state_file) as f:
                return json.load(f)
        except Exception:
            pass
    return {"decisions": {}}


def save_state(folder: Path, state: dict) -> None:
    state_file = folder / STATE_FILE_SUFFIX
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def export_results(folder: Path, images: list[Path], decisions: dict) -> None:
    csv_path = folder / "photo_sort_results.csv"
    json_path = folder / "photo_sort_results.json"

    rows = []
    for img in images:
        key = str(img.relative_to(folder))
        category = decisions.get(key)
        if category is not None:
            rows.append({"filename": key, "category": category})

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "category"])
        writer.writeheader()
        writer.writerows(rows)

    with open(json_path, "w") as f:
        json.dump(rows, f, indent=2)


class PhotoSorter:
    def __init__(self, root: tk.Tk, folder: Path, categories: list[str]):
        self.root = root
        self.folder = folder
        self.categories = categories
        self.images = find_images(folder)

        if not self.images:
            messagebox.showerror("No images found", f"No supported images found in:\n{folder}")
            root.destroy()
            return

        self.state = load_state(folder)
        self.decisions = self.state["decisions"]

        # Find first undecided photo index
        self.index = 0
        for i, img in enumerate(self.images):
            if str(img.relative_to(self.folder)) not in self.decisions:
                self.index = i
                break
        else:
            # All decided — start from end
            self.index = len(self.images) - 1

        self._setup_ui()
        self._bind_keys()
        self._show_current()

    def _setup_ui(self) -> None:
        self.root.title("Photo Sorter")
        self.root.configure(bg="#1a1a1a")
        self.root.geometry("1000x750")
        self.root.minsize(640, 480)

        # Top bar: progress
        top = tk.Frame(self.root, bg="#1a1a1a")
        top.pack(fill="x", padx=10, pady=(8, 0))

        self.progress_label = tk.Label(
            top, text="", bg="#1a1a1a", fg="#aaaaaa", font=("Helvetica", 13)
        )
        self.progress_label.pack(side="left")

        self.filename_label = tk.Label(
            top, text="", bg="#1a1a1a", fg="#cccccc", font=("Helvetica", 12)
        )
        self.filename_label.pack(side="right")

        # Image canvas
        self.canvas = tk.Canvas(self.root, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=8)

        # Decision status label (shows current tag if already decided)
        self.decision_label = tk.Label(
            self.root, text="", bg="#1a1a1a", fg="#44bb44", font=("Helvetica", 14, "bold")
        )
        self.decision_label.pack()

        # Bottom bar: shortcuts
        shortcuts = self._build_shortcut_text()
        tk.Label(
            self.root,
            text=shortcuts,
            bg="#1a1a1a",
            fg="#666666",
            font=("Helvetica", 11),
        ).pack(pady=(0, 8))

        self._img_ref = None  # prevent GC

    def _build_shortcut_text(self) -> str:
        parts = []
        for i, cat in enumerate(self.categories, 1):
            parts.append(f"[{i}] {cat}")
        parts.append("[R] Reject")
        parts.append("[←] Back")
        parts.append("[Esc] Quit")
        return "   ".join(parts)

    def _bind_keys(self) -> None:
        for i, cat in enumerate(self.categories, 1):
            self.root.bind(f"<Key-{i}>", lambda e, c=cat: self._decide(c))
        self.root.bind("<Key-r>", lambda e: self._decide("rejected"))
        self.root.bind("<Key-R>", lambda e: self._decide("rejected"))
        self.root.bind("<Left>", lambda e: self._go_back())
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<Configure>", lambda e: self._resize())

    def _show_current(self) -> None:
        if not self.images:
            return

        img_path = self.images[self.index]
        img_key = str(img_path.relative_to(self.folder))
        decided = sum(1 for img in self.images if str(img.relative_to(self.folder)) in self.decisions)
        self.progress_label.config(text=f"{decided}/{len(self.images)} sorted")
        self.filename_label.config(text=img_key)

        current_decision = self.decisions.get(img_key)
        if current_decision:
            self.decision_label.config(text=f"Tagged: {current_decision}")
        else:
            self.decision_label.config(text="")

        try:
            pil_img = Image.open(img_path)
            self._current_pil = pil_img
            self._render_image()
        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(
                self.canvas.winfo_width() // 2 or 400,
                self.canvas.winfo_height() // 2 or 300,
                text=f"Could not load image:\n{e}",
                fill="#ff6666",
                font=("Helvetica", 14),
            )

    def _render_image(self) -> None:
        if not hasattr(self, "_current_pil"):
            return
        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 600
        if cw < 10 or ch < 10:
            return

        img = self._current_pil.copy()
        img.thumbnail((cw, ch), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(img)
        self._img_ref = tk_img

        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2, anchor="center", image=tk_img)

    def _resize(self) -> None:
        self.root.after(50, self._render_image)

    def _decide(self, category: str) -> None:
        img = self.images[self.index]
        img_key = str(img.relative_to(self.folder))
        self.decisions[img_key] = category
        self.state["decisions"] = self.decisions
        save_state(self.folder, self.state)
        export_results(self.folder, self.images, self.decisions)

        decided = sum(1 for i in self.images if str(i.relative_to(self.folder)) in self.decisions)
        if decided == len(self.images):
            messagebox.showinfo("All done!", f"All {len(self.images)} photos sorted!\nResults saved to photo_sort_results.csv and .json")
            self.root.destroy()
            return

        # Advance to next undecided
        next_idx = self.index + 1
        while next_idx < len(self.images) and str(self.images[next_idx].relative_to(self.folder)) in self.decisions:
            next_idx += 1
        if next_idx >= len(self.images):
            next_idx = self.index  # stay at last photo
        self.index = next_idx
        self._show_current()

    def _go_back(self) -> None:
        if self.index > 0:
            self.index -= 1
            self._show_current()


def main() -> None:
    parser = argparse.ArgumentParser(description="Photo Sorter — categorize photos with keyboard shortcuts")
    parser.add_argument("folder", nargs="?", help="Folder containing photos to sort")
    parser.add_argument(
        "--categories",
        default=",".join(DEFAULT_CATEGORIES),
        help=f"Comma-separated category names (default: {','.join(DEFAULT_CATEGORIES)})",
    )
    parser.add_argument("--demo", action="store_true", help="Use bundled demo images")
    args = parser.parse_args()

    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    if not categories:
        categories = DEFAULT_CATEGORIES
    if len(categories) > 9:
        print("Error: maximum 9 categories supported (keyboard 1–9)")
        sys.exit(1)

    root = tk.Tk()

    if args.demo:
        demo_folder = Path(__file__).parent / "demo_images"
        if not demo_folder.exists() or not any(demo_folder.iterdir()):
            messagebox.showerror("Demo images missing", f"Demo images folder not found at:\n{demo_folder}")
            root.destroy()
            return
        folder = demo_folder
    elif args.folder:
        folder = Path(args.folder)
        if not folder.is_dir():
            print(f"Error: '{folder}' is not a directory")
            sys.exit(1)
    else:
        root.withdraw()
        folder_str = filedialog.askdirectory(title="Select photo folder")
        root.deiconify()
        if not folder_str:
            root.destroy()
            return
        folder = Path(folder_str)

    PhotoSorter(root, folder, categories)
    root.mainloop()


if __name__ == "__main__":
    main()
