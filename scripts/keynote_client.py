#!/usr/bin/env python3
"""
Keynote Automation Client for macOS
Provides robust Python and AppleScript bindings to inspect, manipulate,
create, and export Apple Keynote presentations on macOS.
"""

import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union


def hex_to_rgb16(hex_str: str) -> Tuple[int, int, int]:
    """Convert hex color string (e.g. '#2563eb' or '2563eb') to AppleScript 16-bit RGB (0-65535)."""
    hex_clean = hex_str.strip().lstrip("#")
    if len(hex_clean) == 3:
        hex_clean = "".join(c * 2 for c in hex_clean)
    if len(hex_clean) != 6:
        return (0, 0, 0)
    r8 = int(hex_clean[0:2], 16)
    g8 = int(hex_clean[2:4], 16)
    b8 = int(hex_clean[4:6], 16)
    return (int(r8 * 65535 / 255), int(g8 * 65535 / 255), int(b8 * 65535 / 255))


def rgb16_to_hex(r16: int, g16: int, b16: int) -> str:
    """Convert AppleScript 16-bit RGB (0-65535) to standard hex string (#rrggbb)."""
    r8 = min(255, max(0, int(round(r16 * 255 / 65535))))
    g8 = min(255, max(0, int(round(g16 * 255 / 65535))))
    b8 = min(255, max(0, int(round(b16 * 255 / 65535))))
    return f"#{r8:02x}{g8:02x}{b8:02x}"


def escape_applescript_string(s: str) -> str:
    """Safely escape text for AppleScript literal string."""
    if s is None:
        return ""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\r\n", "\n").replace("\r", "\n")


