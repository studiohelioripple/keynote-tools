#!/usr/bin/env python3
"""
Keynote Spatial Object Detector, Background Color Matcher & Healing Brush Suite
Part of the Apple Keynote Presentation Suite (keynote-tools).
-------------------------------------------------------------------------------
1. Detects objects & shapes by position in each slide (e.g., bottom-right corner rectangles,
   badges, watermark containers, UI buttons).
2. Crops the exact image region located directly underneath the shape.
3. Extracts the true background color (and 2D gradient profile) using perimeter ring detrending.
4. Supports 3 comprehensive masking strategies:
   - `native-shape`: Inpaints background and creates clean native Keynote vector shape objects (`class: shape`).
   - `clean-image`: Synthesizes 100% pure resampled background gradient image patches (zero original texture).
   - `direct-inpaint`: Retouches the underlying slide graphic directly with no overlay objects.
5. Employs local macOS Apple Vision (OCR/artifact detection) & CoreImage/Metal hardware acceleration.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SWIFT_HEALER_BIN = SCRIPT_DIR / "keynote_healer"
SWIFT_HEALER_SRC = SCRIPT_DIR / "keynote_healer.swift"

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    candidate_paths = [
        Path.home() / ".gemini/config/skills/image-explorer-pro/venv/lib/python3.14/site-packages",
        Path.home() / ".gemini/config/skills/image-explorer-pro/venv/lib/python3.13/site-packages",
        Path.home() / ".gemini/config/skills/image-explorer-pro/venv/lib/python3.12/site-packages",
        Path.home() / ".gemini/config/skills/apple-watermark-cleaner/venv/lib/python3.14/site-packages",
    ]
    for p in candidate_paths:
        if p.exists() and str(p) not in sys.path:
            sys.path.insert(0, str(p))
            try:
                import numpy as np
                from PIL import Image, ImageDraw, ImageFilter
                break
            except ImportError:
                continue


def run_osascript(script: str) -> str:
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"AppleScript error: {res.stderr.strip()}")
    return res.stdout.strip()


def run_swift_healer(cmd_args: List[str]) -> Dict[str, Any]:
    if SWIFT_HEALER_BIN.exists() and os.access(SWIFT_HEALER_BIN, os.X_OK):
        cmd = [str(SWIFT_HEALER_BIN)] + cmd_args
    elif SWIFT_HEALER_SRC.exists():
        cmd = ["swift", str(SWIFT_HEALER_SRC)] + cmd_args
    else:
        raise FileNotFoundError("keynote_healer tool not found.")

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Healer tool error: {res.stderr.strip()}")

    out = res.stdout.strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"raw_output": out}


def get_slide_native_objects(slide_num: Optional[int] = None) -> Dict[str, Any]:
    target_slide = f"slide {slide_num}" if slide_num else "current slide"
    applescript = f"""
    tell application "Keynote"
        if not (exists front document) then
            return "ERROR: No presentation is open in Keynote."
        end if
        tell front document
            set docName to name
            set sw to width
            set sh to height
            set totalSlides to count of slides
            tell {target_slide}
                set sNum to slide number
                set objList to {{}}
                
                -- Shapes
                repeat with shp in shapes
                    try
                        set p to position of shp
                        set w to width of shp
                        set h to height of shp
                        set op to opacity of shp
                        set rot to rotation of shp
                        set txt to ""
                        try
                            set txt to object text of shp as text
                        end try
                        set end of objList to ("shape|" & (item 1 of p) & "|" & (item 2 of p) & "|" & w & "|" & h & "|" & op & "|" & rot & "|" & txt)
                    end try
                end repeat
                
                -- Text items
                repeat with ti in text items
                    try
                        set p to position of ti
                        set w to width of ti
                        set h to height of ti
                        set op to opacity of ti
                        set rot to rotation of ti
                        set txt to ""
                        try
                            set txt to object text of ti as text
                        end try
                        set end of objList to ("text item|" & (item 1 of p) & "|" & (item 2 of p) & "|" & w & "|" & h & "|" & op & "|" & rot & "|" & txt)
                    end try
                end repeat
                
                -- Images
                repeat with img in images
                    try
                        set p to position of img
                        set w to width of img
                        set h to height of img
                        set op to opacity of img
                        set rot to rotation of img
                        set fn to ""
                        try
                            set fn to file name of img as text
                        end try
                        set end of objList to ("image|" & (item 1 of p) & "|" & (item 2 of p) & "|" & w & "|" & h & "|" & op & "|" & rot & "|" & fn)
                    end try
                end repeat
                
                set AppleScript's text item delimiters to ";;"
                set serializedList to objList as text
                set AppleScript's text item delimiters to ""
                
                return (docName & ":::" & sNum & ":::" & totalSlides & ":::" & sw & ":::" & sh & ":::" & serializedList)
            end tell
        end tell
    end tell
    """
    raw = run_osascript(applescript)
    if raw.startswith("ERROR:"):
        raise RuntimeError(raw)

    parts = raw.split(":::")
    doc_name = parts[0]
    s_num = int(parts[1])
    total_slides = int(parts[2])
    canvas_w = float(parts[3])
    canvas_h = float(parts[4])
    raw_objs = parts[5] if len(parts) > 5 and parts[5] else ""

    objects = []
    if raw_objs:
        for item_str in raw_objs.split(";;"):
            if not item_str:
                continue
            fields = item_str.split("|")
            if len(fields) >= 7:
                obj_type = fields[0]
                x = float(fields[1])
                y = float(fields[2])
                w = float(fields[3])
                h = float(fields[4])
                opacity = float(fields[5])
                rotation = float(fields[6])
                meta = fields[7] if len(fields) > 7 else ""

                cx = (x + w / 2.0) / canvas_w
                cy = (y + h / 2.0) / canvas_h
                if cx >= 0.65 and cy >= 0.65:
                    zone = "bottom-right"
                elif cx <= 0.35 and cy >= 0.65:
                    zone = "bottom-left"
                elif cx >= 0.65 and cy <= 0.35:
                    zone = "top-right"
                elif cx <= 0.35 and cy <= 0.35:
                    zone = "top-left"
                elif cy >= 0.82:
                    zone = "footer"
                elif cy <= 0.18:
                    zone = "header"
                else:
                    zone = "center"

                objects.append({
                    "type": obj_type,
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "opacity": opacity,
                    "rotation": rotation,
                    "meta": meta,
                    "zone": zone,
                    "norm_bounds": [
                        round(x / canvas_w, 4),
                        round(y / canvas_h, 4),
                        round((x + w) / canvas_w, 4),
                        round((y + h) / canvas_h, 4),
                    ]
                })

    return {
        "doc_name": doc_name,
        "slide_number": s_num,
        "total_slides": total_slides,
        "canvas_width": canvas_w,
        "canvas_height": canvas_h,
        "objects": objects
    }


def process_keynote_masking(
    strategy: str = "native-shape",
    zone: str = "bottom-right",
    slides_range: str = "all",
    save_crops_dir: Optional[Path] = None
) -> None:
    """Applies masking according to the specified strategy across slides."""
    info1 = get_slide_native_objects(1)
    total_slides = info1["total_slides"]
    canvas_w = info1["canvas_width"]
    canvas_h = info1["canvas_height"]
    doc_name = info1["doc_name"]

    target_slide_indices = []
    if slides_range == "all":
        target_slide_indices = list(range(1, total_slides + 1))
    elif slides_range == "current":
        curr = get_slide_native_objects(None)
        target_slide_indices = [curr["slide_number"]]
    else:
        for chunk in slides_range.split(","):
            chunk = chunk.strip()
            if "-" in chunk:
                s, e = chunk.split("-")
                target_slide_indices.extend(range(int(s), int(e) + 1))
            elif chunk.isdigit():
                target_slide_indices.append(int(chunk))

    print(f"[*] Processing '{doc_name}' ({len(target_slide_indices)} slides) with strategy: {strategy.upper()}...")

    with tempfile.TemporaryDirectory(prefix="keynote_mask_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        export_dir = tmp_path / "slides_export"
        export_dir.mkdir(parents=True, exist_ok=True)

        as_export = f"""
        tell application "Keynote"
            tell front document
                export to POSIX file "{export_dir.resolve()}" as slide images with properties {{image format:PNG}}
            end tell
        end tell
        """
        run_osascript(as_export)
        exported_files = sorted(list(export_dir.glob("*.png")))

        for s_idx in target_slide_indices:
            slide_img = str(exported_files[s_idx - 1])

            # Locate bottom-right target box
            s_data = get_slide_native_objects(s_idx)
            target_box = None
            for obj in s_data["objects"]:
                if obj["zone"] == zone:
                    target_box = [int(obj["x"]), int(obj["y"]), int(obj["width"]), int(obj["height"])]
                    break
            if not target_box:
                target_box = [int(canvas_w * 0.90), int(canvas_h * 0.95), int(canvas_w * 0.09), int(canvas_h * 0.04)]

            bx, by, bw, bh = target_box
            box_str = f"{bx},{by},{bw},{bh}"

            healed_img_out = tmp_path / f"slide_{s_idx:02d}_healed.png"
            pure_patch_out = tmp_path / f"slide_{s_idx:02d}_pure_patch.png"

            # 1. Run GPU healing on slide image
            h_res = run_swift_healer([
                "--heal", slide_img,
                "--box", box_str,
                "--out", str(healed_img_out),
                "--save-crop-after", str(pure_patch_out)
            ])
            bg_hex = h_res.get("background", {}).get("hex", "#FFFFFF")

            if save_crops_dir:
                save_crops_dir.mkdir(parents=True, exist_ok=True)
                run_swift_healer(["--crop", slide_img, "--box", box_str, "--out", str(save_crops_dir / f"slide_{s_idx:02d}_before.png")])
                run_swift_healer(["--pure-patch", slide_img, "--box", box_str, "--out", str(save_crops_dir / f"slide_{s_idx:02d}_pure_patch.png")])

            # 2. Apply chosen strategy
            if strategy in ["native-shape", "shape", "vector"]:
                as_script = f"""
                tell application "Keynote"
                    tell front document
                        tell slide {s_idx}
                            -- Clean slide background
                            if (count of images) > 0 then
                                delete image 1
                            end if
                            set newBg to make new image with properties {{file:POSIX file "{healed_img_out.resolve()}"}}
                            set width of newBg to {canvas_w}
                            set height of newBg to {canvas_h}
                            set position of newBg to {{0, 0}}
                            
                            -- Remove extra images
                            set ic to count of images
                            repeat with i from ic to 2 by -1
                                delete image i
                            end repeat
                            
                            -- Remove previous shapes in zone
                            set sc to count of shapes
                            repeat with i from sc to 1 by -1
                                set s to shape i
                                set p to position of s
                                set px to item 1 of p
                                set py to item 2 of p
                                if px >= 1000 and py >= 600 then
                                    delete s
                                end if
                            end repeat
                            
                            -- Insert clean native vector shape
                            set nativeShp to make new shape with properties {{position:{{{bx}, {by}}}, width:{bw}, height:{bh}}}
                        end tell
                    end tell
                end tell
                """
            elif strategy in ["clean-image", "image-patch", "patch"]:
                as_script = f"""
                tell application "Keynote"
                    tell front document
                        tell slide {s_idx}
                            -- Remove previous shapes in zone
                            set sc to count of shapes
                            repeat with i from sc to 1 by -1
                                set s to shape i
                                set p to position of s
                                set px to item 1 of p
                                set py to item 2 of p
                                if px >= 1000 and py >= 600 then
                                    delete s
                                end if
                            end repeat
                            
                            -- Remove previous mask images
                            set ic to count of images
                            repeat with i from ic to 2 by -1
                                delete image i
                            end repeat
                            
                            -- Insert 100% pure resampled background patch
                            set maskObj to make new image with properties {{file:POSIX file "{pure_patch_out.resolve()}"}}
                            set width of maskObj to {bw}
                            set height of maskObj to {bh}
                            set position of maskObj to {{{bx}, {by}}}
                        end tell
                    end tell
                end tell
                """
            else:  # direct-inpaint
                as_script = f"""
                tell application "Keynote"
                    tell front document
                        tell slide {s_idx}
                            if (count of images) > 0 then
                                delete image 1
                            end if
                            set newBg to make new image with properties {{file:POSIX file "{healed_img_out.resolve()}"}}
                            set width of newBg to {canvas_w}
                            set height of newBg to {canvas_h}
                            set position of newBg to {{0, 0}}
                            
                            set sc to count of shapes
                            repeat with i from sc to 1 by -1
                                set s to shape i
                                set p to position of s
                                set px to item 1 of p
                                set py to item 2 of p
                                if px >= 1000 and py >= 600 then
                                    delete s
                                end if
                            end repeat
                        end tell
                    end tell
                end tell
                """

            run_osascript(as_script)
            print(f"  [✓] Slide {s_idx:02d}: Applied {strategy.upper()} ({bw}x{bh} pt @ {bx},{by}) | Background={bg_hex}")

        # Save presentation
        run_osascript('tell application "Keynote" to tell front document to save')
        print(f"\n[✓] Successfully processed and saved '{doc_name}' in Keynote!")


def main():
    parser = argparse.ArgumentParser(
        description="Keynote Object Detector, Background Color Matcher & Apple Vision Healing Brush Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 1. Inspect native objects on all slides
  python3 keynote_object_detector.py --info --slides all

  # 2. Apply NativeVectorShapes strategy across all slides
  python3 keynote_object_detector.py --strategy native-shape --zone bottom-right --slides all

  # 3. Apply CleanImagePatch strategy across all slides
  python3 keynote_object_detector.py --strategy clean-image --zone bottom-right --slides all

  # 4. Apply DirectInpaint strategy (heal underlying slide graphic with zero overlay)
  python3 keynote_object_detector.py --strategy direct-inpaint --zone bottom-right --slides all
        """
    )
    parser.add_argument("--info", action="store_true", help="List native objects and spatial zones on slide(s)")
    parser.add_argument("--slides", type=str, default="all", help="Slide selection: 'all', 'current', or '1,3,5-8'")
    parser.add_argument("--zone", type=str, default="bottom-right", choices=["bottom-right", "bottom-left", "top-right", "top-left", "header", "footer", "all"], help="Spatial target zone")
    parser.add_argument("--strategy", type=str, default="native-shape", choices=["native-shape", "clean-image", "direct-inpaint"], help="Masking strategy to apply")
    parser.add_argument("--save-crops", type=str, help="Directory to save before/after cropped inspection patches")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    save_crops_path = Path(args.save_crops).resolve() if args.save_crops else None

    if args.info:
        if args.slides == "current":
            info = get_slide_native_objects(None)
            if args.json:
                print(json.dumps(info, indent=2))
            else:
                print(f"Presentation: {info['doc_name']}")
                print(f"Slide {info['slide_number']} of {info['total_slides']} (Canvas: {info['canvas_width']}x{info['canvas_height']} pt)")
                for obj in info["objects"]:
                    print(f"  • [{obj['type'].upper()}] Zone: {obj['zone']:<12} Pos: ({obj['x']:.1f}, {obj['y']:.1f}) Size: {obj['width']:.1f}x{obj['height']:.1f} pt")
        else:
            first = get_slide_native_objects(1)
            total = first["total_slides"]
            all_data = [get_slide_native_objects(s) for s in range(1, total + 1)]
            if args.json:
                print(json.dumps(all_data, indent=2))
            else:
                print(f"Presentation: {first['doc_name']} ({total} slides total)")
                for s in all_data:
                    print(f"\n--- Slide {s['slide_number']} ({len(s['objects'])} objects) ---")
                    for obj in s["objects"]:
                        print(f"  • [{obj['type'].upper()}] Zone: {obj['zone']:<12} Pos: ({obj['x']:.1f}, {obj['y']:.1f}) Size: {obj['width']:.1f}x{obj['height']:.1f} pt")
        return

    process_keynote_masking(
        strategy=args.strategy,
        zone=args.zone,
        slides_range=args.slides,
        save_crops_dir=save_crops_path
    )


if __name__ == "__main__":
    main()
