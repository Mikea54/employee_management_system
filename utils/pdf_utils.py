import re
from typing import List


def html_to_text(html: str) -> str:
    """Very basic HTML to plain text conversion."""
    html = re.sub(r'<br\s*/?>', '\n', html)
    return re.sub(r'<[^>]+>', '', html)


def simple_pdf(text: str) -> bytes:
    """Generate a minimal PDF containing the given text."""
    header = b"%PDF-1.4\n"
    objects: List[bytes] = []
    offsets: List[int] = []
    offset = len(header)

    def add(obj: bytes):
        nonlocal offset
        offsets.append(offset)
        objects.append(obj)
        offset += len(obj)

    add(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    add(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    add(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n")

    safe_text = text.replace('\\', r'\\').replace('(', r'\(').replace(')', r'\)')
    y = 750
    lines = []
    for line in safe_text.splitlines():
        if line.strip():
            lines.append(f"BT /F1 12 Tf 50 {y} Td ({line}) Tj ET")
            y -= 15
    stream = "\n".join(lines)
    content = stream.encode("latin1")
    add(f"4 0 obj\n<< /Length {len(content)} >>\nstream\n".encode("latin1") + content + b"\nendstream\nendobj\n")
    add(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    xref_offset = offset
    xref_entries = [b"0000000000 65535 f \n"]
    for off in offsets:
        xref_entries.append(f"{off:010} 00000 n \n".encode("latin1"))
    xref_table = f"xref\n0 {len(offsets)+1}\n".encode("latin1") + b"".join(xref_entries)
    trailer = f"trailer\n<< /Root 1 0 R /Size {len(offsets)+1} >>\nstartxref\n{xref_offset}\n%%EOF".encode("latin1")

    return header + b"".join(objects) + xref_table + trailer
