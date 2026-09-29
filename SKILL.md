---
name: keynote-tools
description: >-
  Apple Keynote (.key) presentation automation, vector-fidelity PDF-to-Keynote conversion,
  spatial object and rectangle detection across slides, background pixel and gradient sampling,
  color replacement/inpainting, local Apple Vision & CoreImage healing brush retouching,
  slide generation, and presentation management on macOS.
---

# Apple Keynote Presentation Suite (`keynote-tools`)

Unified automation and conversion toolkit for **Apple Keynote** (`.key`) on macOS. Enables programmatic presentation creation, PDF slide deck ingestion, spatial object detection by slide position, shape background color matching & masking, local Apple Vision & CoreImage healing brush retouching, vector asset embedding, and automated slide layout management.

---

## 1. Capabilities & Features

- **Declarative Multi-Slide Deck Builder**: Programmatically synthesizes complete Keynote decks from structured JSON/YAML specifications (`knt build --spec deck.json`), with automated layout synthesis for hero titles, section dividers, comparison cards, KPI metric grids, and code blocks.
- **8 Curated Visual Themes & Design Tokens**: Integrated theme engine (`knt themes`) offering 8 production-grade visual styles (`amil-light`, `amil-dark`, `terminal-dark`, `apple-light`, `apple-dark`, `nord-frost`, `cyberpunk-neon`, `editorial-serif`) with matched typography, semantic accents, and contrast invariants.
- **Unified Keynote CLI (`knt` / `keynote-tool`)**: Full command-line interface for active slide inspection, slide CRUD, text search/replace, speaker notes, and multi-format export (PDF, PNG, PPTX, HTML).
- **Spatial Object Detection by Position**: Queries and detects native Keynote items (shapes, text items, images) and slide graphic elements filtered by spatial quadrants or bounding boxes (`bottom-right`, `bottom-left`, `top-right`, `top-left`, `footer`, `header`, or custom rects).
- **Shape Background Color Matching & Masking (`--match-shape-color`)**: Crops the exact slide image region underneath any target shape, extracts the true background color (and 2D gradient surface), and adapts the Keynote shape's fill color so it serves as an invisible masking overlay.
- **Local Apple Vision & CoreImage Healing Brush (`--heal-underneath`)**: Leverages local macOS `Vision` (OCR text & artifact detection) and GPU-accelerated `CoreImage` / `Metal` inpainting to repair and retouch underlying slide images in-place (Apple Photos Clean Up style).
- **Perimeter Background Pixel & 2D Gradient Sampling**: Samples perimeter background pixels surrounding detected rectangles/badges, calculates 2D bilinear gradient surfaces ($R(x,y), G(x,y), B(x,y)$) or solid background colors, and seamlessly replaces object pixels without visible seams.
- **Vector-Fidelity PDF Conversion**: Converts multi-page presentation PDFs into native `.key` presentations while maintaining full vector crispness and resolution independence.
- **Exact Aspect Ratio & Canvas Preservation**: Automatically detects source PDF dimensions (e.g., 16:9 widescreen `1376x768`, `1920x1080`, 4:3 `1024x768`) and creates Keynote documents matched to the exact point bounds.
- **Native AppleScript & CoreGraphics Pipeline**: Uses Swift and PDFKit for rapid single-page extraction and AppleScript IPC to assemble, layout, inspect, and save native Keynote documents.
- **Automatic Keynote Project Generation & Re-injection**: Directly modifies and updates active Keynote documents in-place, or generates standalone presentations.

---

## 2. CLI Commands & Shortcuts

Installed in `~/.local/bin`:

| Command Category | Command | Description |
|---|---|---|
| **Deck Builder** | `knt build --spec <spec.json>` | Build multi-slide presentation deck from JSON/YAML spec |
| **Themes** | `knt themes [--json]` | List 8 curated visual design themes and palette tokens |
| **Document Info** | `knt info [--json]` | Inspect active presentation name, dimensions, slides, and master layouts |
| **Slides List** | `knt slides list [--json]` | List all slides with layout name, items count, and notes preview |
| **Slide Details** | `knt slides get <n> [--json]` | Deep inspect slide items (shapes, text, tables, images, notes) |
| **Text Operations** | `knt text find "query"` / `replace "old" "new"` | Search and replace text across all slides or on a specific slide |
| **Speaker Notes** | `knt notes get <n>` / `set <n> --text "..."` | Read or update presenter notes |
| **Export Deck** | `knt export --format <pdf\|png\|pptx\|html> -o <path>` | Export presentation to file or image folder |
| **PDF Conversion** | `pdf-to-keynote <input.pdf> -o <output.key>` | Convert PDF presentation to native `.key` |
| **Object Detection** | `keynote-object-tool --zone bottom-right` | Inspect objects by position, match shape fill, and run healing brush |

### Usage Examples

```bash
# 1. List curated design themes
knt themes

# 2. Programmatically generate a complete slide deck from specification
knt build --spec references/TEMPLATES.md

# 3. Inspect active Keynote document and slide hierarchy
knt info
knt slides list

# 4. Search and replace text across the entire presentation
knt text replace "Old Company" "New Venture"

# 5. Export presentation to PDF or slide images
knt export -o ./output.pdf --format pdf
knt render -o ./slide_previews/

# 6. Inspect native objects and spatial zones across all slides
python3 scripts/keynote_object_detector.py --info --slides all

# 7. Extract background color beneath bottom-right shapes and adapt shape fill
python3 scripts/keynote_object_detector.py --match-shape-color --zone bottom-right --save-crops ./crops

# 8. Apply local Apple Vision + CoreImage healing brush to inpaint bottom-right rectangles
python3 scripts/keynote_object_detector.py --heal-underneath --zone bottom-right --slides all --save-crops ./crops

# 9. Convert vector PDF slide deck to native Keynote
python3 scripts/pdf_to_keynote.py input_deck.pdf -o OutputDeck.key
```

---

## 3. Architecture & Script References

- **Unified CLI (`knt` / `keynote-tool`)**: `scripts/keynote_tool.py`
- **Declarative Deck Builder**: `scripts/deck_builder.py`
- **Curated Theme Engine**: `scripts/theme_engine.py`
- **AppleScript Client & Automation Engine**: `scripts/keynote_client.py`
- **Object Detector & Healing Suite**: `scripts/keynote_object_detector.py`
- **Native Swift Vision & CoreImage Engine**: `scripts/keynote_healer` (compiled from `keynote_healer.swift`)
- **PDF-to-Keynote Converter**: `scripts/pdf_to_keynote.py`
- **Slide Image Bridge**: `scripts/slide_image_bridge.py`
- **Reference Guides**:
  - `references/PALETTES.md`: Design tokens, palettes, and typography pairings.
  - `references/TEMPLATES.md`: Declarative slide template specifications.
  - `references/APPLESCRIPT_REFERENCE.md`: Complete Keynote AppleScript dictionary.
- **macOS Requirements**: macOS with `/Applications/Keynote.app` installed, Swift compiler (`swiftc`), and standard `osascript`.

---

## 4. Apple Vision Masking & Texture-Synthesized Healing Pipeline

When slides contain unwanted badges, buttons, watermarks, or rectangles in specific positions (e.g., bottom-right corner), masking them requires bypassing native Keynote AppleScript limitations and matching background texture accurately.

**CRITICAL APPLESCRIPT INVARIANT:**
Keynote's AppleScript dictionary does **not** allow directly setting `fill`, `color`, or `stroke` properties on native `shape` objects. GUI scripting for these properties often fails due to strict macOS Accessibility sandboxing. 
**Solution:** To perfectly mask areas without ugly default borders, either inject a generated `.png` patch as a borderless `image` object (`make new image with properties {file: ...}`), or directly inpaint the main background image (`direct-inpaint`).

### Mode A: Synthesized Texture-Aware Patch Injection (`clean-image`)
1. **Sub-Image Crop**: Crops the exact bounding region of the slide image.
2. **Perimeter Detrending & Texture Estimation**: Samples outer boundary pixels. Solves least squares for 2D surface gradient equations:
   $$R(x, y) = a_r x + b_r y + c_r,\quad G(x, y) = a_g x + b_g y + c_g,\quad B(x, y) = a_b x + b_b y + c_b$$
   Calculates the variance of the residuals to estimate the actual high-frequency noise (grain/texture) of the slide background.