class KeynoteClient:
    """Client for controlling Keynote.app and active presentations on macOS."""

    def __init__(self, doc_name: Optional[str] = None):
        self.doc_name = doc_name

    def run_applescript(self, script: str) -> Tuple[bool, str, str]:
        """Execute an AppleScript string via osascript and return (success, stdout, stderr)."""
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        return (res.returncode == 0, res.stdout.strip(), res.stderr.strip())

    def _doc_target(self) -> str:
        """Returns the AppleScript target reference for the document."""
        if self.doc_name:
            escaped = escape_applescript_string(self.doc_name)
            return f'document "{escaped}"'
        return "front document"

    def is_running(self) -> bool:
        """Check if Keynote is currently running."""
        script = 'tell application "System Events" to return (name of processes) contains "Keynote"'
        ok, out, _ = self.run_applescript(script)
        return ok and out.strip().lower() == "true"

    def activate(self) -> bool:
        """Activate Keynote.app."""
        script = 'tell application "Keynote" to activate'
        ok, _, _ = self.run_applescript(script)
        return ok

    def get_doc_info(self) -> Dict[str, Any]:
        """Retrieve comprehensive metadata about the target / active presentation."""
        target = self._doc_target()
        script = f"""
tell application "Keynote"
    if (count of documents) = 0 then
        error "No presentation is currently open in Keynote."
    end if
    set doc to {target}
    set dName to name of doc
    set dWidth to width of doc
    set dHeight to height of doc
    set sCount to count of slides of doc
    set curSlideNum to slide number of (current slide of doc)
    
    set layoutList to {{}}
    repeat with l in slide layouts of doc
        set end of layoutList to name of l
    end repeat
    
    set dFile to ""
    try
        set dFile to POSIX path of (file of doc as text)
    end try
    
    set outText to dName & "\t" & (dWidth as text) & "\t" & (dHeight as text) & "\t" & (sCount as text) & "\t" & (curSlideNum as text) & "\t" & dFile
    return outText
end tell
"""
        ok, out, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to query Keynote doc info: {err}")

        parts = out.split("\t")
        layouts = self.get_layouts()

        return {
            "name": parts[0] if len(parts) > 0 else "",
            "width": int(float(parts[1])) if len(parts) > 1 else 1920,
            "height": int(float(parts[2])) if len(parts) > 2 else 1080,
            "slide_count": int(parts[3]) if len(parts) > 3 else 0,
            "active_slide_index": int(parts[4]) if len(parts) > 4 else 1,
            "file_path": parts[5] if len(parts) > 5 else None,
            "layouts": layouts,
        }

    def get_layouts(self) -> List[str]:
        """Get list of available slide layout master names in the active document."""
        target = self._doc_target()
        script = f"""
tell application "Keynote"
    set doc to {target}
    set layoutList to {{}}
    repeat with l in slide layouts of doc
        set end of layoutList to name of l
    end repeat
    set AppleScript's text item delimiters to "|||"
    return layoutList as text
end tell
"""
        ok, out, _ = self.run_applescript(script)
        if not ok or not out:
            return []
        return [l.strip() for l in out.split("|||") if l.strip()]

    def list_slides(self) -> List[Dict[str, Any]]:
        """List all slides with summary information (slide number, layout, title preview, notes preview)."""
        target = self._doc_target()
        script = f"""
tell application "Keynote"
    set doc to {target}
    set sCount to count of slides of doc
    set outList to {{}}
    repeat with i from 1 to sCount
        set s to slide i of doc
        set lName to name of (base layout of s)
        set isSkipped to skipped of s
        set pNotes to presenter notes of s
        if pNotes is missing value then set pNotes to ""
        
        set sTitle to ""
        try
            if title showing of s then
                set sTitle to object text of (default title item of s)
            end if
        end try
        
        if sTitle = "" then
            repeat with itm in (iWork items of s)
                try
                    set candidate to object text of itm as text
                    if candidate is not "" and length of candidate > 1 then
                        set sTitle to candidate
                        exit repeat
                    end if
                end try
            end repeat
        end if
        
        set itmCount to count of (iWork items of s)
        
        set previewTitle to ""
        if sTitle is not "" then
            set cleanT to paragraphs of sTitle
            if (count of cleanT) > 0 then
                set previewTitle to item 1 of cleanT
            end if
        end if
        
        set previewNotes to ""
        if pNotes is not "" then
            set cleanN to paragraphs of pNotes
            if (count of cleanN) > 0 then
                set previewNotes to item 1 of cleanN
            end if
        end if
        
        set end of outList to (i as text) & "<::>" & lName & "<::>" & (isSkipped as text) & "<::>" & (itmCount as text) & "<::>" & previewTitle & "<::>" & previewNotes
    end repeat
    
    set AppleScript's text item delimiters to linefeed
    return outList as text
end tell
"""
        ok, out, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to list slides: {err}")

        slides = []
        if not out.strip():
            return slides

        for line in out.splitlines():
            if not line.strip():
                continue
            parts = line.split("<::>")
            if len(parts) >= 4:
                idx = int(parts[0])
                layout = parts[1]
                skipped = parts[2].lower() == "true"
                item_count = int(parts[3])
                title = parts[4] if len(parts) > 4 else ""
                notes = parts[5] if len(parts) > 5 else ""
                slides.append({
                    "index": idx,
                    "layout": layout,
                    "skipped": skipped,
                    "item_count": item_count,
                    "title": title.strip(),
                    "notes_preview": notes.strip(),
                })
        return slides

    def set_active_slide(self, slide_index: int) -> bool:
        """Switch Keynote's active visible slide to slide_index (1-indexed)."""
        target = self._doc_target()
        script = f"""
tell application "Keynote"
    set doc to {target}
    tell doc
        set current slide to slide {slide_index}
    end tell
    return slide number of (current slide of doc)
end tell
"""
        ok, out, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to select slide {slide_index}: {err}")
        return int(out) == slide_index

    def get_slide_detail(self, slide_index: int) -> Dict[str, Any]:
        """Extract full object inspection of slide_index including all shapes, text items, images, tables, notes."""
        target = self._doc_target()
        script = f"""
tell application "Keynote"
    set doc to {target}
    set s to slide {slide_index} of doc
    set lName to name of (base layout of s)
    set isSkipped to skipped of s
    set pNotes to presenter notes of s
    if pNotes is missing value then set pNotes to ""
    
    set outItems to {{}}
    set itms to iWork items of s
    set idx to 1
    repeat with itm in itms
        set itmClass to (class of itm) as text
        set itmPos to position of itm
        set posX to item 1 of itmPos
        set posY to item 2 of itmPos
        set posW to width of itm
        set posH to height of itm
        set itmRot to rotation of itm
        set itmOpac to opacity of itm
        
        set itmText to ""
        set itmFont to ""
        set itmSize to 0
        set itmColor to ""
        set itmExtra to ""
        
        if itmClass contains "shape" or itmClass contains "text item" then
            try
                set itmText to object text of itm as text
                set itmFont to font of object text of itm as text
                set itmSize to size of object text of itm as real
                set cRec to color of object text of itm
                set itmColor to (item 1 of cRec as text) & "," & (item 2 of cRec as text) & "," & (item 3 of cRec as text)
            end try
        else if itmClass contains "image" then
            try
                set itmExtra to file name of itm as text
            end try
            try
                set itmText to description of itm as text
            end try
        else if itmClass contains "table" then
            try
                set itmExtra to "rows=" & (row count of itm as text) & ";cols=" & (column count of itm as text)
            end try
        else if itmClass contains "line" then
            try
                set sp to start point of itm
                set ep to end point of itm
                set itmExtra to "start=" & (item 1 of sp as text) & "," & (item 2 of sp as text) & ";end=" & (item 1 of ep as text) & "," & (item 2 of ep as text)
            end try
        end if
        
        set itemRecord to (idx as text) & "<|>" & itmClass & "<|>" & (posX as text) & "<|>" & (posY as text) & "<|>" & (posW as text) & "<|>" & (posH as text) & "<|>" & (itmRot as text) & "<|>" & (itmOpac as text) & "<|>" & (itmSize as text) & "<|>" & itmFont & "<|>" & itmColor & "<|>" & itmExtra & "<|>" & itmText
        set end of outItems to itemRecord
        set idx to idx + 1
    end repeat
    
    set AppleScript's text item delimiters to "<#ITEM#>"
    set allItemsText to outItems as text
    return ({slide_index} as text) & "<#SLIDE#>" & lName & "<#SLIDE#>" & (isSkipped as text) & "<#SLIDE#>" & pNotes & "<#SLIDE#>" & allItemsText
end tell
"""
        ok, out, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to inspect slide {slide_index}: {err}")

        slide_parts = out.split("<#SLIDE#>")
        s_idx = int(slide_parts[0])
        layout_name = slide_parts[1]
        skipped = slide_parts[2].lower() == "true"
        notes = slide_parts[3]
        items_blob = slide_parts[4] if len(slide_parts) > 4 else ""

        items = []
        if items_blob.strip():
            for itm_raw in items_blob.split("<#ITEM#>"):
                if not itm_raw.strip():
                    continue
                p = itm_raw.split("<|>")
                if len(p) >= 12:
                    color_hex = None
                    if p[10].strip():
                        c_parts = p[10].split(",")
                        if len(c_parts) == 3:
                            try:
                                color_hex = rgb16_to_hex(int(c_parts[0]), int(c_parts[1]), int(c_parts[2]))
                            except Exception:
                                pass

                    items.append({
                        "item_index": int(p[0]),
                        "type": p[1].replace("«class ", "").replace("»", "").strip(),
                        "x": int(float(p[2])),
                        "y": int(float(p[3])),
                        "width": int(float(p[4])),
                        "height": int(float(p[5])),
                        "rotation": int(p[6]),
                        "opacity": int(p[7]),
                        "font_size": float(p[8]) if p[8] and float(p[8]) > 0 else None,
                        "font_name": p[9] if p[9] else None,
                        "text_color": color_hex,
                        "extra": p[11],
                        "text": p[12] if len(p) > 12 else "",
                    })

        return {
            "slide_index": s_idx,
            "layout": layout_name,
            "skipped": skipped,
            "presenter_notes": notes,
            "items": items,
        }

    def add_slide(self, layout: str = "Blank", after_slide: Optional[int] = None) -> int:
        """Create a new slide with specified layout master. Returns new slide index."""
        target = self._doc_target()
        layout_esc = escape_applescript_string(layout)
        after_clause = f"after slide {after_slide} of doc" if after_slide is not None else "at end of slides of doc"

        script = f"""
tell application "Keynote"
    set doc to {target}
    set targetLayout to slide layout "{layout_esc}" of doc
    set newSlide to make new slide at {after_clause} with properties {{base layout:targetLayout}}
    return slide number of newSlide
end tell
"""
        ok, out, err = self.run_applescript(script)
        if not ok:
            script_fallback = f"""
tell application "Keynote"
    set doc to {target}
    set newSlide to make new slide at {after_clause}
    return slide number of newSlide
end tell
"""
            ok2, out2, err2 = self.run_applescript(script_fallback)
            if not ok2:
                raise RuntimeError(f"Failed to add slide: {err} | {err2}")
            return int(out2)
        return int(out)

    def duplicate_slide(self, slide_index: int) -> int:
        """Duplicate slide_index. Placed directly after slide_index. Returns new slide index."""
        target = self._doc_target()
        script = f"""
tell application "Keynote"
    set doc to {target}
    duplicate slide {slide_index} of doc
    return {slide_index + 1}
end tell
"""
        ok, out, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to duplicate slide {slide_index}: {err}")
        return int(out)

    def delete_slide(self, slide_index: int) -> bool:
        """Delete slide at slide_index (1-indexed)."""
        target = self._doc_target()
        script = f"""
tell application "Keynote"
    set doc to {target}
    delete slide {slide_index} of doc
    return true
end tell
"""
        ok, _, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to delete slide {slide_index}: {err}")
        return True

    def move_slide(self, from_index: int, to_index: int, position: str = "before") -> bool:
        """Move slide from from_index to before/after to_index."""
        target = self._doc_target()
        pos_kw = "before" if position.lower() == "before" else "after"
        script = f"""
tell application "Keynote"
    set doc to {target}
    move slide {from_index} of doc to {pos_kw} slide {to_index} of doc
    return true
end tell
"""
        ok, _, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to move slide {from_index} {pos_kw} slide {to_index}: {err}")
        return True

    def set_presenter_notes(self, slide_index: int, notes: str) -> bool:
        """Set presenter notes for slide_index."""
        target = self._doc_target()
        notes_esc = escape_applescript_string(notes)
        script = f"""
tell application "Keynote"
    set doc to {target}
    set presenter notes of slide {slide_index} of doc to "{notes_esc}"
    return true
end tell
"""
        ok, _, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to set presenter notes for slide {slide_index}: {err}")
        return True

    def append_presenter_notes(self, slide_index: int, notes: str) -> bool:
        """Append text to presenter notes for slide_index."""
        target = self._doc_target()
        notes_esc = escape_applescript_string(notes)
        script = f"""
tell application "Keynote"
    set doc to {target}
    set curNotes to presenter notes of slide {slide_index} of doc
    if curNotes is missing value or curNotes is "" then
        set presenter notes of slide {slide_index} of doc to "{notes_esc}"
    else
        set presenter notes of slide {slide_index} of doc to curNotes & linefeed & "{notes_esc}"
    end if
    return true
end tell
"""
        ok, _, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to append presenter notes for slide {slide_index}: {err}")
        return True

    def add_text_item(
        self,
        slide_index: int,
        text: str,
        x: int,
        y: int,
        width: int,
        height: int,
        font: Optional[str] = None,
        size: Optional[float] = None,
        color: Optional[str] = None,
    ) -> int:
        """Add a text box to slide_index with optional font, font size, and hex text color."""
        target = self._doc_target()
        text_esc = escape_applescript_string(text)

        font_cmd = f'set font of object text of tItem to "{escape_applescript_string(font)}"' if font else ""
        size_cmd = f"set size of object text of tItem to {size}" if size else ""
        color_cmd = ""
        if color:
            r16, g16, b16 = hex_to_rgb16(color)
            color_cmd = f"set color of object text of tItem to {{{r16}, {g16}, {b16}}}"

        script = f"""
tell application "Keynote"
    set doc to {target}
    tell slide {slide_index} of doc
        set tItem to make new text item with properties {{object text:"{text_esc}", position:{{{x}, {y}}}, width:{width}, height:{height}}}
        {font_cmd}
        {size_cmd}
        {color_cmd}
        return (count of iWork items)
    end tell
end tell
"""
        ok, out, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to add text item on slide {slide_index}: {err}")
        return int(out)

    def add_shape(
        self,
        slide_index: int,
        x: int,
        y: int,
        width: int,
        height: int,
        text: Optional[str] = None,
        font: Optional[str] = None,
        size: Optional[float] = None,
        text_color: Optional[str] = None,
        opacity: int = 100,
        rotation: int = 0,
    ) -> int:
        """Add a shape container with optional text and opacity to slide_index."""
        target = self._doc_target()
        text_cmd = ""
        if text is not None:
            text_esc = escape_applescript_string(text)
            text_cmd = f'set object text of shp to "{text_esc}"\n'
            if font:
                text_cmd += f'set font of object text of shp to "{escape_applescript_string(font)}"\n'
            if size:
                text_cmd += f"set size of object text of shp to {size}\n"
            if text_color:
                r16, g16, b16 = hex_to_rgb16(text_color)
                text_cmd += f"set color of object text of shp to {{{r16}, {g16}, {b16}}}\n"

        script = f"""
tell application "Keynote"
    set doc to {target}
    tell slide {slide_index} of doc
        set shp to make new shape with properties {{position:{{{x}, {y}}}, width:{width}, height:{height}, opacity:{opacity}, rotation:{rotation}}}
        {text_cmd}
        return (count of iWork items)
    end tell
end tell
"""
        ok, out, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to add shape on slide {slide_index}: {err}")
        return int(out)

    def add_image(
        self,
        slide_index: int,
        file_path: str,
        x: int,
        y: int,
        width: Optional[int] = None,
        height: Optional[int] = None,
        opacity: int = 100,
        rotation: int = 0,
        description: Optional[str] = None,
    ) -> int:
        """Insert an image from local file path onto slide_index."""
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Image file not found: {abs_path}")

        target = self._doc_target()
        size_props = ""
        if width is not None and height is not None:
            size_props = f", width:{width}, height:{height}"
        elif width is not None:
            size_props = f", width:{width}"
        elif height is not None:
            size_props = f", height:{height}"

        desc_cmd = ""
        if description:
            desc_cmd = f'set description of imgItem to "{escape_applescript_string(description)}"'

        script = f"""
tell application "Keynote"
    set doc to {target}
    tell slide {slide_index} of doc
        set imgItem to make new image with properties {{file:POSIX file "{abs_path}", position:{{{x}, {y}}}{size_props}, opacity:{opacity}, rotation:{rotation}}}
        {desc_cmd}
        return (count of iWork items)
    end tell
end tell
"""
        ok, out, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to insert image on slide {slide_index}: {err}")
        return int(out)

    def add_table(
        self,
        slide_index: int,
        rows: int,
        cols: int,
        x: int,
        y: int,
        width: int,
        height: int,
        data: Optional[List[List[Any]]] = None,
        header_row: bool = True,
        header_bg: Optional[str] = None,
        header_fg: Optional[str] = None,
        cell_fg: Optional[str] = None,
        font_size: Optional[float] = None,
    ) -> int:
        """Add a formatted table to slide_index with optional cell values, header background, and text colors."""
        target = self._doc_target()
        header_count = 1 if header_row else 0

        cell_ops = []
        if data:
            for r_idx, row in enumerate(data, start=1):
                if r_idx > rows:
                    break
                for c_idx, val in enumerate(row, start=1):
                    if c_idx > cols:
                        break
                    v_str = escape_applescript_string(str(val))
                    cell_ops.append(f'set value of cell {c_idx} of row {r_idx} to "{v_str}"')

        header_styling = []
        if header_row and header_bg:
            r16, g16, b16 = hex_to_rgb16(header_bg)
            for c_idx in range(1, cols + 1):
                header_styling.append(f"set background color of cell {c_idx} of row 1 to {{{r16}, {g16}, {b16}}}")
        if header_row and header_fg:
            r16, g16, b16 = hex_to_rgb16(header_fg)
            for c_idx in range(1, cols + 1):
                header_styling.append(f"set text color of cell {c_idx} of row 1 to {{{r16}, {g16}, {b16}}}")

        cell_styling = []
        if cell_fg:
            r16, g16, b16 = hex_to_rgb16(cell_fg)
            start_r = 2 if header_row else 1
            for r_idx in range(start_r, rows + 1):
                for c_idx in range(1, cols + 1):
                    cell_styling.append(f"set text color of cell {c_idx} of row {r_idx} to {{{r16}, {g16}, {b16}}}")

        font_styling = []
        if font_size:
            font_styling.append(f"set font size of cell range of tbl to {font_size}")

        all_table_body = "\n".join(cell_ops + header_styling + cell_styling + font_styling)

        script = f"""
tell application "Keynote"
    set doc to {target}
    tell slide {slide_index} of doc
        set tbl to make new table with properties {{row count:{rows}, column count:{cols}, position:{{{x}, {y}}}, width:{width}, height:{height}, header row count:{header_count}}}
        tell tbl
            {all_table_body}
        end tell
        return (count of iWork items)
    end tell
end tell
"""
        ok, out, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to add table on slide {slide_index}: {err}")
        return int(out)

    def add_line(
        self,
        slide_index: int,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
    ) -> int:
        """Add a connecting line between start and end coordinates on slide_index."""
        target = self._doc_target()
        script = f"""
tell application "Keynote"
    set doc to {target}
    tell slide {slide_index} of doc
        set ln to make new line with properties {{start point:{{{start_x}, {start_y}}}, end point:{{{end_x}, {end_y}}}}}
        return (count of iWork items)
    end tell
end tell
"""
        ok, out, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to add line on slide {slide_index}: {err}")
        return int(out)

    def delete_item(self, slide_index: int, item_index: int) -> bool:
        """Delete an iWork item by index from slide_index."""
        target = self._doc_target()
        script = f"""
tell application "Keynote"
    set doc to {target}
    delete iWork item {item_index} of slide {slide_index} of doc
    return true
end tell
"""
        ok, _, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to delete item {item_index} on slide {slide_index}: {err}")
        return True

    def find_text(self, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Search for occurrences of query text across all slides and elements."""
        slides = self.list_slides()
        matches = []
        target = query if case_sensitive else query.lower()

        for s in slides:
            s_idx = s["index"]
            detail = self.get_slide_detail(s_idx)
            notes = detail.get("presenter_notes", "")
            notes_cmp = notes if case_sensitive else notes.lower()
            if target in notes_cmp:
                matches.append({
                    "slide_index": s_idx,
                    "location": "presenter_notes",
                    "item_index": None,
                    "item_type": None,
                    "text": notes,
                })
            for item in detail.get("items", []):
                t = item.get("text", "")
                if not t:
                    continue
                t_cmp = t if case_sensitive else t.lower()
                if target in t_cmp:
                    matches.append({
                        "slide_index": s_idx,
                        "location": "item",
                        "item_index": item["item_index"],
                        "item_type": item["type"],
                        "text": t,
                        "bounds": {"x": item["x"], "y": item["y"], "width": item["width"], "height": item["height"]},
                    })

        return matches

    def replace_text(
        self,
        find_str: str,
        replace_str: str,
        slide_index: Optional[int] = None,
        case_sensitive: bool = False,
    ) -> int:
        """Search and replace occurrences of find_str with replace_str in items and presenter notes."""
        target = self._doc_target()
        find_esc = escape_applescript_string(find_str)
        replace_esc = escape_applescript_string(replace_str)
        slide_range_clause = f"set targetSlides to {{slide {slide_index} of doc}}" if slide_index else "set targetSlides to slides of doc"

        script = f"""
tell application "Keynote"
    set doc to {target}
    {slide_range_clause}
    set replaceCount to 0
    
    repeat with s in targetSlides
        set pNotes to presenter notes of s
        if pNotes is not missing value and pNotes contains "{find_esc}" then
            set AppleScript's text item delimiters to "{find_esc}"
            set textParts to text items of pNotes
            set AppleScript's text item delimiters to "{replace_esc}"
            set presenter notes of s to (textParts as text)
            set replaceCount to replaceCount + 1
        end if
        
        repeat with itm in (iWork items of s)
            try
                set itmText to object text of itm as text
                if itmText contains "{find_esc}" then
                    set AppleScript's text item delimiters to "{find_esc}"
                    set textParts to text items of itmText
                    set AppleScript's text item delimiters to "{replace_esc}"
                    set object text of itm to (textParts as text)
                    set replaceCount to replaceCount + 1
                end if
            end try
        end repeat
    end repeat
    
    return replaceCount
end tell
"""
        ok, out, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Failed to replace text: {err}")
        return int(out)

    def export(
        self,
        output_path: str,
        export_format: str = "pdf",
        skipped_slides: bool = False,
    ) -> str:
        """Export presentation to PDF, PNG slide images, JPEG slide images, PPTX, or HTML."""
        target = self._doc_target()
        abs_out = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(abs_out), exist_ok=True)

        fmt_lower = export_format.lower().strip()
        if fmt_lower in ["pdf"]:
            script = f"""
tell application "Keynote"
    set doc to {target}
    export doc to POSIX file "{abs_out}" as PDF with properties {{skipped slides:{str(skipped_slides).lower()}}}
    return "{abs_out}"
end tell
"""
        elif fmt_lower in ["png", "slide images", "img"]:
            script = f"""
tell application "Keynote"
    set doc to {target}
    export doc to POSIX file "{abs_out}" as slide images with properties {{image format:PNG, skipped slides:{str(skipped_slides).lower()}}}
    return "{abs_out}"
end tell
"""
        elif fmt_lower in ["jpg", "jpeg"]:
            script = f"""
tell application "Keynote"
    set doc to {target}
    export doc to POSIX file "{abs_out}" as slide images with properties {{image format:JPEG, skipped slides:{str(skipped_slides).lower()}}}
    return "{abs_out}"
end tell
"""
        elif fmt_lower in ["pptx", "powerpoint"]:
            script = f"""
tell application "Keynote"
    set doc to {target}
    export doc to POSIX file "{abs_out}" as Microsoft PowerPoint
    return "{abs_out}"
end tell
"""
        elif fmt_lower in ["html"]:
            script = f"""
tell application "Keynote"
    set doc to {target}
    export doc to POSIX file "{abs_out}" as HTML
    return "{abs_out}"
end tell
"""
        else:
            raise ValueError(f"Unsupported export format: {export_format}. Use pdf, png, jpeg, pptx, or html.")

        ok, out, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Export failed: {err}")
        return abs_out

    def slideshow_control(self, action: str = "start") -> bool:
        """Control presentation playback: start, stop, next, previous."""
        target = self._doc_target()
        act = action.lower().strip()
        if act == "start":
            script = f'tell application "Keynote" to start {target}'
        elif act == "stop":
            script = 'tell application "Keynote" to stop front document'
        elif act in ["next", "forward", "step"]:
            script = 'tell application "Keynote" to show next'
        elif act in ["previous", "prev", "back"]:
            script = 'tell application "Keynote" to show previous'
        else:
            raise ValueError(f"Unknown playback action: {action}")

        ok, _, err = self.run_applescript(script)
        if not ok:
            raise RuntimeError(f"Playback action {action} failed: {err}")
        return True


if __name__ == "__main__":
    client = KeynoteClient()
    if not client.is_running():
        print("Keynote is not running.")
        sys.exit(1)
    try:
        info = client.get_doc_info()
        print(json.dumps(info, indent=2))
    except Exception as e:
        print(f"Error: {e}")
