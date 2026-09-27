#!/usr/bin/env python3
"""
Keynote Conversion & Automation Suite (pdf_to_keynote.py)
--------------------------------------------------------
Converts multi-page PDF documents or slide decks into native Apple Keynote (.key) presentations.
Preserves 100% vector graphics fidelity, exact dimensions, and slide layouts.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def is_keynote_available() -> bool:
    """Checks if Apple Keynote is installed on macOS."""
    if sys.platform != "darwin":
        return False
    return os.path.exists("/Applications/Keynote.app") or os.path.exists("/System/Applications/Keynote.app")


def extract_pdf_pages_swift(pdf_path: Path, output_dir: Path) -> tuple[int, float, float]:
    """
    Extracts individual PDF pages into single-page PDFs using PDFKit via Swift.
    Returns (page_count, width, height) in points.
    """
    swift_script = f"""
import Foundation
import PDFKit

let srcUrl = URL(fileURLWithPath: "{pdf_path.resolve()}")
guard let doc = PDFDocument(url: srcUrl) else {{
    print("ERROR: Unable to load PDF")
    exit(1)
}}

let count = doc.pageCount
guard count > 0, let firstPage = doc.page(at: 0) else {{
    print("ERROR: PDF has no pages")
    exit(2)
}}

let bounds = firstPage.bounds(for: .mediaBox)
print("\\(count)|\\(bounds.width)|\\(bounds.height)")

for i in 0..<count {{
    guard let page = doc.page(at: i) else {{ continue }}
    let single = PDFDocument()
    single.insert(page, at: 0)
    let outUrl = URL(fileURLWithPath: "{output_dir.resolve()}/page_\\(i + 1).pdf")
    single.write(to: outUrl)
}}
"""
    result = subprocess.run(["swift", "-e", swift_script], capture_output=True, text=True, check=True)
    first_line = result.stdout.strip().split("\n")[0]
    parts = first_line.split("|")
    count = int(parts[0])
    width = float(parts[1])
    height = float(parts[2])
    return count, width, height


def build_keynote_presentation(
    page_count: int,
    width: float,
    height: float,
    pages_dir: Path,
    output_key_path: Path,
    open_when_done: bool = True
) -> None:
    """
    Automates Apple Keynote via AppleScript to create a new presentation,
    populate it with slides matching the source dimensions, and save the .key package.
    """
    abs_out_path = output_key_path.resolve()
    
    # Construct AppleScript to build slides and save
    applescript = f"""
tell application "Keynote"
    activate
    set doc to make new document with properties {{width:{width}, height:{height}}}
    tell doc
        set bLayout to slide layout "Blank"
        set s1 to slide 1
        set base slide of s1 to bLayout
        tell s1
            set img to make new image with properties {{file:POSIX file "{pages_dir.resolve()}/page_1.pdf"}}
            set width of img to {width}
            set height of img to {height}
            set position of img to {{0, 0}}
        end tell
        
        repeat with i from 2 to {page_count}
            set pFile to "{pages_dir.resolve()}/page_" & (i as string) & ".pdf"
            set newSlide to make new slide with properties {{base slide:bLayout}}
            tell newSlide
                set img to make new image with properties {{file:POSIX file pFile}}
                set width of img to {width}
                set height of img to {height}
                set position of img to {{0, 0}}
            end tell
        end repeat
    end tell
    
    set targetFile to POSIX file "{abs_out_path}"
    save doc in targetFile
    close doc saving no
end tell
"""
    # Execute AppleScript
    subprocess.run(["osascript", "-e", applescript], check=True, capture_output=True, text=True)

    # Re-open native file cleanly so Keynote binds directly to the saved document
    if open_when_done:
        subprocess.run(["open", str(abs_out_path)], check=True)


def convert_pdf_to_keynote(
    pdf_path: str | Path,
    output_path: str | Path | None = None,
    open_result: bool = True
) -> Path:
    """
    Converts a PDF presentation to a Keynote project (.key).
    """
    src = Path(pdf_path).resolve()
    if not src.exists():
        raise FileNotFoundError(f"Input file not found: {src}")

    if not is_keynote_available():
        raise RuntimeError("Apple Keynote is not installed on this system.")

    if output_path:
        out = Path(output_path).resolve()
    else:
        out = src.with_suffix(".key")

    with tempfile.TemporaryDirectory(prefix="keynote_conv_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        print(f"[*] Extracting vector pages from {src.name}...")
        page_count, width, height = extract_pdf_pages_swift(src, tmp_path)
        print(f"[*] Found {page_count} pages with dimensions {width}x{height} pt.")
        
        print(f"[*] Generating Keynote presentation at {out.name}...")
        build_keynote_presentation(
            page_count=page_count,
            width=width,
            height=height,
            pages_dir=tmp_path,
            output_key_path=out,
            open_when_done=open_result
        )

    print(f"[✓] Successfully converted and saved: {out}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Keynote Tools: Convert PDF presentations to native Apple Keynote (.key) projects"
    )
    parser.add_argument("input", help="Path to input PDF file (.pdf)")
    parser.add_argument("-o", "--output", help="Path to output Keynote presentation (.key)")
    parser.add_argument("--no-open", dest="open", action="store_false", default=True, help="Do not open presentation in Keynote")

    args = parser.parse_args()
    try:
        convert_pdf_to_keynote(args.input, output_path=args.output, open_result=args.open)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
