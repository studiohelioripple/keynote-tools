#!/usr/bin/env python3
"""
Keynote CLI Tool (knt / keynote-tool)
Comprehensive command-line interface to inspect, manipulate, style,
and export Apple Keynote presentations on macOS.
"""

import argparse
import json
import os
import sys
import tempfile
from typing import Optional

from keynote_client import KeynoteClient
from theme_engine import list_available_themes, get_theme
from deck_builder import DeckBuilder


def print_table(headers, rows):
    """Simple terminal table formatter."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))
    
    header_str = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    sep_str = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    print(header_str)
    print(sep_str)
    for row in rows:
        print(" | ".join(f"{str(val):<{col_widths[i]}}" for i, val in enumerate(row)))


def cmd_info(args, client: KeynoteClient):
    info = client.get_doc_info()
    if args.json:
        print(json.dumps(info, indent=2))
        return
    print("\n📊 Active Keynote Presentation")
    print("=" * 45)
    print(f"  • Name:             {info['name']}")
    print(f"  • Dimensions:       {info['width']} x {info['height']} px")
    print(f"  • Total Slides:     {info['slide_count']}")
    print(f"  • Active Slide:     Slide #{info['active_slide_index']}")
    if info.get("file_path") and not info["file_path"].endswith("missing value"):
        print(f"  • File Path:        {info['file_path']}")
    print(f"  • Master Layouts:   {', '.join(info['layouts'][:5])} ({len(info['layouts'])} total)")
    print()


def cmd_slides_list(args, client: KeynoteClient):
    slides = client.list_slides()
    if args.json:
        print(json.dumps(slides, indent=2))
        return
    
    if not slides:
        print("No slides found in active presentation.")
        return

    headers = ["#", "Layout", "Items", "Title Preview", "Presenter Notes"]
    rows = []
    for s in slides:
        skip_mark = " (skipped)" if s["skipped"] else ""
        rows.append([
            f"{s['index']}{skip_mark}",
            s["layout"][:18],
            str(s["item_count"]),
            (s["title"][:36] + "...") if len(s["title"]) > 36 else s["title"],
            (s["notes_preview"][:30] + "...") if len(s["notes_preview"]) > 30 else s["notes_preview"],
        ])
    print()
    print_table(headers, rows)
    print()


def cmd_slides_show(args, client: KeynoteClient):
    client.set_active_slide(args.slide)
    print(f"Switched active view to Slide #{args.slide}.")


def cmd_slides_get(args, client: KeynoteClient):
    detail = client.get_slide_detail(args.slide)
    if args.json:
        print(json.dumps(detail, indent=2))
        return
    
    print(f"\n🔍 Slide #{detail['slide_index']} Details [Layout: {detail['layout']}]")
    print("=" * 60)
    if detail["presenter_notes"]:
        print(f"📝 Presenter Notes:\n{detail['presenter_notes']}\n")
    
    print(f"📦 Items ({len(detail['items'])}):")
    for itm in detail["items"]:
        color_str = f" | color: {itm['text_color']}" if itm.get("text_color") else ""
        font_str = f" | font: {itm['font_name']} {itm['font_size']}pt" if itm.get("font_name") else ""
        text_str = f" | text: \"{itm['text']}\"" if itm.get("text") else ""
        extra_str = f" | {itm['extra']}" if itm.get("extra") else ""
        print(f"  [{itm['item_index']}] {itm['type'].upper()} at ({itm['x']}, {itm['y']}) {itm['width']}x{itm['height']}px{font_str}{color_str}{extra_str}{text_str}")
    print()


def cmd_slides_add(args, client: KeynoteClient):
    idx = client.add_slide(layout=args.layout, after_slide=args.after)
    print(f"Created new slide with layout '{args.layout}' at Slide #{idx}.")


def cmd_slides_duplicate(args, client: KeynoteClient):
    idx = client.duplicate_slide(args.slide)
    print(f"Duplicated Slide #{args.slide} -> New Slide #{idx}.")


def cmd_slides_delete(args, client: KeynoteClient):
    client.delete_slide(args.slide)
    print(f"Deleted Slide #{args.slide}.")


def cmd_slides_move(args, client: KeynoteClient):
    client.move_slide(args.slide, args.to, position=args.position)
    print(f"Moved Slide #{args.slide} {args.position} Slide #{args.to}.")


def cmd_notes_get(args, client: KeynoteClient):
    detail = client.get_slide_detail(args.slide)
    notes = detail.get("presenter_notes", "")
    if args.json:
        print(json.dumps({"slide": args.slide, "notes": notes}, indent=2))
    else:
        print(notes if notes else f"(No presenter notes for Slide #{args.slide})")


def cmd_notes_set(args, client: KeynoteClient):
    client.set_presenter_notes(args.slide, args.text)
    print(f"Updated presenter notes for Slide #{args.slide}.")


def cmd_notes_append(args, client: KeynoteClient):
    client.append_presenter_notes(args.slide, args.text)
    print(f"Appended text to presenter notes for Slide #{args.slide}.")


def cmd_text_find(args, client: KeynoteClient):
    matches = client.find_text(args.query, case_sensitive=args.case_sensitive)
    if args.json:
        print(json.dumps(matches, indent=2))
        return
    print(f"\n🔎 Search results for '{args.query}': ({len(matches)} matches)")
    print("=" * 60)
    for m in matches:
        loc = f"Slide #{m['slide_index']} ({m['location']})"
        if m.get("item_index") is not None:
            loc += f" [Item #{m['item_index']} - {m['item_type']}]"
        snippet = m['text'].strip().replace("\n", " ")
        if len(snippet) > 80:
            snippet = snippet[:80] + "..."
        print(f"  • {loc}: \"{snippet}\"")
    print()


def cmd_text_replace(args, client: KeynoteClient):
    count = client.replace_text(
        find_str=args.find,
        replace_str=args.replace,
        slide_index=args.slide,
        case_sensitive=args.case_sensitive,
    )
    scope = f"on Slide #{args.slide}" if args.slide else "across all slides"
    print(f"Replaced {count} occurrence(s) of '{args.find}' with '{args.replace}' {scope}.")


def cmd_text_add(args, client: KeynoteClient):
    client.add_text_item(
        slide_index=args.slide,
        text=args.text,
        x=args.x,
        y=args.y,
        width=args.w,
        height=args.h,
        font=args.font,
        size=args.size,
        color=args.color,
    )
    print(f"Added text item to Slide #{args.slide} at ({args.x}, {args.y}).")


def cmd_shape_add(args, client: KeynoteClient):
    client.add_shape(
        slide_index=args.slide,
        x=args.x,
        y=args.y,
        width=args.w,
        height=args.h,
        text=args.text,
        font=args.font,
        size=args.size,
        text_color=args.color,
        opacity=args.opacity,
        rotation=args.rotation,
    )
    print(f"Added shape container to Slide #{args.slide} at ({args.x}, {args.y}).")


def cmd_image_add(args, client: KeynoteClient):
    client.add_image(
        slide_index=args.slide,
        file_path=args.file,
        x=args.x,
        y=args.y,
        width=args.w,
        height=args.h,
        opacity=args.opacity,
        rotation=args.rotation,
        description=args.desc,
    )
    print(f"Inserted image '{args.file}' onto Slide #{args.slide} at ({args.x}, {args.y}).")


def cmd_table_add(args, client: KeynoteClient):
    data = None
    if args.csv:
        import csv
        with open(args.csv, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            data = list(reader)
    elif args.json_data:
        data = json.loads(args.json_data)

    client.add_table(
        slide_index=args.slide,
        rows=args.rows,
        cols=args.cols,
        x=args.x,
        y=args.y,
        width=args.w,
        height=args.h,
        data=data,
        header_row=not args.no_header,
        header_bg=args.header_bg,
        header_fg=args.header_fg,
        cell_fg=args.cell_fg,
        font_size=args.font_size,
    )
    print(f"Created {args.rows}x{args.cols} table on Slide #{args.slide} at ({args.x}, {args.y}).")


def cmd_line_add(args, client: KeynoteClient):
    client.add_line(
        slide_index=args.slide,
        start_x=args.x1,
        start_y=args.y1,
        end_x=args.x2,
        end_y=args.y2,
    )
    print(f"Created line connector on Slide #{args.slide} from ({args.x1},{args.y1}) to ({args.x2},{args.y2}).")


def cmd_item_delete(args, client: KeynoteClient):
    client.delete_item(slide_index=args.slide, item_index=args.item)
    print(f"Deleted item #{args.item} from Slide #{args.slide}.")


def cmd_export(args, client: KeynoteClient):
    out = client.export(
        output_path=args.output,
        export_format=args.format,
        skipped_slides=args.skipped,
    )
    print(f"Exported presentation as {args.format.upper()} to: {out}")


def cmd_render(args, client: KeynoteClient):
    out_dir = args.output_dir or tempfile.mkdtemp(prefix="keynote_render_")
    client.export(output_path=out_dir, export_format="png")
    exported_imgs = sorted([os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.endswith(".png")])
    print(f"\n🖼 Rendered {len(exported_imgs)} slide images to: {out_dir}")
    for img in exported_imgs:
        print(f"  • {img}")
    print()


def cmd_build(args, client: KeynoteClient):
    spec_path = os.path.abspath(args.spec)
    if not os.path.exists(spec_path):
        raise FileNotFoundError(f"Spec file not found: {spec_path}")
    
    with open(spec_path, "r", encoding="utf-8") as f:
        if spec_path.endswith((".yaml", ".yml")):
            try:
                import yaml
                spec = yaml.safe_load(f)
            except ImportError:
                print("Error: PyYAML not installed. Please use JSON spec format.")
                sys.exit(1)
        else:
            spec = json.load(f)

    builder = DeckBuilder(client=client, theme_name=spec.get("theme", "amil-light"))
    created = builder.build_from_spec(spec)
    print(f"Successfully generated {len(created)} slides from spec ({spec_path}).")


def cmd_themes(args, client: KeynoteClient):
    themes = list_available_themes()
    if args.json:
        print(json.dumps(themes, indent=2))
        return
    print("\n🎨 Available Curated Keynote Themes")
    print("=" * 60)
    headers = ["Theme ID", "Name", "Mode", "Accent", "Canvas BG"]
    rows = [[t["id"], t["name"], t["mode"], t["accent"], t["canvas_bg"]] for t in themes]
    print_table(headers, rows)
    print()


def cmd_play(args, client: KeynoteClient):
    client.slideshow_control(action=args.action)
    print(f"Slideshow action '{args.action}' executed.")


def main():
    parser = argparse.ArgumentParser(
        prog="knt",
        description="Keynote Automation CLI for macOS - Active presentation control, inspection, and manipulation",
    )
    parser.add_argument("--doc", help="Target document name (defaults to active front document)")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # info
    p_info = subparsers.add_parser("info", help="Get active document information")
    p_info.add_argument("--json", action="store_true", help="Output as JSON")

    # slides
    p_slides = subparsers.add_parser("slides", help="Slide-level operations")
    slides_sub = p_slides.add_subparsers(dest="slides_command")
    
    # slides list
    p_s_list = slides_sub.add_parser("list", help="List all slides")
    p_s_list.add_argument("--json", action="store_true", help="Output as JSON")

    # slides show
    p_s_show = slides_sub.add_parser("show", help="Go to slide")
    p_s_show.add_argument("slide", type=int, help="Slide number")

    # slides get
    p_s_get = slides_sub.add_parser("get", help="Get slide details and items")
    p_s_get.add_argument("slide", type=int, help="Slide number")
    p_s_get.add_argument("--json", action="store_true", help="Output as JSON")

    # slides add
    p_s_add = slides_sub.add_parser("add", help="Add a new slide")
    p_s_add.add_argument("--layout", default="Blank", help="Layout master name (default: Blank)")
    p_s_add.add_argument("--after", type=int, help="Insert after slide number")

    # slides duplicate
    p_s_dup = slides_sub.add_parser("duplicate", help="Duplicate slide")
    p_s_dup.add_argument("slide", type=int, help="Slide number")

    # slides delete
    p_s_del = slides_sub.add_parser("delete", help="Delete slide")
    p_s_del.add_argument("slide", type=int, help="Slide number")

    # slides move
    p_s_mov = slides_sub.add_parser("move", help="Move slide")
    p_s_mov.add_argument("slide", type=int, help="Slide number to move")
    p_s_mov.add_argument("--to", type=int, required=True, help="Target slide number")
    p_s_mov.add_argument("--position", choices=["before", "after"], default="before", help="Placement")

    # notes
    p_notes = subparsers.add_parser("notes", help="Presenter notes operations")
    notes_sub = p_notes.add_subparsers(dest="notes_command")
    
    p_n_get = notes_sub.add_parser("get", help="Get notes")
    p_n_get.add_argument("slide", type=int, help="Slide number")
    p_n_get.add_argument("--json", action="store_true", help="Output as JSON")

    p_n_set = notes_sub.add_parser("set", help="Set notes")
    p_n_set.add_argument("slide", type=int, help="Slide number")
    p_n_set.add_argument("--text", required=True, help="Notes text")

    p_n_app = notes_sub.add_parser("append", help="Append notes")
    p_n_app.add_argument("slide", type=int, help="Slide number")
    p_n_app.add_argument("--text", required=True, help="Notes text to append")

    # text
    p_text = subparsers.add_parser("text", help="Text operations")
    text_sub = p_text.add_subparsers(dest="text_command")
    
    p_t_find = text_sub.add_parser("find", help="Find text across presentation")
    p_t_find.add_argument("query", help="Search query")
    p_t_find.add_argument("--case-sensitive", action="store_true", help="Case-sensitive search")
    p_t_find.add_argument("--json", action="store_true", help="Output as JSON")

    p_t_rep = text_sub.add_parser("replace", help="Find and replace text")
    p_t_rep.add_argument("find", help="Text to find")
    p_t_rep.add_argument("replace", help="Replacement text")
    p_t_rep.add_argument("--slide", type=int, help="Limit replacement to specific slide")
    p_t_rep.add_argument("--case-sensitive", action="store_true", help="Case-sensitive match")

    p_t_add = text_sub.add_parser("add", help="Add text box")
    p_t_add.add_argument("--slide", type=int, required=True, help="Slide number")
    p_t_add.add_argument("--text", required=True, help="Text string")
    p_t_add.add_argument("--x", type=int, required=True, help="X coordinate")
    p_t_add.add_argument("--y", type=int, required=True, help="Y coordinate")
    p_t_add.add_argument("--w", type=int, required=True, help="Width")
    p_t_add.add_argument("--h", type=int, required=True, help="Height")
    p_t_add.add_argument("--font", help="Font PostScript name (e.g. SFProDisplay-Bold)")
    p_t_add.add_argument("--size", type=float, help="Font size in points")
    p_t_add.add_argument("--color", help="Hex color code (e.g. #2563eb)")

    # shape
    p_shape = subparsers.add_parser("shape", help="Shape operations")
    shape_sub = p_shape.add_subparsers(dest="shape_command")
    p_sh_add = shape_sub.add_parser("add", help="Add shape container")
    p_sh_add.add_argument("--slide", type=int, required=True, help="Slide number")
    p_sh_add.add_argument("--x", type=int, required=True, help="X coordinate")
    p_sh_add.add_argument("--y", type=int, required=True, help="Y coordinate")
    p_sh_add.add_argument("--w", type=int, required=True, help="Width")
    p_sh_add.add_argument("--h", type=int, required=True, help="Height")
    p_sh_add.add_argument("--text", help="Text content")
    p_sh_add.add_argument("--font", help="Font PostScript name")
    p_sh_add.add_argument("--size", type=float, help="Font size in points")
    p_sh_add.add_argument("--color", help="Text hex color")
    p_sh_add.add_argument("--opacity", type=int, default=100, help="Opacity (0-100)")
    p_sh_add.add_argument("--rotation", type=int, default=0, help="Rotation angle in degrees")

    # image
    p_img = subparsers.add_parser("image", help="Image operations")
    img_sub = p_img.add_subparsers(dest="image_command")
    p_im_add = img_sub.add_parser("add", help="Insert image")
    p_im_add.add_argument("--slide", type=int, required=True, help="Slide number")
    p_im_add.add_argument("--file", required=True, help="Path to image file")
    p_im_add.add_argument("--x", type=int, required=True, help="X coordinate")
    p_im_add.add_argument("--y", type=int, required=True, help="Y coordinate")
    p_im_add.add_argument("--w", type=int, help="Width")
    p_im_add.add_argument("--h", type=int, help="Height")
    p_im_add.add_argument("--opacity", type=int, default=100, help="Opacity (0-100)")
    p_im_add.add_argument("--rotation", type=int, default=0, help="Rotation angle")
    p_im_add.add_argument("--desc", help="Accessibility description")

    # table
    p_tbl = subparsers.add_parser("table", help="Table operations")
    tbl_sub = p_tbl.add_subparsers(dest="table_command")
    p_tb_add = tbl_sub.add_parser("add", help="Add table")
    p_tb_add.add_argument("--slide", type=int, required=True, help="Slide number")
    p_tb_add.add_argument("--rows", type=int, required=True, help="Number of rows")
    p_tb_add.add_argument("--cols", type=int, required=True, help="Number of columns")
    p_tb_add.add_argument("--x", type=int, required=True, help="X coordinate")
    p_tb_add.add_argument("--y", type=int, required=True, help="Y coordinate")
    p_tb_add.add_argument("--w", type=int, required=True, help="Width")
    p_tb_add.add_argument("--h", type=int, required=True, help="Height")
    p_tb_add.add_argument("--csv", help="Path to CSV file to populate table")
    p_tb_add.add_argument("--json-data", help="JSON matrix of cell values (e.g. '[[\"A\",\"B\"],[\"1\",\"2\"]]')")
    p_tb_add.add_argument("--no-header", action="store_true", help="Do not treat first row as header")
    p_tb_add.add_argument("--header-bg", help="Hex color for header background")
    p_tb_add.add_argument("--header-fg", help="Hex color for header text")
    p_tb_add.add_argument("--cell-fg", help="Hex color for body cell text")
    p_tb_add.add_argument("--font-size", type=float, help="Font size in points")

    # line
    p_ln = subparsers.add_parser("line", help="Line operations")
    ln_sub = p_ln.add_subparsers(dest="line_command")
    p_ln_add = ln_sub.add_parser("add", help="Add line")
    p_ln_add.add_argument("--slide", type=int, required=True, help="Slide number")
    p_ln_add.add_argument("--x1", type=int, required=True, help="Start X")
    p_ln_add.add_argument("--y1", type=int, required=True, help="Start Y")
    p_ln_add.add_argument("--x2", type=int, required=True, help="End X")
    p_ln_add.add_argument("--y2", type=int, required=True, help="End Y")

    # item
    p_itm = subparsers.add_parser("item", help="Item operations")
    itm_sub = p_itm.add_subparsers(dest="item_command")
    p_it_del = itm_sub.add_parser("delete", help="Delete item from slide")
    p_it_del.add_argument("--slide", type=int, required=True, help="Slide number")
    p_it_del.add_argument("--item", type=int, required=True, help="Item index")

    # export
    p_exp = subparsers.add_parser("export", help="Export presentation")
    p_exp.add_argument("--output", "-o", required=True, help="Output file or directory path")
    p_exp.add_argument("--format", "-f", default="pdf", choices=["pdf", "png", "jpeg", "pptx", "html"], help="Export format")
    p_exp.add_argument("--skipped", action="store_true", help="Include skipped slides")

    # render
    p_rend = subparsers.add_parser("render", help="Render slide images for inspection")
    p_rend.add_argument("--output-dir", "-o", help="Output directory")

    # build
    p_bld = subparsers.add_parser("build", help="Build presentation deck from specification")
    p_bld.add_argument("--spec", "-s", required=True, help="Path to JSON or YAML deck specification")

    # themes
    p_thm = subparsers.add_parser("themes", help="List available visual themes")
    p_thm.add_argument("--json", action="store_true", help="Output as JSON")

    # play
    p_ply = subparsers.add_parser("play", help="Control slideshow playback")
    p_ply.add_argument("action", choices=["start", "stop", "next", "prev"], default="start", nargs="?", help="Playback action")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "themes":
        cmd_themes(args, None)
        return

    client = KeynoteClient(doc_name=args.doc)
    if not client.is_running():
        print("Error: Keynote is not running. Please open Keynote or launch a presentation.")
        sys.exit(1)

    try:
        if args.command == "info":
            cmd_info(args, client)
        elif args.command == "slides":
            if args.slides_command == "list":
                cmd_slides_list(args, client)
            elif args.slides_command == "show":
                cmd_slides_show(args, client)
            elif args.slides_command == "get":
                cmd_slides_get(args, client)
            elif args.slides_command == "add":
                cmd_slides_add(args, client)
            elif args.slides_command == "duplicate":
                cmd_slides_duplicate(args, client)
            elif args.slides_command == "delete":
                cmd_slides_delete(args, client)
            elif args.slides_command == "move":
                cmd_slides_move(args, client)
            else:
                p_slides.print_help()
        elif args.command == "notes":
            if args.notes_command == "get":
                cmd_notes_get(args, client)
            elif args.notes_command == "set":
                cmd_notes_set(args, client)
            elif args.notes_command == "append":
                cmd_notes_append(args, client)
            else:
                p_notes.print_help()
        elif args.command == "text":
            if args.text_command == "find":
                cmd_text_find(args, client)
            elif args.text_command == "replace":
                cmd_text_replace(args, client)
            elif args.text_command == "add":
                cmd_text_add(args, client)
            else:
                p_text.print_help()
        elif args.command == "shape":
            if args.shape_command == "add":
                cmd_shape_add(args, client)
            else:
                p_shape.print_help()
        elif args.command == "image":
            if args.image_command == "add":
                cmd_image_add(args, client)
            else:
                p_image.print_help()
        elif args.command == "table":
            if args.table_command == "add":
                cmd_table_add(args, client)
            else:
                p_table.print_help()
        elif args.command == "line":
            if args.line_command == "add":
                cmd_line_add(args, client)
            else:
                p_ln.print_help()
        elif args.command == "item":
            if args.item_command == "delete":
                cmd_item_delete(args, client)
            else:
                p_itm.print_help()
        elif args.command == "export":
            cmd_export(args, client)
        elif args.command == "render":
            cmd_render(args, client)
        elif args.command == "build":
            cmd_build(args, client)
        elif args.command == "themes":
            cmd_themes(args, client)
        elif args.command == "play":
            cmd_play(args, client)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
