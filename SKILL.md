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

| Command | Shortcut Alias | Function |
|---|---|---|
| `pdf-to-keynote` | `keynote-convert` | Convert any PDF presentation to native `.key` and open in Keynote |
| `keynote-object-tool` | `keynote-detect` | Inspect objects by position, match shape fill color, and run healing brush |

### Usage Examples

```bash
# 1. Inspect native objects and spatial zones across all slides in active Keynote presentation
python3 ~/.gemini/config/skills/keynote-tools/scripts/keynote_object_detector.py --info --slides all

# 2. Extract background color beneath bottom-right shapes and adapt shape fill to mask it
python3 ~/.gemini/config/skills/keynote-tools/scripts/keynote_object_detector.py --match-shape-color --zone bottom-right --save-crops ./crops

# 3. Apply local Apple Vision + CoreImage healing brush to inpaint bottom-right rectangles across all slides
python3 ~/.gemini/config/skills/keynote-tools/scripts/keynote_object_detector.py --heal-underneath --zone bottom-right --slides all --save-crops ./crops

# 4. Clean bottom-right rectangles on specific slides (e.g. slides 2 through 10)
python3 ~/.gemini/config/skills/keynote-tools/scripts/keynote_object_detector.py --heal-underneath --zone bottom-right --slides 2-10

# 5. Process a standalone slide image or diagram directly using the healing brush
python3 ~/.gemini/config/skills/keynote-tools/scripts/keynote_object_detector.py --image slide_mockup.png --zone bottom-right --save-crops ./crops --output cleaned_slide.png
```

---

## 3. Architecture & Script References

- **Object Detector & Healing Suite**: `~/.gemini/config/skills/keynote-tools/scripts/keynote_object_detector.py`
- **Native Swift Vision & CoreImage Engine**: `~/.gemini/config/skills/keynote-tools/scripts/keynote_healer` (compiled from `keynote_healer.swift`)
- **Converter Engine**: `~/.gemini/config/skills/keynote-tools/scripts/pdf_to_keynote.py`
- **Slide Image Bridge**: `~/.gemini/config/skills/keynote-tools/scripts/slide_image_bridge.py`
- **macOS Requirements**: macOS with `/Applications/Keynote.app` installed, Swift compiler (`swift`), and standard `osascript`.

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
1. **Artifact/Text Detection**: Runs Apple Vision OCR (`VNRecognizeTextRequest`) to identify text and defect bounds.
2. **GPU-Accelerated Retouching**: Executes multi-pass CoreImage / Metal inpainting, combining 2D bilinear gradient reconstruction with the newly calculated noise variance (texture synthesis).
3. **Feathered Splicing**: Merges the textured healed crop back into the full slide canvas with anti-aliased edge feathering.
4. **Keynote Re-injection**: Injects the fully healed image back as the main background of the slide (replacing `image 1`).

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
