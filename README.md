# Apple Keynote Presentation Suite (`keynote-tools`)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)](https://apple.com)
[![Swift](https://img.shields.io/badge/Swift-5.9%2B-orange.svg)](https://swift.org)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)](https://python.org)
[![GitHub Repository](https://img.shields.io/badge/GitHub-studiohelioripple%2Fkeynote--tools-181717?logo=github)](https://github.com/studiohelioripple/keynote-tools)

A comprehensive suite and agent skill for programmatic **Apple Keynote** (`.key`) presentation automation, vector-fidelity PDF-to-Keynote conversion, spatial object detection across slides, background pixel sampling, shape background color matching, local **Apple Vision & CoreImage** healing brush retouching, and native slide synthesis on macOS.

---

## ✨ Key Capabilities

- 🎯 **Spatial Object Detection by Position**: Queries and detects native Keynote items (`shapes`, `text items`, `images`, `tables`) and slide graphic elements filtered by spatial quadrants or custom bounding boxes (`bottom-right`, `bottom-left`, `top-right`, `top-left`, `footer`, `header`, or custom rects).
- 🎨 **Shape Background Color Matching & Masking (`--match-shape-color`)**: Crops the exact slide image region underneath any target shape, extracts the true background color (and 2D gradient surface), and adapts the Keynote shape's fill color so it serves as a seamless masking overlay.
- 🖌️ **Local Apple Vision & CoreImage Healing Brush (`--heal-underneath`)**: Leverages local macOS `Vision` framework (OCR text & artifact detection) and GPU-accelerated `CoreImage` / `Metal` inpainting to repair and retouch underlying slide images in-place (Apple Photos Clean Up style).
- 📑 **Vector-Fidelity PDF to Keynote**: Converts multi-page PDF slide decks into native Keynote presentations with exact 1:1 aspect ratios, vector sharpness, and slide layout preservation (`pdf_to_keynote.py`).
- 🧩 **Native Unmerged Element Synthesis**: Deconstructs flat slides into unmerged, native Keynote elements—selectable text boxes, transparent PNG visual cutouts, background canvases, and dual-tone metric scale bars.
- 📐 **Semantic Layout Rearrangement**: Classifies and arranges content into structured typographic hierarchies:
  - **Category Eyebrows / Badges** (accent uppercase)
  - **Hero Metrics** (38–48 pt bold display figures)
  - **Section Leads** (editorial summaries)
  - **Structured Technical Details** (bulleted specifications with balanced leading)
  - **Dual-tone Scale Bars** (quantitative ratio indicators)
- 🎨 **Strict Palette Invariant & Box Minimization**: Eliminates clashing foreign white/black boxes. Elements and typography sit directly on the presentation's canonical gradient canvas.
- 👁️ **Embedded Infographic Preservation**: Intelligently distinguishes between editorial copy and internal diagram labels (inside 3D models, flowcharts, schematics), leaving graphical text intact without blurry inpainting.
- ⚡ **Hybrid AI Architecture**: Seamlessly routes fast OCR cleanup, bounding-box parsing, and structured data extraction to local Ollama models (`Qwen2.5-coder`, `moondream`), while cloud models guide narrative strategy.
- 🍏 **Robust AppleScript Bridge**: Programmatically inspects, inserts, duplicates, splits, cleans, and restyles slides via native macOS AppleScript events (`slide_image_bridge.py`, `keynote_object_detector.py`).

---

## 🛠️ CLI Utilities & Workflow Tools

| Tool | Language | Description |
|---|---|---|
| [`scripts/keynote_object_detector.py`](scripts/keynote_object_detector.py) | Python 3 | Spatial object detector, shape color matcher, and Apple Vision healing orchestrator. |
| [`scripts/keynote_healer.swift`](scripts/keynote_healer.swift) | Swift / Metal | Native Swift Apple Vision OCR & CoreImage GPU inpainting / background analysis engine. |
| [`scripts/pdf_to_keynote.py`](scripts/pdf_to_keynote.py) | Python / Swift | High-fidelity vector PDF to Keynote converter with auto-aspect ratio matching. |
| [`scripts/slide_image_bridge.py`](scripts/slide_image_bridge.py) | Python / AppleScript | Slide image extraction, multi-image splitting, and AppleScript automation bridge. |
| [`SKILL.md`](SKILL.md) | Markdown | Agentic skill definition, invariants, and comprehensive reference guide. |

---

## 🚀 Installation & Quick Start

### Prerequisites
- macOS 13+ with `/Applications/Keynote.app` installed
- Swift compiler (`swiftc`)
- Python 3.9+ with `Pillow` and `numpy`

### Compile Native Swift Engine
```bash
cd scripts
swiftc -O keynote_healer.swift -o keynote_healer
```

---

## 📖 Usage Examples

### 1. Spatial Object Inspection & Shape Color Masking
```bash
# Inspect all native objects and spatial quadrants on all slides
python3 scripts/keynote_object_detector.py --info --slides all

# Crop image under bottom-right shape, extract background color, and adapt shape fill
python3 scripts/keynote_object_detector.py --match-shape-color --zone bottom-right --save-crops ./crops
```

### 2. Apple Vision & CoreImage Healing Brush Retouching
```bash
# Heal bottom-right corner rectangles across all slides in active Keynote presentation
python3 scripts/keynote_object_detector.py --heal-underneath --zone bottom-right --slides all --save-crops ./crops

# Heal bottom-right rectangles on specific slides (e.g., slides 2 through 10)
python3 scripts/keynote_object_detector.py --heal-underneath --zone bottom-right --slides 2-10

# Process a standalone slide image directly
python3 scripts/keynote_object_detector.py --image slide_mockup.png --zone bottom-right --save-crops ./crops --output cleaned_slide.png
```

### 3. Convert PDF Slide Deck to Native Keynote
```bash
python3 scripts/pdf_to_keynote.py input_deck.pdf -o OutputDeck.key
```

### 4. Multi-Image Slide Splitting
Distribute slides with multiple image overlays into individual, clean sequential slides:
```bash
python3 scripts/slide_image_bridge.py split --doc "Presentation.key" --slide 15
```

---

## 📜 Invariant Design Principles

1. **Luminance-Opposing Contrast Invariant**: Text brightness strictly opposes background luminance ($Y = 0.299R + 0.587G + 0.114B$) for WCAG AA compliance.
2. **Prohibition of Artificial Box Containers**: Avoid arbitrary solid cards or foreign gray boxes; prioritize open canvas breathing room.
3. **Non-Destructive Graphic Inpainting**: Never erase internal labels from complex diagrams, flowcharts, or 3D renders. Extract whole RGBA assets and overlay editorial copy cleanly.

---

## 👤 Author & Links

- **Author**: studiohelioripple ([@studiohelioripple](https://github.com/studiohelioripple))
- **Repository**: [https://github.com/studiohelioripple/keynote-tools](https://github.com/studiohelioripple/keynote-tools)

---

## 📄 License

MIT License © 2026 [studiohelioripple](https://github.com/studiohelioripple).
