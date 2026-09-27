# Apple Keynote Tools & Automation Suite (`keynote-tools`)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)](https://apple.com)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)](https://python.org)

A comprehensive suite and agent skill for programmatic Apple Keynote (`.key`) presentation automation, vector-fidelity PDF-to-Keynote conversion, native slide synthesis, typographic standardization, and hybrid AI slide re-engineering on macOS.

---

## ✨ Key Capabilities

- 📑 **Vector-Fidelity PDF to Keynote**: Convert multi-page PDF slide decks into native Keynote presentations with 1:1 aspect ratios, vector sharpness, and slide layout preservation (`pdf_to_keynote.py`).
- 🧩 **Native Unmerged Element Synthesis**: Deconstruct flat slides into unmerged, native Keynote elements—selectable text boxes, transparent PNG visual cutouts, background canvases, and dual-tone metric scale bars.
- 📐 **Semantic Layout Rearrangement**: Classify and arrange content into structured typographic hierarchies:
  - **Category Eyebrows / Badges** (accent uppercase)
  - **Hero Metrics** (38–48 pt bold display figures)
  - **Section Leads** (editorial summaries)
  - **Structured Technical Details** (bulleted specifications with balanced leading)
  - **Dual-tone Scale Bars** (quantitative ratio indicators)
- 🎨 **Strict Palette Invariant & Box Minimization**: Eliminate clashing foreign white/black boxes. Elements and typography breathe directly on the presentation's canonical gradient canvas, sampled from master slides.
- 👁️ **Embedded Infographic Preservation**: Intelligently distinguish between editorial copy and internal diagram labels (inside 3D models, flowcharts, machinery schematics), leaving graphical text intact without blurry inpainting.
- ⚡ **Hybrid AI Architecture**: Seamlessly route fast OCR cleanup, bounding-box parsing, and structured data extraction to local Ollama models (`Qwen2.5-coder`, `moondream`), while cloud models guide narrative strategy.
- 🍏 **Robust AppleScript Bridge**: Programmatically inspect, insert, duplicate, split, and restyle slides via native macOS AppleScript events (`slide_image_bridge.py`).

---

## 🛠️ CLI Utilities & Workflow Tools

| Tool | Description |
|---|---|
| [`scripts/pdf_to_keynote.py`](scripts/pdf_to_keynote.py) | High-fidelity vector PDF to Keynote converter with auto-aspect ratio matching. |
| [`scripts/slide_image_bridge.py`](scripts/slide_image_bridge.py) | Slide image extraction, multi-image splitting, and AppleScript automation bridge. |
| [`SKILL.md`](SKILL.md) | Agentic skill definition, invariants, and comprehensive AppleScript/Python reference guide. |

---

## 🚀 Usage Examples

### 1. Convert PDF Slide Deck to Native Keynote
```bash
python3 scripts/pdf_to_keynote.py input_deck.pdf -o OutputDeck.key
```

### 2. Multi-Image Slide Splitting
Distribute slides with multiple image overlays into individual, clean sequential slides:
```bash
python3 scripts/slide_image_bridge.py split --doc "Presentation.key" --slide 15
```

### 3. Native Slide Rebuilding via AppleScript
```applescript
tell application "Keynote"
    tell front document
        set newSlide to make new slide with properties {base slide:slide 1}
        tell newSlide
            set bg to make new image with properties {file:POSIX file "/path/to/gradient_bg.png"}
            set cutout to make new image with properties {file:POSIX file "/path/to/diagram_rgba.png"}
            set txt to make new text item with properties {object text:"HERO METRIC 60%", position:{80, 120}}
        end tell
    end tell
end tell
```

---

## 📜 Invariant Design Principles

1. **Luminance-Opposing Contrast Invariant**: Text brightness strictly opposes background luminance ($Y = 0.299R + 0.587G + 0.114B$) for WCAG AA compliance.
2. **Prohibition of Artificial Box Containers**: Avoid arbitrary solid cards or foreign gray boxes; prioritize open canvas breathing room.
3. **Non-Destructive Graphic Inpainting**: Never erase internal labels from complex diagrams, flowcharts, or 3D renders. Extract whole RGBA assets and overlay editorial copy cleanly.

---

## 📄 License

MIT License © 2026 [studiohelioripple](https://github.com/studiohelioripple).
