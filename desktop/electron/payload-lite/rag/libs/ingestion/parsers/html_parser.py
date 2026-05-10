"""HTML parser — extracts structure using BeautifulSoup."""

from __future__ import annotations

from libs.ingestion.parsers.base import (
    ContentElement,
    ElementType,
    ParseResult,
)

try:
    from bs4 import BeautifulSoup, Tag
except ImportError as exc:
    raise ImportError(
        "beautifulsoup4 is required for HTML parsing. "
        "Install it with: pip install beautifulsoup4"
    ) from exc

_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_BLOCK_TAGS = {"p", "div", "section", "article"}


class HtmlParser:
    """Parses HTML files into structured elements using BeautifulSoup."""

    @property
    def supported_extensions(self) -> set[str]:
        return {".html", ".htm"}

    def parse(self, content: bytes, filename: str) -> ParseResult:
        # Try to detect encoding from HTML meta; fall back to utf-8
        text = content.decode("utf-8", errors="replace")
        soup = BeautifulSoup(text, "html.parser")

        elements: list[ContentElement] = []
        title: str | None = None

        # Extract <title>
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title = title_tag.string.strip()

        # Walk the body (or whole document if no body)
        root = soup.body or soup
        self._walk(root, elements)

        # Fall back title from first h1
        if not title:
            for e in elements:
                if e.type == ElementType.HEADING and e.level == 1:
                    title = e.content
                    break

        # Build raw text
        raw_text = soup.get_text(separator="\n", strip=True)

        return ParseResult(
            elements=elements,
            title=title,
            raw_text=raw_text,
            metadata={"format": "html"},
        )

    # ------------------------------------------------------------------

    def _walk(self, node: Tag, elements: list[ContentElement]) -> None:
        """Recursively extract elements from the DOM tree."""
        for child in node.children:
            if not isinstance(child, Tag):
                continue

            tag = child.name.lower()

            if tag in _HEADING_TAGS:
                level = int(tag[1])
                text = child.get_text(strip=True)
                if text:
                    elements.append(
                        ContentElement(
                            type=ElementType.HEADING, content=text, level=level
                        )
                    )

            elif tag == "table":
                table_text = self._extract_table(child)
                if table_text:
                    elements.append(
                        ContentElement(type=ElementType.TABLE, content=table_text)
                    )

            elif tag in ("pre", "code"):
                code_text = child.get_text()
                if code_text.strip():
                    lang = child.get("class", [])
                    meta = {}
                    if lang:
                        # Common pattern: class="language-python"
                        for cls in lang:
                            if cls.startswith("language-"):
                                meta["language"] = cls[9:]
                                break
                    elements.append(
                        ContentElement(
                            type=ElementType.CODE_BLOCK,
                            content=code_text.strip(),
                            metadata=meta,
                        )
                    )

            elif tag == "blockquote":
                text = child.get_text(strip=True)
                if text:
                    elements.append(
                        ContentElement(type=ElementType.BLOCKQUOTE, content=text)
                    )

            elif tag in ("ul", "ol"):
                for li in child.find_all("li", recursive=False):
                    li_text = li.get_text(strip=True)
                    if li_text:
                        elements.append(
                            ContentElement(
                                type=ElementType.LIST_ITEM, content=li_text
                            )
                        )

            elif tag in _BLOCK_TAGS:
                # Check if this block has nested block-level children
                has_block_children = any(
                    isinstance(c, Tag) and c.name.lower() in (
                        _HEADING_TAGS | _BLOCK_TAGS | {"table", "pre", "ul", "ol", "blockquote"}
                    )
                    for c in child.children
                )
                if has_block_children:
                    self._walk(child, elements)
                else:
                    text = child.get_text(strip=True)
                    if text:
                        elements.append(
                            ContentElement(
                                type=ElementType.PARAGRAPH, content=text
                            )
                        )
            else:
                # Recurse into unknown containers (e.g., <main>, <nav>, <aside>)
                self._walk(child, elements)

    @staticmethod
    def _extract_table(table_tag: Tag) -> str:
        """Convert an HTML table to a simple text representation."""
        rows: list[str] = []
        for tr in table_tag.find_all("tr"):
            cells = [
                td.get_text(strip=True)
                for td in tr.find_all(["th", "td"])
            ]
            rows.append(" | ".join(cells))
        return "\n".join(rows)
