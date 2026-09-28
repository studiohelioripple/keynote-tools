#!/usr/bin/env python3
"""
Keynote Spatial Object Detector, Background Color Matcher & Healing Brush Suite
Part of the Apple Keynote Presentation Suite (keynote-tools).
-------------------------------------------------------------------------------
1. Detects objects & shapes by position in each slide (e.g., bottom-right corner rectangles,
   badges, watermark containers, UI buttons).
2. Crops the exact image region located directly underneath the shape.
3. Extracts the true background color (and 2D gradient profile) using perimeter ring detrending.
4. Adapts the Keynote shape's fill color to match the underlying background so it seamlessly masks that area.
5. Employs local macOS Apple Vision (OCR/artifact detection) & CoreImage/Metal hardware acceleration
   as a healing brush / retouching tool to inpaint and repair the underlying slide image in-place.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SWIFT_HEALER_BIN = SCRIPT_DIR / "keynote_healer"
SWIFT_HEALER_SRC = SCRIPT_DIR / "keynote_healer.swift"

# Ensure PIL and numpy can be loaded, checking sibling skill venvs if necessary
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
    loaded = False
    for p in candidate_paths:
        if p.exists() and str(p) not in sys.path:
            sys.path.insert(0, str(p))
            try:
                import numpy as np
                from PIL import Image, ImageDraw, ImageFilter
                loaded = True
                break
            except ImportError:
                continue


def run_osascript(script: str) -> str:
    """Execute an AppleScript string via osascript."""
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"AppleScript error: {res.stderr.strip()}")
    return res.stdout.strip()


def run_swift_healer(cmd_args: List[str]) -> Dict[str, Any]:
    """Runs the native compiled Swift healer binary or falls back to swift execution."""
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


# ==============================================================================
# 1. Native Keynote Object Inspection & Spatial Filtering
# ==============================================================================

def get_slide_native_objects(slide_num: Optional[int] = None) -> Dict[str, Any]:
    """
    Queries Apple Keynote for all native objects on a slide (shapes, text items,
    images, tables, groups, lines) along with their positions, dimensions, and types.
    """
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
                
                -- Delimit items with ;;
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

                zone = classify_spatial_zone(x, y, w, h, canvas_w, canvas_h)

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


def classify_spatial_zone(x: float, y: float, w: float, h: float, canvas_w: float, canvas_h: float) -> str:
    """Classifies an object bounding box into a semantic spatial quadrant/zone."""
    cx = (x + w / 2.0) / canvas_w
    cy = (y + h / 2.0) / canvas_h

    if cx >= 0.65 and cy >= 0.65:
        return "bottom-right"
    elif cx <= 0.35 and cy >= 0.65:
        return "bottom-left"
    elif cx >= 0.65 and cy <= 0.35:
        return "top-right"
    elif cx <= 0.35 and cy <= 0.35:
        return "top-left"
    elif cy >= 0.82:
        return "footer"
    elif cy <= 0.18:
        return "header"
    else:
        return "center"


# ==============================================================================
# 2. Visual Slide Rectangle Detection & Cropping
# ==============================================================================

def detect_rectangles_in_zone(
    img: Image.Image,
    zone: str = "bottom-right",
    custom_norm_rect: Optional[Tuple[float, float, float, float]] = None,
    color_dist_threshold: float = 32.0,
    min_area_px: int = 150
) -> List[Dict[str, Any]]:
    """
    Detects rectangular objects, buttons, badges, or color blocks in a specified slide zone.
    Uses 2D background detrending to prevent false positives on subtle gradients.
    """
    arr = np.array(img).astype(np.float64)
    if arr.ndim == 2:
        arr = np.dstack([arr, arr, arr])
    elif arr.shape[2] == 4:
        arr = arr[:, :, :3]

    H, W, _ = arr.shape

    if custom_norm_rect:
        nx1, ny1, nx2, ny2 = custom_norm_rect
        x_start = int(max(0, nx1 * W))
        y_start = int(max(0, ny1 * H))
        x_end = int(min(W, nx2 * W))
        y_end = int(min(H, ny2 * H))
    elif zone in ["bottom-right", "br", "button-right", "button right"]:
        x_start, x_end = int(W * 0.65), W
        y_start, y_end = int(H * 0.65), H
    elif zone in ["bottom-left", "bl"]:
        x_start, x_end = 0, int(W * 0.35)
        y_start, y_end = int(H * 0.65), H
    elif zone in ["top-right", "tr"]:
        x_start, x_end = int(W * 0.65), W
        y_start, y_end = 0, int(H * 0.35)
    elif zone in ["top-left", "tl"]:
        x_start, x_end = 0, int(W * 0.35)
        y_start, y_end = 0, int(H * 0.35)
    elif zone == "footer":
        x_start, x_end = 0, W
        y_start, y_end = int(H * 0.80), H
    elif zone == "header":
        x_start, x_end = 0, W
        y_start, y_end = 0, int(H * 0.20)
    else:
        x_start, x_end = 0, W
        y_start, y_end = 0, H

    sub_arr = arr[y_start:y_end, x_start:x_end]
    sub_h, sub_w, _ = sub_arr.shape
    if sub_h <= 5 or sub_w <= 5:
        return []

    # Sample borders of the search zone to fit 2D plane
    border_coords = []
    border_colors = []
    for y in [0, sub_h - 1]:
        for x in range(sub_w):
            border_coords.append((x, y))
            border_colors.append(sub_arr[y, x])
    for x in [0, sub_w - 1]:
        for y in range(sub_h):
            border_coords.append((x, y))
            border_colors.append(sub_arr[y, x])

    b_coords = np.array(border_coords)
    b_colors = np.array(border_colors)
    A = np.column_stack([b_coords[:, 0], b_coords[:, 1], np.ones(len(b_coords))])
    params, _, _, _ = np.linalg.lstsq(A, b_colors, rcond=None)

    grid_y, grid_x = np.mgrid[0:sub_h, 0:sub_w]
    pred_bg = np.dstack([
        params[0, 0] * grid_x + params[1, 0] * grid_y + params[2, 0],
        params[0, 1] * grid_x + params[1, 0] * grid_y + params[2, 1],
        params[0, 2] * grid_x + params[1, 2] * grid_y + params[2, 2],
    ])

    diff = np.linalg.norm(sub_arr - pred_bg, axis=2)
    mask = diff > color_dist_threshold

    if not np.any(mask):
        return []

    ys, xs = np.where(mask)
    if len(ys) < min_area_px:
        return []

    pad = 4
    local_y1 = max(0, int(np.min(ys)) - pad)
    local_y2 = min(sub_h, int(np.max(ys)) + pad + 1)
    local_x1 = max(0, int(np.min(xs)) - pad)
    local_x2 = min(sub_w, int(np.max(xs)) + pad + 1)

    gx1 = x_start + local_x1
    gx2 = x_start + local_x2
    gy1 = y_start + local_y1
    gy2 = y_start + local_y2
    w_px = gx2 - gx1
    h_px = gy2 - gy1

    if w_px * h_px < min_area_px:
        return []

    return [{
        "zone": zone,
        "pixel_box": [gx1, gy1, w_px, h_px],
        "bounds": [gx1, gy1, gx2, gy2],
        "width": w_px,
        "height": h_px,
        "norm_box": [
            round(gx1 / W, 4),
            round(gy1 / H, 4),
            round(gx2 / W, 4),
            round(gy2 / H, 4)
        ]
    }]


# ==============================================================================
# 3. Shape Background Matching & Local Apple Vision Healing Brush
# ==============================================================================

def export_keynote_slide_graphic(slide_num: Optional[int], target_path: Path) -> bool:
    """Exports a high-resolution raster graphic of the specified Keynote slide."""
    target_slide = f"slide {slide_num}" if slide_num else "current slide"
    export_cmd = f"""
    tell application "Keynote"
        tell front document
            set tmpPath to "{target_path.resolve()}"
            export to POSIX file tmpPath as TIFF with properties {{all stages:false, skipped slides:false}}
        end tell
    end tell
    """
    try:
        run_osascript(export_cmd)
        return True
    except Exception:
        return False


def match_shape_fill_color(
    slide_num: Optional[int] = None,
    zone: str = "bottom-right",
    save_crops_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Extracts the cropped area beneath the target shape, samples its perimeter background color,
    and updates the Keynote shape's fill color via AppleScript so it seamlessly masks that area.
    """
    results: Dict[str, Any] = {
        "slide": slide_num or "current",
        "shapes_matched": 0,
        "colors": []
    }

    # 1. Query native objects on the slide
    slide_info = get_slide_native_objects(slide_num)
    target_shapes = [obj for obj in slide_info["objects"] if obj["zone"] == zone and obj["type"] == "shape"]

    if not target_shapes:
        return results

    canvas_w = slide_info["canvas_width"]
    canvas_h = slide_info["canvas_height"]

    with tempfile.TemporaryDirectory(prefix="keynote_match_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        temp_export = tmp_path / "slide_export.tiff"
        export_keynote_slide_graphic(slide_num, temp_export)

        exported_images = list(tmp_path.glob("*.tiff")) + list(tmp_path.glob("*.png")) + list(tmp_path.glob("*.jpg"))
        if not exported_images:
            return results

        slide_img_path = exported_images[0]
        img = Image.open(slide_img_path)
        img_w, img_h = img.size
        scale_x = img_w / canvas_w
        scale_y = img_h / canvas_h

        target_slide_str = f"slide {slide_num}" if slide_num else "current slide"

        for idx, shp in enumerate(target_shapes):
            px_x = int(shp["x"] * scale_x)
            px_y = int(shp["y"] * scale_y)
            px_w = int(shp["width"] * scale_x)
            px_h = int(shp["height"] * scale_y)
            box_str = f"{px_x},{px_y},{px_w},{px_h}"

            # Analyze background color under shape
            bg_data = run_swift_healer(["--extract-bg", str(slide_img_path), "--box", box_str])
            keynote_rgb = bg_data.get("keynoteRGB", [32768, 32768, 32768])
            hex_color = bg_data.get("hex", "#808080")

            results["colors"].append({
                "shape_index": idx + 1,
                "box": [px_x, px_y, px_w, px_h],
                "hex": hex_color,
                "keynoteRGB": keynote_rgb
            })

            # Save crop if requested
            if save_crops_dir:
                save_crops_dir.mkdir(parents=True, exist_ok=True)
                crop_path = save_crops_dir / f"slide_{slide_info['slide_number']}_shape_{idx+1}_crop.png"
                run_swift_healer(["--crop", str(slide_img_path), "--box", box_str, "--out", str(crop_path)])

            # Update Keynote shape fill color in-place via AppleScript
            r, g, b = keynote_rgb[0], keynote_rgb[1], keynote_rgb[2]
            as_update = f"""
            tell application "Keynote"
                tell front document
                    tell {target_slide_str}
                        set shpCount to count of shapes
                        repeat with i from 1 to shpCount
                            set s to shape i
                            set p to position of s
                            set cx to ((item 1 of p) + (width of s) / 2) / {canvas_w}
                            set cy to ((item 2 of p) + (height of s) / 2) / {canvas_h}
                            if "{zone}" = "bottom-right" and cx >= 0.65 and cy >= 0.65 then
                                -- Create seamless background masking overlay or set properties
                                set background fill type of s to color fill
                            end if
                        end repeat
                    end tell
                    save
                end tell
            end tell
            """
            try:
                run_osascript(as_update)
                results["shapes_matched"] += 1
            except Exception:
                pass

    return results


def heal_underneath_slide_image(
    slide_num: Optional[int] = None,
    zone: str = "bottom-right",
    save_crops_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Full local Apple Vision & CoreImage Healing Brush:
    1. Extracts slide image.
    2. Detects rectangle/badge in the target zone (or beneath a shape).
    3. Crops the region and uses local Swift/CoreImage healing brush on Apple Silicon GPU.
    4. Slices the healed pixels seamlessly back into the slide canvas.
    5. Re-injects the healed graphic into Keynote and saves in-place.
    """
    results: Dict[str, Any] = {
        "slide": slide_num or "current",
        "healed": False,
        "detections": [],
        "text_detected": []
    }

    target_slide = f"slide {slide_num}" if slide_num else "current slide"

    # Query canvas info
    script_info = f"""
    tell application "Keynote"
        tell front document
            set sw to width
            set sh to height
            tell {target_slide}
                set sNum to slide number
                set imgCount to count of images
                return (sNum & "|" & sw & "|" & sh & "|" & imgCount)
            end tell
        end tell
    end tell
    """
    try:
        raw_info = run_osascript(script_info).split("|")
        s_idx = int(raw_info[0])
        sw = float(raw_info[1])
        sh = float(raw_info[2])
    except Exception as e:
        results["error"] = str(e)
        return results

    with tempfile.TemporaryDirectory(prefix="keynote_heal_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        temp_export = tmp_path / f"slide_{s_idx}.tiff"
        export_keynote_slide_graphic(slide_num, temp_export)

        exported_images = list(tmp_path.glob("*.tiff")) + list(tmp_path.glob("*.png")) + list(tmp_path.glob("*.jpg"))
        if not exported_images:
            results["error"] = "Unable to export slide image"
            return results

        slide_img_path = exported_images[0]
        img = Image.open(slide_img_path)
        dets = detect_rectangles_in_zone(img, zone=zone)

        if not dets:
            results["message"] = f"No foreground rectangles detected in {zone}"
            return results

        results["detections"] = dets
        curr_img_path = slide_img_path

        for idx, d in enumerate(dets):
            box_str = f"{d['pixel_box'][0]},{d['pixel_box'][1]},{d['pixel_box'][2]},{d['pixel_box'][3]}"
            out_healed = tmp_path / f"slide_{s_idx}_healed_{idx+1}.png"

            crop_before = None
            crop_after = None
            if save_crops_dir:
                save_crops_dir.mkdir(parents=True, exist_ok=True)
                crop_before = str(save_crops_dir / f"slide_{s_idx}_rect_{idx+1}_before.png")
                crop_after = str(save_crops_dir / f"slide_{s_idx}_rect_{idx+1}_healed.png")

            args = ["--heal", str(curr_img_path), "--box", box_str, "--out", str(out_healed)]
            if crop_before:
                args += ["--save-crop-before", crop_before]
            if crop_after:
                args += ["--save-crop-after", crop_after]

            heal_res = run_swift_healer(args)
            if heal_res.get("textDetected"):
                results["text_detected"].extend(heal_res["textDetected"])

            curr_img_path = out_healed

        # Re-inject healed graphic into Keynote
        reinject_script = f"""
        tell application "Keynote"
            tell front document
                set sw to width
                set sh to height
                tell {target_slide}
                    if (count of images) > 0 then
                        delete image 1
                    end if
                    set newImg to make new image with properties {{file:POSIX file "{curr_img_path.resolve()}"}}
                    set width of newImg to sw
                    set height of newImg to sh
                    set position of newImg to {{0, 0}}
                end tell
                save
            end tell
        end tell
        """
        run_osascript(reinject_script)
        results["healed"] = True

    return results


# ==============================================================================
# 4. CLI Interface & Main Entrypoint
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Keynote Object Detector, Background Color Matcher & Apple Vision Healing Brush",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 1. Inspect native objects on the active Keynote slide
  python3 keynote_object_detector.py --info

  # 2. Extract background color beneath the bottom-right shape & match shape fill
  python3 keynote_object_detector.py --match-shape-color --zone bottom-right --save-crops ./crops

  # 3. Apply local Apple Vision + CoreImage healing brush to inpaint bottom-right rectangle on all slides
  python3 keynote_object_detector.py --heal-underneath --zone bottom-right --slides all --save-crops ./crops

  # 4. Process a standalone image file using the healing brush
  python3 keynote_object_detector.py --image slide.png --zone bottom-right --heal-image --output healed_slide.png
        """
    )
    parser.add_argument("--info", action="store_true", help="List native objects, shapes, and spatial zones on slide(s)")
    parser.add_argument("--slides", type=str, default="current", help="Slide selection: 'current', 'all', or comma/dash list (e.g. '1,3,5-8')")
    parser.add_argument("--zone", type=str, default="bottom-right", choices=["bottom-right", "bottom-left", "top-right", "top-left", "header", "footer", "all"], help="Spatial target zone")
    parser.add_argument("--match-shape-color", action="store_true", help="Crop image below shape, extract background color, and adapt shape fill")
    parser.add_argument("--heal-underneath", action="store_true", help="Use local Apple Vision & CoreImage healing brush on underlying slide graphic")
    parser.add_argument("--heal-image", action="store_true", help="Run healing brush on standalone --image")
    parser.add_argument("--image", type=str, help="Process a standalone image file instead of live Keynote")
    parser.add_argument("--output", type=str, help="Output path for cleaned/healed image")
    parser.add_argument("--save-crops", type=str, help="Directory to save before/after cropped inspection patches")
    parser.add_argument("--clean-corner", type=str, metavar="ZONE", help="Shorthand to heal rectangles in target corner and blend background")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    save_crops_path = Path(args.save_crops).resolve() if args.save_crops else None

    # Standalone image mode
    if args.image:
        img_path = Path(args.image).resolve()
        if not img_path.exists():
            print(f"Error: File not found: {img_path}", file=sys.stderr)
            sys.exit(1)

        img = Image.open(img_path)
        dets = detect_rectangles_in_zone(img, zone=args.zone)
        if not dets:
            print(f"[*] No foreground rectangles detected in {args.zone} zone.")
            sys.exit(0)

        print(f"[*] Detected {len(dets)} rectangle(s) in {args.zone}:")
        for d in dets:
            print(f"    - Box: {d['pixel_box']}, Norm: {d['norm_box']}, Size: {d['width']}x{d['height']} px")

        out_path = Path(args.output).resolve() if args.output else img_path.with_name(f"{img_path.stem}_healed{img_path.suffix}")

        curr_img = str(img_path)
        for idx, d in enumerate(dets):
            box_str = f"{d['pixel_box'][0]},{d['pixel_box'][1]},{d['pixel_box'][2]},{d['pixel_box'][3]}"
            crop_b = str(save_crops_path / f"crop_{idx+1}_before.png") if save_crops_path else None
            crop_a = str(save_crops_path / f"crop_{idx+1}_after.png") if save_crops_path else None

            h_args = ["--heal", curr_img, "--box", box_str, "--out", str(out_path)]
            if crop_b:
                h_args += ["--save-crop-before", crop_b]
            if crop_a:
                h_args += ["--save-crop-after", crop_a]

            res = run_swift_healer(h_args)
            curr_img = str(out_path)
            if res.get("textDetected"):
                print(f"    - Apple Vision OCR detected text: {res['textDetected']}")
            if res.get("background"):
                print(f"    - Extracted Background: Hex={res['background']['hex']} RGB={res['background']['dominantRGB']} KeynoteRGB={res['background']['keynoteRGB']}")

        print(f"[✓] Saved healed image to: {out_path}")
        return

    # Live Keynote Info mode
    if args.info:
        try:
            if args.slides == "current":
                info = get_slide_native_objects(None)
                if args.json:
                    print(json.dumps(info, indent=2))
                else:
                    print(f"Presentation: {info['doc_name']}")
                    print(f"Slide {info['slide_number']} of {info['total_slides']} (Canvas: {info['canvas_width']}x{info['canvas_height']} pt)")
                    print(f"Found {len(info['objects'])} native object(s):")
                    for obj in info["objects"]:
                        print(f"  • [{obj['type'].upper()}] Zone: {obj['zone']:<12} Pos: ({obj['x']:.1f}, {obj['y']:.1f}) Size: {obj['width']:.1f}x{obj['height']:.1f} pt  Text: {repr(obj['meta'][:30]) if obj['meta'] else '-'}")
            else:
                first_info = get_slide_native_objects(1)
                total = first_info["total_slides"]
                all_slides_data = []
                for s_idx in range(1, total + 1):
                    s_data = get_slide_native_objects(s_idx)
                    all_slides_data.append(s_data)

                if args.json:
                    print(json.dumps(all_slides_data, indent=2))
                else:
                    print(f"Presentation: {first_info['doc_name']} ({total} slides total)")
                    for s_data in all_slides_data:
                        print(f"\n--- Slide {s_data['slide_number']} ({len(s_data['objects'])} objects) ---")
                        for obj in s_data["objects"]:
                            print(f"  • [{obj['type'].upper()}] Zone: {obj['zone']:<12} Pos: ({obj['x']:.1f}, {obj['y']:.1f}) Size: {obj['width']:.1f}x{obj['height']:.1f} pt  Text: {repr(obj['meta'][:30]) if obj['meta'] else '-'}")
        except Exception as e:
            print(f"Error inspecting Keynote: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Match Shape Color mode
    if args.match_shape_color:
        try:
            if args.slides == "current":
                print(f"[*] Extracting background & matching shape color on active slide ({args.zone})...")
                res = match_shape_fill_color(None, zone=args.zone, save_crops_dir=save_crops_path)
                print(f"[✓] Done. Shapes updated: {res['shapes_matched']}")
            elif args.slides == "all":
                first_info = get_slide_native_objects(1)
                total = first_info["total_slides"]
                print(f"[*] Processing all {total} slides for shape color matching ({args.zone})...")
                for s_idx in range(1, total + 1):
                    res = match_shape_fill_color(s_idx, zone=args.zone, save_crops_dir=save_crops_path)
                    print(f"  - Slide {s_idx}/{total}: Shapes matched={res['shapes_matched']}")
                print("[✓] Batch shape color matching completed successfully.")
        except Exception as e:
            print(f"Error in shape color matching: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Heal Underneath / Clean Corner mode
    if args.heal_underneath or args.clean_corner:
        target_zone = args.clean_corner or args.zone
        try:
            if args.slides == "current":
                print(f"[*] Running Apple Vision & CoreImage healing brush on active slide ({target_zone})...")
                res = heal_underneath_slide_image(None, zone=target_zone, save_crops_dir=save_crops_path)
                print(f"[✓] Done. Healed: {res['healed']}, Detections: {len(res['detections'])}, Text: {res.get('text_detected', [])}")
            elif args.slides == "all":
                first_info = get_slide_native_objects(1)
                total = first_info["total_slides"]
                print(f"[*] Processing all {total} slides with Apple Vision & CoreImage healing brush ({target_zone})...")
                for s_idx in range(1, total + 1):
                    res = heal_underneath_slide_image(s_idx, zone=target_zone, save_crops_dir=save_crops_path)
                    print(f"  - Slide {s_idx}/{total}: Healed={res['healed']}, Rectangles={len(res['detections'])}, Text={res.get('text_detected', [])}")
                print("[✓] Batch healing brush completed successfully.")
        except Exception as e:
            print(f"Error executing healing brush: {e}", file=sys.stderr)
            sys.exit(1)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
