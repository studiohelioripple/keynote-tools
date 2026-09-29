#!/usr/bin/env python3
"""
Theme Engine and Visual Palette Manager for Keynote Presentations.
Provides curated design palettes, typography pairings, component styling tokens,
and automatic formatting rules.
"""

from typing import Dict, Any, List, Optional

THEMES: Dict[str, Dict[str, Any]] = {
    "amil-light": {
        "name": "Amil Design Light",
        "mode": "light",
        "canvas_bg": "#f8fafc",
        "card_bg": "#ffffff",
        "card_border": "#e2e8f0",
        "text_primary": "#0f172a",
        "text_secondary": "#475569",
        "text_muted": "#94a3b8",
        "accent": "#2563eb",
        "accent_secondary": "#0284c7",
        "success": "#10b981",
        "warning": "#f59e0b",
        "font_title": "SF Pro Display",
        "font_body": "SF Pro Text",
        "font_mono": "SF Mono",
    },
    "amil-dark": {
        "name": "Amil Design Dark",
        "mode": "dark",
        "canvas_bg": "#0b0f19",
        "card_bg": "#131b2e",
        "card_border": "#1e293b",
        "text_primary": "#f8fafc",
        "text_secondary": "#94a3b8",
        "text_muted": "#64748b",
        "accent": "#38bdf8",
        "accent_secondary": "#818cf8",
        "success": "#34d399",
        "warning": "#fbbf24",
        "font_title": "SF Pro Display",
        "font_body": "SF Pro Text",
        "font_mono": "SF Mono",
    },
    "terminal-dark": {
        "name": "Terminal Slate & Amber",
        "mode": "dark",
        "canvas_bg": "#10161f",
        "card_bg": "#182230",
        "card_border": "#26354a",
        "text_primary": "#f1f5f9",
        "text_secondary": "#94a3b8",
        "text_muted": "#64748b",
        "accent": "#38bdf8",
        "accent_secondary": "#f59e0b",
        "success": "#10b981",
        "warning": "#f59e0b",
        "font_title": "SF Mono",
        "font_body": "SF Pro Text",
        "font_mono": "SF Mono",
    },
    "apple-light": {
        "name": "Apple Cupertino Light",
        "mode": "light",
        "canvas_bg": "#ffffff",
        "card_bg": "#f5f5f7",
        "card_border": "#d2d2d7",
        "text_primary": "#1d1d1f",
        "text_secondary": "#6e6e73",
        "text_muted": "#86868b",
        "accent": "#0071e3",
        "accent_secondary": "#5e5ce6",
        "success": "#34c759",
        "warning": "#ff9500",
        "font_title": "SF Pro Display",
        "font_body": "SF Pro Text",
        "font_mono": "SF Mono",
    },
    "apple-dark": {
        "name": "Apple Space Black",
        "mode": "dark",
        "canvas_bg": "#000000",
        "card_bg": "#1c1c1e",
        "card_border": "#2c2c2e",
        "text_primary": "#f5f5f7",
        "text_secondary": "#a1a1a6",
        "text_muted": "#636366",
        "accent": "#2997ff",
        "accent_secondary": "#bf5af2",
        "success": "#30d158",
        "warning": "#ffd60a",
        "font_title": "SF Pro Display",
        "font_body": "SF Pro Text",
        "font_mono": "SF Mono",
    },
    "nord-frost": {
        "name": "Nord Frost",
        "mode": "dark",
        "canvas_bg": "#242933",
        "card_bg": "#2e3440",
        "card_border": "#3b4252",
        "text_primary": "#eceff4",
        "text_secondary": "#d8dee9",
        "text_muted": "#4c566a",
        "accent": "#88c0d0",
        "accent_secondary": "#81a1c1",
        "success": "#a3be8c",
        "warning": "#ebcb8b",
        "font_title": "SF Pro Display",
        "font_body": "SF Pro Text",
        "font_mono": "Menlo",
    },
    "cyberpunk-neon": {
        "name": "Cyberpunk Neon",
        "mode": "dark",
        "canvas_bg": "#090a0f",
        "card_bg": "#12131f",
        "card_border": "#27273a",
        "text_primary": "#ffffff",
        "text_secondary": "#cbd5e1",
        "text_muted": "#64748b",
        "accent": "#f43f5e",
        "accent_secondary": "#facc15",
        "success": "#06b6d4",
        "warning": "#f59e0b",
        "font_title": "SF Pro Display",
        "font_body": "SF Pro Text",
        "font_mono": "SF Mono",
    },
    "editorial-serif": {
        "name": "Editorial Serif",
        "mode": "light",
        "canvas_bg": "#f7f4ed",
        "card_bg": "#ffffff",
        "card_border": "#e7e2d7",
        "text_primary": "#26211e",
        "text_secondary": "#574e47",
        "text_muted": "#8c827a",
        "accent": "#9b111e",
        "accent_secondary": "#b45309",
        "success": "#15803d",
        "warning": "#d97706",
        "font_title": "New York",
        "font_body": "Georgia",
        "font_mono": "Courier",
    }
}

THEME_ALIASES = {
    "light": "amil-light",
    "amil": "amil-light",
    "default": "amil-light",
    "dark": "amil-dark",
    "terminal": "terminal-dark",
    "cli": "terminal-dark",
    "apple": "apple-light",
    "cupertino": "apple-light",
    "space-black": "apple-dark",
    "space-dark": "apple-dark",
    "nord": "nord-frost",
    "cyberpunk": "cyberpunk-neon",
    "editorial": "editorial-serif",
    "serif": "editorial-serif",
}


def get_theme(theme_name: str = "amil-light") -> Dict[str, Any]:
    """Resolve theme configuration by name or alias."""
    name_clean = theme_name.lower().strip()
    resolved_id = THEME_ALIASES.get(name_clean, name_clean)
    return THEMES.get(resolved_id, THEMES["amil-light"])


def list_available_themes() -> List[Dict[str, str]]:
    """Return summary list of all available themes."""
    return [
        {
            "id": k,
            "name": v["name"],
            "mode": v["mode"],
            "accent": v["accent"],
            "canvas_bg": v["canvas_bg"],
        }
        for k, v in THEMES.items()
    ]


if __name__ == "__main__":
    import json
    print(json.dumps(list_available_themes(), indent=2))
