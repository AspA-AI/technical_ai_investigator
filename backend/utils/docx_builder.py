"""Minimal DOCX writer for technical report exports.

This keeps the project dependency-free for Word exports by writing the OpenXML
package directly with the standard library.
"""

from __future__ import annotations

from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

ET.register_namespace("w", W_NS)
ET.register_namespace("r", R_NS)


def _w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _text_run(text: str, *, bold: bool = False, size: int | None = None) -> ET.Element:
    run = ET.Element(_w("r"))
    if bold or size is not None:
        rpr = ET.SubElement(run, _w("rPr"))
        if bold:
            ET.SubElement(rpr, _w("b"))
        if size is not None:
            sz = ET.SubElement(rpr, _w("sz"))
            sz.set(_w("val"), str(size))
    text_el = ET.SubElement(run, _w("t"))
    if text.startswith(" ") or text.endswith(" "):
        text_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text_el.text = text
    return run


def _paragraph(
    text: str = "",
    *,
    bold: bool = False,
    size: int | None = None,
    spacing_after: int | None = None,
) -> ET.Element:
    paragraph = ET.Element(_w("p"))
    ppr = ET.SubElement(paragraph, _w("pPr"))
    if spacing_after is not None:
        spacing = ET.SubElement(ppr, _w("spacing"))
        spacing.set(_w("after"), str(spacing_after))
    paragraph.append(_text_run(text, bold=bold, size=size))
    return paragraph


def _heading(text: str, level: int) -> ET.Element:
    if level <= 1:
        return _paragraph(text, bold=True, size=34, spacing_after=120)
    if level == 2:
        return _paragraph(text, bold=True, size=28, spacing_after=80)
    return _paragraph(text, bold=True, size=24, spacing_after=60)


def _blank_paragraph() -> ET.Element:
    return _paragraph("")


def markdown_to_docx_bytes(markdown: str) -> bytes:
    """Convert a markdown report into a minimal valid DOCX package."""
    document = ET.Element(_w("document"))
    body = ET.SubElement(document, _w("body"))

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            body.append(_blank_paragraph())
            continue

        if stripped.startswith("# "):
            body.append(_heading(stripped[2:].strip(), 1))
            continue
        if stripped.startswith("## "):
            body.append(_heading(stripped[3:].strip(), 2))
            continue
        if stripped.startswith("### "):
            body.append(_heading(stripped[4:].strip(), 3))
            continue
        if stripped.startswith("- "):
            body.append(_paragraph(f"• {stripped[2:].strip()}"))
            continue
        body.append(_paragraph(stripped))

    sect_pr = ET.SubElement(body, _w("sectPr"))
    pg_sz = ET.SubElement(sect_pr, _w("pgSz"))
    pg_sz.set(_w("w"), "12240")
    pg_sz.set(_w("h"), "15840")
    pg_mar = ET.SubElement(sect_pr, _w("pgMar"))
    pg_mar.set(_w("top"), "1440")
    pg_mar.set(_w("right"), "1440")
    pg_mar.set(_w("bottom"), "1440")
    pg_mar.set(_w("left"), "1440")

    document_xml = ET.tostring(document, encoding="utf-8", xml_declaration=True)

    content_types_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""

    rels_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{PKG_REL_NS}">
  <Relationship Id="rId1" Type="{R_NS}/officeDocument" Target="word/document.xml"/>
</Relationships>
""".encode("utf-8")

    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", rels_xml)
        archive.writestr("word/document.xml", document_xml)

    return buffer.getvalue()
