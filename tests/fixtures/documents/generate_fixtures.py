from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


FIXTURE_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_text_pdf(path: Path, text: str) -> None:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
    objects = [
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        f"4 0 obj\n<< /Length {len(stream)} >>\nstream\n{stream}\nendstream\nendobj\n",
        "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    header = "%PDF-1.4\n"
    offsets = [0]
    body = ""
    current = len(header.encode("utf-8"))
    for obj in objects:
        offsets.append(current)
        body += obj
        current += len(obj.encode("utf-8"))
    xref_start = current
    xref_lines = ["xref", f"0 {len(offsets)}", "0000000000 65535 f "]
    for offset in offsets[1:]:
        xref_lines.append(f"{offset:010d} 00000 n ")
    trailer = "\n".join(
        xref_lines
        + [
            "trailer",
            f"<< /Size {len(offsets)} /Root 1 0 R >>",
            "startxref",
            str(xref_start),
            "%%EOF",
            "",
        ]
    )
    path.write_bytes((header + body + trailer).encode("utf-8"))


def _write_scanned_pdf(path: Path) -> None:
    _write_text_pdf(path, "")


def _write_docx(path: Path) -> None:
    content_types = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">
  <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>
  <Default Extension=\"xml\" ContentType=\"application/xml\"/>
  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>
</Types>
"""
    rels = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>
</Relationships>
"""
    document_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">
  <w:body>
    <w:p><w:r><w:t>Sample DOCX paragraph one.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Sample DOCX paragraph two.</w:t></w:r></w:p>
  </w:body>
</w:document>
"""

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in [
            ("[Content_Types].xml", content_types),
            ("_rels/.rels", rels),
            ("word/document.xml", document_xml),
        ]:
            info = zipfile.ZipInfo(name)
            info.date_time = (2020, 1, 1, 0, 0, 0)
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload)


def generate() -> dict[str, str]:
    sample_pdf = FIXTURE_DIR / "sample.pdf"
    scanned_pdf = FIXTURE_DIR / "scanned.pdf"
    sample_docx = FIXTURE_DIR / "sample.docx"

    _write_text_pdf(sample_pdf, "Sample PDF text layer.")
    _write_scanned_pdf(scanned_pdf)
    _write_docx(sample_docx)

    manifest = {
        "sample.pdf": _sha256(sample_pdf),
        "scanned.pdf": _sha256(scanned_pdf),
        "sample.docx": _sha256(sample_docx),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2, sort_keys=True))
