# Apple Keynote AppleScript & Automation Reference

This document provides a comprehensive technical reference for scripting and automating **Apple Keynote (`Keynote.app`)** on macOS via AppleScript, JXA, and Python.

---

## 1. Application & Document Model

### Targeting Active Document
```applescript
tell application "Keynote"
    set doc to front document
    set docName to name of doc
    set docWidth to width of doc
    set docHeight to height of doc
    set totalSlides to count of slides of doc
    set currentSlideNum to slide number of (current slide of doc)
end tell
```

### Switching Active Visible Slide
> [!IMPORTANT]
> To change the currently viewed slide, use `tell doc to set current slide to slide N`:
```applescript
tell application "Keynote"
    tell front document
        set current slide to slide 3
    end tell
end tell
```

---

## 2. Slide Operations

### Creating Slides
```applescript
tell application "Keynote"
    tell front document
        -- Add blank slide at end
        make new slide at end of slides with properties {base layout:slide layout "Blank"}
        
        -- Add slide after slide 2
        make new slide after slide 2 with properties {base layout:slide layout "Title & Bullets"}
    end tell
end tell
```

### Duplicating, Moving, and Deleting Slides
```applescript
tell application "Keynote"
    tell front document
        -- Duplicate slide 1 (creates duplicate directly after slide 1)
        duplicate slide 1
        
        -- Move slide 3 before slide 1
        move slide 3 to before slide 1
        
        -- Move slide 2 after slide 5
        move slide 2 to after slide 5
        
        -- Delete slide 4
        delete slide 4
    end tell
end tell
```

### Presenter Notes
```applescript
tell application "Keynote"
    tell front document
        -- Read notes
        set myNotes to presenter notes of slide 1
        
        -- Set notes
        set presenter notes of slide 1 to "Key speaking points for Q3 review."
        
        -- Append notes
        set curNotes to presenter notes of slide 1
        set presenter notes of slide 1 to curNotes & linefeed & "Additional talking point."
    end tell
end tell
```

---

## 3. Creating & Styling Slide Elements

### 16-Bit RGB Color Rule
> [!IMPORTANT]
> AppleScript iWork applications use **16-bit RGB tuples** (`0` to `65535`) instead of standard 8-bit (`0` to `255`).
> - Formula: `R_16 = int(R_8 * 65535 / 255)`
> - Pure White: `{65535, 65535, 65535}`
> - Pure Black: `{0, 0, 0}`
> - Royal Blue (`#2563eb`): `{9509, 25443, 60395}`
> - Electric Cyan (`#38bdf8`): `{14392, 48573, 63607}`

### Text Items (Text Boxes)
```applescript
tell application "Keynote"
    tell front document
        tell slide 1
            set tItem to make new text item with properties {object text:"Executive Summary", position:{100, 120}, width:800, height:60}
            tell object text of tItem
                set font to "SFProDisplay-Bold"
                set size to 36
                set color to {9509, 25443, 60395}
            end tell
        end tell
    end tell
end tell
```

### Shape Containers
```applescript
tell application "Keynote"
    tell front document
        tell slide 1
            set shp to make new shape with properties {position:{100, 200}, width:400, height:250, opacity:90}
            set object text of shp to "Card Description Text"
            set font of object text of shp to "SFProText-Regular"
            set size of object text of shp to 16
        end tell
    end tell
end tell
```

### Inserting Images
```applescript
tell application "Keynote"
    tell front document
        tell slide 1
            make new image with properties {file:POSIX file "/path/to/diagram.png", position:{100, 150}, width:600, height:400}
        end tell
    end tell
end tell
```

### Tables
```applescript
tell application "Keynote"
    tell front document
        tell slide 1
            set tbl to make new table with properties {row count:4, column count:3, position:{100, 200}, width:700, height:220, header row count:1}
            tell tbl
                -- Set headers
                set value of cell 1 of row 1 to "Feature"
                set value of cell 2 of row 1 to "Standard"
                set value of cell 3 of row 1 to "Enterprise"
                set background color of cell 1 of row 1 to {9509, 25443, 60395}
                set text color of cell 1 of row 1 to {65535, 65535, 65535}
                
                -- Set cell values
                set value of cell 1 of row 2 to "Local AI Acceleration"
                set value of cell 2 of row 2 to "Included"
                set value of cell 3 of row 2 to "Unlimited"
            end tell
        end tell
    end tell
end tell
```

### Connecting Lines
```applescript
tell application "Keynote"
    tell front document
        tell slide 1
            make new line with properties {start point:{100, 300}, end point:{800, 300}}
        end tell
    end tell
end tell
```

---

## 4. Exporting Presentations

```applescript
tell application "Keynote"
    set doc to front document
    
    -- Export to PDF
    export doc to POSIX file "/tmp/deck.pdf" as PDF with properties {skipped slides:false}
    
    -- Export to PNG slide images (folder of slides.001.png, ...)
    export doc to POSIX file "/tmp/slide_images" as slide images with properties {image format:PNG, skipped slides:false}
    
    -- Export to PowerPoint (.pptx)
    export doc to POSIX file "/tmp/deck.pptx" as Microsoft PowerPoint
    
    -- Export to HTML
    export doc to POSIX file "/tmp/html_export" as HTML
end tell
```

---

## 5. Slideshow Playback Control

```applescript
tell application "Keynote"
    -- Start presentation
    start front document
    
    -- Next build / slide
    show next
    
    -- Previous slide
    show previous
    
    -- Stop playback
    stop front document
end tell
```