3. **Patch Generation**: Synthesizes a pure patch combining the 2D gradient and uniform random noise matched exactly to the residual variance.
4. **Keynote Injection**: Injects this patch into Keynote as an `image` object that overlays the unwanted content seamlessly.

### Mode B: Direct Background Inpainting (`direct-inpaint` / `--heal`)
1. **Apple Vision Tight Segmentation**: Shells out to the `apple-watermark-cleaner` skill, utilizing `VNRecognizeTextRequest` and localized background delta thresholding to strictly segment ink strokes.
2. **Navier-Stokes AI Inpainting**: Runs OpenCV Fast Marching (Telea) / Navier-Stokes background inpainting over the slide image to flawlessly reconstruct the canvas texture.
3. **Keynote Re-injection**: Injects the fully healed image back as the main background of the slide (replacing `image 1`).

### Mode C: Solid Color Rectangle Simulation (`solid-shape`)
1. **Dominant Color Extraction**: Samples the dominant background color of the perimeter region.
2. **Solid PNG Generation**: Generates a flat, solid-colored PNG patch (e.g. 100% `#FFFFFF`) dynamically.
3. **Rectangle Simulation Injection**: Injects this PNG as an `image` object over the target zone. This perfectly simulates inserting a borderless native `shape` rectangle colored exactly like the local solid background, cleanly bypassing the AppleScript `shape fill` limitation.
4. **Layout Edge Extension (`--extend-to-edge` / `--extend-right`)**: Extends the mask boundary horizontally to the absolute edge of the slide canvas (`width = canvas_w - x`), ensuring zero gap between the mask and the slide border.

---

## 5. In-Place Image/PDF Slide Editing & Re-injection Pipeline

When slides are imported as vector PDFs or flat images (e.g. from Canva, Figma, or `pdf-to-keynote`):

1. **Information & Extraction**:
   - Query Keynote front document, current slide, and canvas bounds:
     ```bash
     python3 ~/.gemini/config/skills/keynote-tools/scripts/slide_image_bridge.py --info
     ```
   - Extract the slide's backing asset from `.key` package (`Data/page_X.pdf` or `Data/page_X.png`) or render via `qlmanage -t -s 2048`.

2. **Text Detection & Layer Inpainting**:
   - Run Apple Vision OCR: `apple-vision ocr <slide.png> --pretty`.
   - Inpaint target text areas using `image-text-replacer` / `apple-layer-separator` (Otsu adaptive thresholding + OpenCV Telea inpainting) to regenerate clean background without artifacts.

3. **Typography Composition**:
   - Re-render the user-specified replacement text matching system fonts, sizes, weights, and alignment onto the reconstructed background.

4. **In-Place Re-injection & Save**:
   - Re-inject the updated high-resolution graphic into Keynote and save in-place:
     ```bash
     python3 ~/.gemini/config/skills/keynote-tools/scripts/slide_image_bridge.py --reinject "/path/to/updated_slide.png"
     ```

---

## 6. Multi-Image Slide Splitting & Distribution (AppleScript Pattern)

Keynote's AppleScript dictionary does not permit direct `duplicate image` or `move image to new slide` calls (throws error: `Images can not be copied. (-10000)`).

To reliably distribute multiple stacked or clustered images from one slide across individual slides while preserving exact canvas positions, dimensions, and styling:

1. **Slide Duplication Strategy**:
   - Duplicate the multi-image slide $N - 1$ times to create $N$ identical slides.
   - For each slide, retain one targeted image and delete the other $N - 1$ images in reverse index order.

