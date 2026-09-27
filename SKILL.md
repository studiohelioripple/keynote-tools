---
name: keynote-tools
description: >-
  Apple Keynote (.key) presentation automation, vector-fidelity PDF-to-Keynote conversion,
  slide generation, and presentation management on macOS. Converts multi-page PDF slide decks
  into native Keynote projects with exact 1:1 aspect ratios, vector crispness, and full editing support.
---

# Apple Keynote Presentation Suite (`keynote-tools`)

Unified automation and conversion toolkit for **Apple Keynote** (`.key`) on macOS. Enables programmatic presentation creation, PDF slide deck ingestion, vector asset embedding, and automated slide layout management.

---

## 1. Capabilities & Features

- **Vector-Fidelity PDF Conversion**: Converts multi-page presentation PDFs into native `.key` presentations while maintaining full vector crispness and resolution independence.
- **Exact Aspect Ratio & Canvas Preservation**: Automatically detects source PDF dimensions (e.g., 16:9 widescreen `1376x768`, `1920x1080`, 4:3 `1024x768`) and creates Keynote documents matched to the exact point bounds.
- **Native AppleScript & CoreGraphics Pipeline**: Uses Swift and PDFKit for rapid single-page extraction and AppleScript IPC to assemble, layout, and save native Keynote documents.
- **Automatic Keynote Project Generation**: Saves native `.key` bundle files and directly brings Keynote to the foreground with the project open and ready for presentation or editing.

---

## 2. CLI Commands & Shortcuts

Installed in `~/.local/bin`:

| Command | Shortcut Alias | Function |
|---|---|---|
| `pdf-to-keynote` | `keynote-convert` | Convert any PDF presentation to native `.key` and open in Keynote |

### Usage Examples

```bash
# Convert a PDF presentation to a Keynote project in the same directory and open it
pdf-to-keynote presentation.pdf

# Specify custom output path
pdf-to-keynote presentation.pdf -o ~/Documents/CustomPresentation.key

# Convert in background without opening Keynote
pdf-to-keynote presentation.pdf --no-open
```

---

## 3. Architecture & Script References

- **Converter Engine**: `~/.gemini/config/skills/keynote-tools/scripts/pdf_to_keynote.py`
- **Slide Image Bridge**: `~/.gemini/config/skills/keynote-tools/scripts/slide_image_bridge.py`
- **CLI Symlinks**: `~/.local/bin/pdf-to-keynote`, `~/.local/bin/keynote-convert`
- **macOS Requirements**: macOS with `/Applications/Keynote.app` installed, Swift compiler (`swift`), and standard `osascript`.

---

## 4. In-Place Image/PDF Slide Editing & Re-injection Pipeline

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

## 5. Multi-Image Slide Splitting & Distribution (AppleScript Pattern)

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

## 6. Contrast Invariance, Thematic Typography & Local AI Integration

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

## 7. Hybrid AI Architecture, Semantic Layout Rearrangement & Palette Invariant

1. **Hybrid AI Delegation (Local $\leftrightarrow$ Cloud)**:
   - **Local Layer** (`local-model-bridge`): Handles data privacy, layout extraction, bounding-box parsing, and fast structured JSON generation via local Ollama models (`Qwen2.5-coder`, `moondream`).
   - **Cloud Layer**: Orchestrates complex multi-modal design strategy, high-level narrative alignment, and multi-file automation.
   - Dynamic routing checks local availability first and seamlessly falls back to cloud models when advanced reasoning or unquantized visual understanding is required.

2. **Semantic Layout Rearrangement**:
   - Rather than dumping raw OCR text into arbitrary shapes, semantically categorize content into:
     - **Eyebrows / Badges**: Category/phase tags (`10–11pt Helvetica-Bold` in accent color).
     - **Hero Metrics**: Standalone quantitative figures (`38–48pt Helvetica-Bold`, e.g. `60%`, `< 50 KB`).
     - **Section Leads**: 1–2 sentence narrative summaries (`15–17pt Helvetica-Bold`).
     - **Structured Details**: Bulleted technical specifications (`12–13pt Helvetica` with disciplined leading).
     - **Dual-tone Scale Bars**: Quantitative ratio indicators visualizing performance differentials.
   - Rearrange elements spatial flow (Architecture $\rightarrow$ Pipeline $\rightarrow$ Ecosystem) for optimal visual narrative.

3. **Strict Palette Invariant & Box Minimization**:
   - **Prohibition of Foreign Containers**: Never insert arbitrary white boxes, harsh black cards, or unrelated grays that clash with the presentation.
   - **Canvas Breathing Room**: Allow visual cutouts (3D models, machines, diagrams) and typography to sit directly on the canonical presentation gradient canvas, matching the natural editorial aesthetic of master slides.
   - **Palette Sampling**: Sample background and accent RGB values directly from reference slides (`1–14`) before generating new slides.

---

## 8. Infographical Graphic Preservation & Non-Destructive Text Invariant

1. **Differentiating Editorial Text vs. Embedded Infographic Labels**:
   - Presentations and slide decks frequently contain architectural models, 3D renderings, flow diagrams, schematics, and UI mockups where text is an integral component of the visual asset (e.g. node labels in workflow graphs, measurement callouts on 3D isometric building blocks, badges inside diagrams, component callout arrows).
   - The skill MUST classify detected text elements into two strict categories:
     - **Editorial & Body Text**: Slide headers, section subtitles, paragraph descriptions, metric callouts, and bullet lists. These must be synthesized as native, editable, selectable Keynote text items.
     - **Embedded Infographical Text**: Labels, numbers, and captions situated inside or directly attached to visual graphics, 3D renders, or flowcharts.

2. **Non-Destructive Inpainting & Extraction Protocol**:
   - **Strict Preservation**: NEVER attempt to inpaint, erase, or recreate embedded infographic text as generic slide text boxes. Erasing them destroys vector lines, leader arrows, and graphic integrity, while recreating them produces misaligned typography.
   - **Selective Background Inpainting**: When cleaning slide canvases, only inpaint regions identified as editorial slide copy.
   - **Whole-Graphic RGBA Cutouts**: Extract diagrams, schematics, and 3D illustrations as complete, transparent RGBA PNG assets with their internal text, icons, and annotations fully preserved.
   - **Native Overlay Separation**: Native Keynote text items should only accompany the graphic as external narrative headers, summary captions, or side-by-side analytical copy.


