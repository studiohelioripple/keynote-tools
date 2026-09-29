#!/usr/bin/env python3
"""
Declarative Presentation Deck Builder for Apple Keynote.
Constructs high-fidelity slides and component layouts programmatically
based on structured JSON/YAML specs and theme tokens.
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional

from keynote_client import KeynoteClient
from theme_engine import get_theme


class DeckBuilder:
    """Builds structured presentation slides into an active Keynote presentation."""

    def __init__(self, client: Optional[KeynoteClient] = None, theme_name: str = "amil-light"):
        self.client = client or KeynoteClient()
        self.theme = get_theme(theme_name)
        self.doc_info = self.client.get_doc_info()
        self.doc_w = self.doc_info["width"]
        self.doc_h = self.doc_info["height"]

    def set_theme(self, theme_name: str):
        self.theme = get_theme(theme_name)

    def _get_blank_layout(self) -> str:
        layouts = self.doc_info.get("layouts", [])
        for candidate in ["Blank", "Empty", "Title Only", "Title Slide"]:
            if candidate in layouts:
                return candidate
        return layouts[0] if layouts else "Blank"

    def build_title_slide(
        self,
        title: str,
        subtitle: Optional[str] = None,
        tag: Optional[str] = None,
        footer: Optional[str] = None,
        notes: Optional[str] = None,
        after_slide: Optional[int] = None,
    ) -> int:
        """Create a hero title slide."""
        s_idx = self.client.add_slide(layout=self._get_blank_layout(), after_slide=after_slide)
        
        # Tag badge
        y_cursor = int(self.doc_h * 0.28)
        if tag:
            tag_w = min(400, max(120, len(tag) * 14 + 30))
            self.client.add_text_item(
                slide_index=s_idx,
                text=tag.upper(),
                x=int(self.doc_w * 0.08),
                y=y_cursor,
                width=tag_w,
                height=36,
                font=f"{self.theme['font_mono']}-Bold",
                size=14,
                color=self.theme["accent"],
            )
            y_cursor += 45

        # Main Title
        title_size = 54 if self.doc_w >= 1920 else (44 if self.doc_w >= 1280 else 36)
        self.client.add_text_item(
            slide_index=s_idx,
            text=title,
            x=int(self.doc_w * 0.08),
            y=y_cursor,
            width=int(self.doc_w * 0.84),
            height=int(self.doc_h * 0.3),
            font=f"{self.theme['font_title']}-Bold",
            size=title_size,
            color=self.theme["text_primary"],
        )

        # Subtitle
        if subtitle:
            sub_y = y_cursor + int(title_size * 2.2)
            sub_size = 24 if self.doc_w >= 1920 else 20
            self.client.add_text_item(
                slide_index=s_idx,
                text=subtitle,
                x=int(self.doc_w * 0.08),
                y=sub_y,
                width=int(self.doc_w * 0.84),
                height=int(self.doc_h * 0.2),
                font=self.theme["font_body"],
                size=sub_size,
                color=self.theme["text_secondary"],
            )

        # Footer
        if footer:
            self.client.add_text_item(
                slide_index=s_idx,
                text=footer,
                x=int(self.doc_w * 0.08),
                y=int(self.doc_h * 0.88),
                width=int(self.doc_w * 0.84),
                height=30,
                font=self.theme["font_body"],
                size=14,
                color=self.theme["text_muted"],
            )

        if notes:
            self.client.set_presenter_notes(s_idx, notes)

        return s_idx

    def _render_header(self, slide_index: int, title: str, subtitle: Optional[str] = None):
        """Render standard slide header."""
        margin_x = int(self.doc_w * 0.06)
        margin_y = int(self.doc_h * 0.06)
        title_size = 36 if self.doc_w >= 1920 else 28

        self.client.add_text_item(
            slide_index=slide_index,
            text=title,
            x=margin_x,
            y=margin_y,
            width=int(self.doc_w * 0.88),
            height=50,
            font=f"{self.theme['font_title']}-Bold",
            size=title_size,
            color=self.theme["text_primary"],
        )

        if subtitle:
            self.client.add_text_item(
                slide_index=slide_index,
                text=subtitle,
                x=margin_x,
                y=margin_y + 48,
                width=int(self.doc_w * 0.88),
                height=35,
                font=self.theme["font_body"],
                size=16,
                color=self.theme["text_secondary"],
            )

    def build_card_content_slide(
        self,
        title: str,
        content: str,
        subtitle: Optional[str] = None,
        notes: Optional[str] = None,
        after_slide: Optional[int] = None,
    ) -> int:
        """Create a slide with header and content card."""
        s_idx = self.client.add_slide(layout=self._get_blank_layout(), after_slide=after_slide)
        self._render_header(s_idx, title, subtitle)

        margin_x = int(self.doc_w * 0.06)
        card_y = int(self.doc_h * 0.22)
        card_w = int(self.doc_w * 0.88)
        card_h = int(self.doc_h * 0.70)

        # Card container
        self.client.add_shape(
            slide_index=s_idx,
            x=margin_x,
            y=card_y,
            width=card_w,
            height=card_h,
            opacity=95,
        )

        # Card inner text
        pad = 28
        self.client.add_text_item(
            slide_index=s_idx,
            text=content,
            x=margin_x + pad,
            y=card_y + pad,
            width=card_w - (pad * 2),
            height=card_h - (pad * 2),
            font=self.theme["font_body"],
            size=18,
            color=self.theme["text_primary"],
        )

        if notes:
            self.client.set_presenter_notes(s_idx, notes)

        return s_idx

    def build_two_column_slide(
        self,
        title: str,
        col1_title: str,
        col1_content: str,
        col2_title: str,
        col2_content: str,
        subtitle: Optional[str] = None,
        notes: Optional[str] = None,
        after_slide: Optional[int] = None,
    ) -> int:
        """Create a two-column comparison or split card slide."""
        s_idx = self.client.add_slide(layout=self._get_blank_layout(), after_slide=after_slide)
        self._render_header(s_idx, title, subtitle)

        margin_x = int(self.doc_w * 0.06)
        gap = int(self.doc_w * 0.03)
        card_y = int(self.doc_h * 0.22)
        card_w = int((self.doc_w * 0.88 - gap) / 2)
        card_h = int(self.doc_h * 0.70)

        # Col 1 Card
        self.client.add_shape(slide_index=s_idx, x=margin_x, y=card_y, width=card_w, height=card_h)
        # Col 1 Header
        self.client.add_text_item(
            slide_index=s_idx,
            text=col1_title,
            x=margin_x + 24,
            y=card_y + 24,
            width=card_w - 48,
            height=40,
            font=f"{self.theme['font_title']}-Bold",
            size=22,
            color=self.theme["accent"],
        )
        # Col 1 Text
        self.client.add_text_item(
            slide_index=s_idx,
            text=col1_content,
            x=margin_x + 24,
            y=card_y + 70,
            width=card_w - 48,
            height=card_h - 90,
            font=self.theme["font_body"],
            size=16,
            color=self.theme["text_primary"],
        )

        # Col 2 Card
        col2_x = margin_x + card_w + gap
        self.client.add_shape(slide_index=s_idx, x=col2_x, y=card_y, width=card_w, height=card_h)
        # Col 2 Header
        self.client.add_text_item(
            slide_index=s_idx,
            text=col2_title,
            x=col2_x + 24,
            y=card_y + 24,
            width=card_w - 48,
            height=40,
            font=f"{self.theme['font_title']}-Bold",
            size=22,
            color=self.theme["accent_secondary"],
        )
        # Col 2 Text
        self.client.add_text_item(
            slide_index=s_idx,
            text=col2_content,
            x=col2_x + 24,
            y=card_y + 70,
            width=card_w - 48,
            height=card_h - 90,
            font=self.theme["font_body"],
            size=16,
            color=self.theme["text_primary"],
        )

        if notes:
            self.client.set_presenter_notes(s_idx, notes)

        return s_idx

    def build_metric_grid_slide(
        self,
        title: str,
        metrics: List[Dict[str, str]],
        subtitle: Optional[str] = None,
        notes: Optional[str] = None,
        after_slide: Optional[int] = None,
    ) -> int:
        """Create a KPI / Metric stat cards slide (supports 2 to 4 cards)."""
        s_idx = self.client.add_slide(layout=self._get_blank_layout(), after_slide=after_slide)
        self._render_header(s_idx, title, subtitle)

        n = min(4, max(2, len(metrics)))
        margin_x = int(self.doc_w * 0.06)
        gap = int(self.doc_w * 0.02)
        total_w = int(self.doc_w * 0.88)
        card_w = int((total_w - ((n - 1) * gap)) / n)
        card_y = int(self.doc_h * 0.28)
        card_h = int(self.doc_h * 0.55)

        for i, m in enumerate(metrics[:n]):
            cx = margin_x + i * (card_w + gap)
            # Card Background
            self.client.add_shape(slide_index=s_idx, x=cx, y=card_y, width=card_w, height=card_h)
            
            # Metric Value (Big Number)
            val_str = str(m.get("value", "0"))
            self.client.add_text_item(
                slide_index=s_idx,
                text=val_str,
                x=cx + 16,
                y=card_y + 30,
                width=card_w - 32,
                height=60,
                font=f"{self.theme['font_title']}-Bold",
                size=38 if len(val_str) <= 6 else 30,
                color=self.theme["accent"],
            )

            # Metric Label
            label_str = m.get("label", "Metric")
            self.client.add_text_item(
                slide_index=s_idx,
                text=label_str,
                x=cx + 16,
                y=card_y + 100,
                width=card_w - 32,
                height=40,
                font=f"{self.theme['font_title']}-Bold",
                size=18,
                color=self.theme["text_primary"],
            )

            # Metric Description / Subtitle
            desc_str = m.get("desc", "")
            if desc_str:
                self.client.add_text_item(
                    slide_index=s_idx,
                    text=desc_str,
                    x=cx + 16,
                    y=card_y + 145,
                    width=card_w - 32,
                    height=card_h - 160,
                    font=self.theme["font_body"],
                    size=14,
                    color=self.theme["text_secondary"],
                )

        if notes:
            self.client.set_presenter_notes(s_idx, notes)

        return s_idx

    def build_table_slide(
        self,
        title: str,
        headers: List[str],
        rows: List[List[Any]],
        subtitle: Optional[str] = None,
        notes: Optional[str] = None,
        after_slide: Optional[int] = None,
    ) -> int:
        """Create a slide containing a styled data table."""
        s_idx = self.client.add_slide(layout=self._get_blank_layout(), after_slide=after_slide)
        self._render_header(s_idx, title, subtitle)

        margin_x = int(self.doc_w * 0.06)
        tbl_y = int(self.doc_h * 0.22)
        tbl_w = int(self.doc_w * 0.88)
        tbl_h = int(self.doc_h * 0.70)

        num_cols = len(headers)
        num_rows = len(rows) + 1
        data_matrix = [headers] + rows

        self.client.add_table(
            slide_index=s_idx,
            rows=num_rows,
            cols=num_cols,
            x=margin_x,
            y=tbl_y,
            width=tbl_w,
            height=tbl_h,
            data=data_matrix,
            header_row=True,
            header_bg=self.theme["accent"],
            header_fg="#ffffff",
            cell_fg=self.theme["text_primary"],
            font_size=15,
        )

        if notes:
            self.client.set_presenter_notes(s_idx, notes)

        return s_idx

    def build_code_slide(
        self,
        title: str,
        code_snippet: str,
        language: str = "bash",
        subtitle: Optional[str] = None,
        notes: Optional[str] = None,
        after_slide: Optional[int] = None,
    ) -> int:
        """Create a developer terminal code slide."""
        s_idx = self.client.add_slide(layout=self._get_blank_layout(), after_slide=after_slide)
        self._render_header(s_idx, title, subtitle)

        margin_x = int(self.doc_w * 0.06)
        card_y = int(self.doc_h * 0.22)
        card_w = int(self.doc_w * 0.88)
        card_h = int(self.doc_h * 0.70)

        # Terminal container shape
        self.client.add_shape(slide_index=s_idx, x=margin_x, y=card_y, width=card_w, height=card_h)

        # Terminal Window Header Dots
        dot_y = card_y + 14
        self.client.add_text_item(
            slide_index=s_idx,
            text=f"● ● ●   {language.lower()}",
            x=margin_x + 20,
            y=dot_y,
            width=200,
            height=25,
            font=self.theme["font_mono"],
            size=12,
            color=self.theme["text_muted"],
        )

        # Code block text
        self.client.add_text_item(
            slide_index=s_idx,
            text=code_snippet,
            x=margin_x + 24,
            y=card_y + 45,
            width=card_w - 48,
            height=card_h - 60,
            font=self.theme["font_mono"],
            size=14,
            color=self.theme["text_primary"],
        )

        if notes:
            self.client.set_presenter_notes(s_idx, notes)

        return s_idx

    def build_from_spec(self, spec: Dict[str, Any]) -> List[int]:
        """Build multiple slides from a complete JSON/dictionary specification."""
        if "theme" in spec:
            self.set_theme(spec["theme"])

        created_slides = []
        for slide_spec in spec.get("slides", []):
            stype = slide_spec.get("type", "content").lower().strip()
            title = slide_spec.get("title", "Untitled Slide")
            subtitle = slide_spec.get("subtitle")
            notes = slide_spec.get("notes")

            if stype in ["title", "hero"]:
                idx = self.build_title_slide(
                    title=title,
                    subtitle=subtitle,
                    tag=slide_spec.get("tag"),
                    footer=slide_spec.get("footer"),
                    notes=notes,
                )
            elif stype in ["two_column", "split", "comparison"]:
                idx = self.build_two_column_slide(
                    title=title,
                    col1_title=slide_spec.get("col1_title", "Left Column"),
                    col1_content=slide_spec.get("col1_content", ""),
                    col2_title=slide_spec.get("col2_title", "Right Column"),
                    col2_content=slide_spec.get("col2_content", ""),
                    subtitle=subtitle,
                    notes=notes,
                )
            elif stype in ["metrics", "kpi", "stats"]:
                idx = self.build_metric_grid_slide(
                    title=title,
                    metrics=slide_spec.get("metrics", []),
                    subtitle=subtitle,
                    notes=notes,
                )
            elif stype in ["table", "grid"]:
                idx = self.build_table_slide(
                    title=title,
                    headers=slide_spec.get("headers", []),
                    rows=slide_spec.get("rows", []),
                    subtitle=subtitle,
                    notes=notes,
                )
            elif stype in ["code", "terminal"]:
                idx = self.build_code_slide(
                    title=title,
                    code_snippet=slide_spec.get("code", ""),
                    language=slide_spec.get("language", "bash"),
                    subtitle=subtitle,
                    notes=notes,
                )
            else:
                idx = self.build_card_content_slide(
                    title=title,
                    content=slide_spec.get("content", ""),
                    subtitle=subtitle,
                    notes=notes,
                )
            created_slides.append(idx)

        return created_slides


if __name__ == "__main__":
    print("DeckBuilder initialized.")
