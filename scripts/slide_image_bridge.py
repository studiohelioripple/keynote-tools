#!/usr/bin/env python3
"""
Keynote Slide Image Extractor, Inpainter, and Re-injector
Part of keynote-tools suite.
-----------------------------------------------------------
Automates extracting the backing image/PDF of the active Keynote slide,
performing text OCR / layer inpainting, and cleanly re-injecting the updated
graphic back into the Keynote presentation in-place.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run_osascript(script: str) -> str:
    res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"AppleScript error: {res.stderr.strip()}")
    return res.stdout.strip()


def get_slide_info(slide_num: int | None = None) -> dict:
    target_slide = f"slide {slide_num}" if slide_num else "current slide"
    script = f"""
    tell application "Keynote"
        if not (exists front document) then
            return "ERROR: No presentation is open in Keynote."
        end if
        tell front document
            set sw to width
            set sh to height
            set docName to name
            tell {target_slide}
                set sNum to slide number
                set imgCount to count of images
                set fn to ""
                if imgCount > 0 then
                    try
                        set fn to file name of image 1 as text
                    end try
                end if
                return (docName & "|" & sNum & "|" & sw & "|" & sh & "|" & imgCount & "|" & fn)
            end tell
        end tell
    end tell
    """
    raw = run_osascript(script)
    if raw.startswith("ERROR:"):
        print(raw, file=sys.stderr)
        sys.exit(1)

    parts = raw.split("|")
    return {
        "doc_name": parts[0],
        "slide_number": int(parts[1]),
        "canvas_width": float(parts[2]),
        "canvas_height": float(parts[3]),
        "image_count": int(parts[4]),
        "file_name": parts[5] if len(parts) > 5 else ""
    }


def replace_slide_image(image_path: str, slide_num: int | None = None) -> None:
    abs_path = os.path.abspath(image_path)
    target_slide = f"slide {slide_num}" if slide_num else "current slide"
    script = f"""
    tell application "Keynote"
        tell front document
            set sw to width
            set sh to height
            tell {target_slide}
                if (count of images) > 0 then
                    delete image 1
                end if
                set newImg to make new image with properties {{file:POSIX file "{abs_path}"}}
                set width of newImg to sw
                set height of newImg to sh
                set position of newImg to {{0, 0}}
            end tell
            save
        end tell
    end tell
    """
    run_osascript(script)


def main():
    parser = argparse.ArgumentParser(description="Extract, inspect, or re-inject Keynote slide images.")
    parser.add_argument("--info", action="store_true", help="Print information about Keynote slide")
    parser.add_argument("--slide", type=int, default=None, help="Target slide number (defaults to active slide)")
    parser.add_argument("--reinject", type=str, help="Path of updated image to re-inject into slide")
    args = parser.parse_args()

    if args.info:
        info = get_slide_info(args.slide)
        print(json.dumps(info, indent=2))
        return

    if args.reinject:
        target_desc = f"slide {args.slide}" if args.slide else "active slide"
        print(f"[*] Re-injecting image into {target_desc}: {args.reinject}")
        replace_slide_image(args.reinject, args.slide)
        print(f"[✓] Successfully replaced {target_desc} graphic and saved presentation.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