2. **AppleScript Recipe**:
```applescript
tell application "Keynote"
    tell front document
        -- Target slide (e.g., last slide)
        set sIdx to count of slides
        set origSlide to slide sIdx
        set numImgs to count of images of origSlide
        
        -- Duplicate origSlide (numImgs - 1) times
        repeat (numImgs - 1) times
            duplicate origSlide
        end repeat
        
        -- Now slides sIdx through (sIdx + numImgs - 1) each contain all images.
        -- For each slide, delete every image except the target image (in reverse order).
        set firstNewSlide to sIdx
        repeat with i from 1 to numImgs
            set currSlide to slide (firstNewSlide + i - 1)
            repeat with j from numImgs to 1 by -1
                if j is not i then
                    delete (image j of currSlide)
                end if
            end repeat
        end repeat
    end tell
end tell
```

---

## 7. Contrast Invariance, Thematic Typography & Local AI Integration

When programmatically reconstructing or generating native Keynote slides:

1. **Luminance-Opposing Contrast Invariant (WCAG AA)**:
   - Text color brightness MUST oppose background/panel luminance:
     $$\text{Luminance } Y = 0.299\,R + 0.587\,G + 0.114\,B$$
   - Light translucent panels ($Y > 140$): Use Deep Obsidian Charcoal text (`{2500, 3000, 4500}`).
   - Dark frosted panels ($Y < 120$): Use Crisp Pale Platinum text (`{62000, 63000, 65535}`).
   - Keynote 16-bit RGB values range from `0` to `65535`.

2. **Thematic Editorial Typography Hierarchy**:
   - **Slide Header**: 24–28 pt, `Helvetica-Bold`, Deep Slate/Navy accent (`{4000, 5000, 7000}`).
   - **Category Eyebrow / Badges**: 10–11 pt, uppercase, bold tracking, themed accent (`{2000, 28000, 52000}`).
   - **Card / Section Titles**: 16–18 pt, `Helvetica-Bold`, high-contrast solid (`{2000, 2500, 3500}`).
   - **Hero Metric Callouts**: 38–48 pt bold display numbers (e.g. `60%`, `20%`, `< 50 KB`).
   - **Body Paragraphs**: 11–13 pt, regular weight, structured leading with clear line breaks.

3. **Local AI Model Delegation (`local-model-bridge`)**:
   - Always prioritize local Ollama models (`Qwen2.5-coder:latest` or `moondream:latest` at `http://localhost:11434/api/generate`) for extracting structured editorial hierarchy, bullet synthesis, and metric identification offline before passing parameters to AppleScript.

---

## 8. Hybrid AI Architecture, Semantic Layout Rearrangement & Palette Invariant

1. **Hybrid AI Delegation (Local $\leftrightarrow$ Cloud)**:
   - **Local Layer** (`local-model-bridge`): Handles data privacy, layout extraction, bounding-box parsing, and fast structured JSON generation via local Ollama models (`Qwen2.5-coder`, `moondream`).
   - **Cloud Layer**: Orchestrates complex multi-modal design strategy, high-level narrative alignment, and multi-file automation.

2. **Semantic Layout Rearrangement**:
   - Semantically categorize content into Eyebrows / Badges, Hero Metrics, Section Leads, Structured Details, and Dual-tone Scale Bars.

3. **Strict Palette Invariant & Box Minimization**:
   - **Prohibition of Foreign Containers**: Never insert arbitrary white boxes, harsh black cards, or unrelated grays that clash with the presentation.
   - **Canvas Breathing Room**: Allow visual cutouts and typography to sit directly on the canonical presentation gradient canvas.
   - **Palette Sampling**: Sample background and accent RGB values directly from reference slides (`1–14`) before generating new slides.

---

## 9. Infographical Graphic Preservation & Non-Destructive Text Invariant

1. **Differentiating Editorial Text vs. Embedded Infographic Labels**:
   - The skill MUST classify detected text elements into:
     - **Editorial & Body Text**: Synthesized as native, editable Keynote text items.
     - **Embedded Infographical Text**: Preserved inside graphics/diagrams without destructive wiping.

2. **Non-Destructive Inpainting & Extraction Protocol**:
   - **Strict Preservation**: NEVER attempt to inpaint, erase, or recreate embedded infographic text as generic slide text boxes.
   - **Selective Background Inpainting**: Only inpaint regions identified as editorial slide copy or targeted corner badges/watermark rectangles.
