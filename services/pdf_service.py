def create_text_pdf(title, lines):
    """Create a small dependency-free PDF suitable for attendance exports."""
    page_lines = [title, ""] + [str(line) for line in lines]
    chunks = [page_lines[index:index + 44] for index in range(0, len(page_lines), 44)] or [[]]
    page_object_numbers = [4 + index * 2 for index in range(len(chunks))]
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            f"<< /Type /Pages /Kids [{' '.join(f'{number} 0 R' for number in page_object_numbers)}] "
            f"/Count {len(chunks)} >>"
        ).encode(),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    for index, chunk in enumerate(chunks):
        page_number = page_object_numbers[index]
        content_number = page_number + 1
        objects[page_number] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_number} 0 R >>"
        ).encode()
        commands = ["BT", "/F1 11 Tf", "48 748 Td", "14 TL"]
        for line in chunk:
            commands.append(f"({_escape_pdf_text(line)}) Tj")
            commands.append("T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1", "replace")
        objects[content_number] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode()
            + stream
            + b"\nendstream"
        )

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {0: 0}
    for number in sorted(objects):
        offsets[number] = len(output)
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(objects[number])
        output.extend(b"\nendobj\n")
    xref = len(output)
    maximum = max(objects)
    output.extend(f"xref\n0 {maximum + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for number in range(1, maximum + 1):
        output.extend(f"{offsets[number]:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {maximum + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(output)


def _escape_pdf_text(value):
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
