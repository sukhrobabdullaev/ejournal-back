"""PDF and QR builders for reviewer recognition certificates."""
from io import BytesIO

from django.conf import settings
from django.utils import timezone
from reportlab.graphics import renderPDF, renderSVG
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas


def _draw_center_wrapped_text(
    pdf: canvas.Canvas,
    text: str,
    *,
    font_name: str,
    font_size: int,
    center_x: float,
    top_y: float,
    max_width: float,
    line_height: float,
) -> float:
    """Draw wrapped text centered on X and return next Y cursor."""
    lines = simpleSplit(text, font_name, font_size, max_width) or [text]
    cursor_y = top_y
    pdf.setFont(font_name, font_size)
    for line in lines:
        pdf.drawCentredString(center_x, cursor_y, line)
        cursor_y -= line_height
    return cursor_y


def _truncate_with_ellipsis(text: str, max_length: int = 700) -> str:
    value = (text or "").strip()
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


def _draw_labeled_comment_block(
    pdf: canvas.Canvas,
    *,
    label: str,
    text: str,
    x: float,
    start_y: float,
    max_width: float,
    max_lines: int = 2,
) -> float:
    pdf.setFillColor(colors.HexColor("#1F2937"))
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(x, start_y, label)

    content = _truncate_with_ellipsis(text or "Not provided.", max_length=750)
    lines = simpleSplit(content, "Helvetica", 9, max_width)[:max_lines]
    if len(simpleSplit(content, "Helvetica", 9, max_width)) > max_lines and lines:
        lines[-1] = _truncate_with_ellipsis(lines[-1], max_length=max(len(lines[-1]) - 3, 10))

    cursor_y = start_y - 5.2 * mm
    pdf.setFillColor(colors.HexColor("#374151"))
    pdf.setFont("Helvetica", 9)
    for line in lines:
        pdf.drawString(x, cursor_y, line)
        cursor_y -= 4.5 * mm
    return cursor_y - 1.5 * mm


def _build_qr_drawing(value: str, size_mm: float = 28) -> Drawing:
    qr_widget = qr.QrCodeWidget(value or "about:blank")
    bounds = qr_widget.getBounds()
    qr_width = max(bounds[2] - bounds[0], 1)
    qr_height = max(bounds[3] - bounds[1], 1)
    size = size_mm * mm
    drawing = Drawing(
        size,
        size,
        transform=[size / qr_width, 0, 0, size / qr_height, 0, 0],
    )
    drawing.add(qr_widget)
    return drawing


def _draw_qr_code(pdf: canvas.Canvas, value: str, x: float, y: float, size_mm: float = 28):
    drawing = _build_qr_drawing(value, size_mm=size_mm)
    renderPDF.draw(drawing, pdf, x, y)


def build_certificate_qr_svg(value: str, size_mm: float = 36) -> str:
    """Build certificate QR code SVG string."""
    drawing = _build_qr_drawing(value, size_mm=size_mm)
    rendered = renderSVG.drawToString(drawing)
    if isinstance(rendered, bytes):
        return rendered.decode("utf-8")
    return rendered


def build_reviewer_recognition_pdf(
    submission_title: str,
    author_full_name: str,
    reviewer_full_name: str,
    *,
    issued_at=None,
    verification_url: str = "",
    reviewer_comment: str = "",
    editor_comment: str = "",
) -> bytes:
    """Build reviewer recognition certificate as a designed PDF bytes blob."""
    submission_title = (submission_title or "Untitled article").strip()
    author_full_name = (author_full_name or "Author").strip()
    reviewer_full_name = (reviewer_full_name or "Reviewer").strip()
    issued_at = issued_at or timezone.now()
    issued_label = issued_at.strftime("%d %B %Y")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    # Background
    pdf.setFillColor(colors.HexColor("#FFFFFF"))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    # Decorative frame close to provided design
    outer_x = 10 * mm
    outer_y = 9 * mm
    outer_w = width - (20 * mm)
    outer_h = height - (18 * mm)
    pdf.setStrokeColor(colors.HexColor("#6CA6BE"))
    pdf.setLineWidth(1.5)
    pdf.rect(outer_x, outer_y, outer_w, outer_h, stroke=1, fill=0)
    pdf.setStrokeColor(colors.HexColor("#8BC0D6"))
    pdf.setLineWidth(0.8)
    pdf.rect(outer_x + 4 * mm, outer_y + 4 * mm, outer_w - 8 * mm, outer_h - 8 * mm, stroke=1, fill=0)

    # Header logo block (vector placeholder style)
    center_x = width / 2
    pdf.setFillColor(colors.HexColor("#0E6B94"))
    logo_x = center_x - 40 * mm
    logo_y = height - 44 * mm
    pdf.rect(logo_x, logo_y, 18 * mm, 18 * mm, fill=1, stroke=0)
    pdf.setStrokeColor(colors.HexColor("#E8F3F8"))
    pdf.setLineWidth(2)
    pdf.line(logo_x + 3 * mm, logo_y + 1 * mm, logo_x + 15 * mm, logo_y + 13 * mm)
    pdf.line(logo_x + 0.5 * mm, logo_y + 6 * mm, logo_x + 11 * mm, logo_y + 16.5 * mm)
    pdf.line(logo_x + 6 * mm, logo_y + 0.5 * mm, logo_x + 17 * mm, logo_y + 11.5 * mm)

    pdf.setFillColor(colors.HexColor("#1A4D77"))
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(logo_x + 20.5 * mm, logo_y + 11 * mm, "DCIJ")
    pdf.drawString(logo_x + 20.5 * mm, logo_y + 3 * mm, "INFO")

    # Title
    pdf.setFillColor(colors.HexColor("#0E6B94"))
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawCentredString(center_x, height - 57 * mm, "CERTIFICATE OF REVIEWER RECOGNITION")

    # Body
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawCentredString(center_x, height - 77 * mm, "This is to certify that")

    pdf.setFillColor(colors.HexColor("#1F5F95"))
    pdf.setFont("Helvetica-Bold", 21)
    pdf.drawCentredString(center_x, height - 93 * mm, author_full_name)

    pdf.setFillColor(colors.HexColor("#2B2B5A"))
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(center_x, height - 107 * mm, "has received a positive review recommendation for:")

    pdf.setFillColor(colors.black)
    article_bottom = _draw_center_wrapped_text(
        pdf,
        submission_title,
        font_name="Times-Roman",
        font_size=15,
        center_x=center_x,
        top_y=height - 121 * mm,
        max_width=width - 90 * mm,
        line_height=8.5 * mm,
    )

    pdf.setFont("Helvetica", 12)
    pdf.setFillColor(colors.HexColor("#3D3D3D"))
    pdf.drawCentredString(center_x, article_bottom - 1.5 * mm, f"Issued on: {issued_label}")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawCentredString(center_x, article_bottom - 11 * mm, f"Reviewer: {reviewer_full_name}")

    pdf.setFont("Times-Roman", 12)
    pdf.drawCentredString(
        center_x,
        article_bottom - 22 * mm,
        "Awarded by: Digital Innovation and Emerging Technologies (DCIJ)",
    )

    comments_x = 32 * mm
    comments_width = width - 64 * mm
    comments_start_y = article_bottom - 31 * mm
    comment_cursor = _draw_labeled_comment_block(
        pdf,
        label="Reviewer comments:",
        text=reviewer_comment,
        x=comments_x,
        start_y=comments_start_y,
        max_width=comments_width,
    )
    _draw_labeled_comment_block(
        pdf,
        label="Editor comment:",
        text=editor_comment,
        x=comments_x,
        start_y=comment_cursor,
        max_width=comments_width,
    )

    # Bottom block (chief editor + QR + signature line)
    bottom_y = 22 * mm
    qr_x = center_x - 10 * mm
    qr_y = bottom_y + 6 * mm
    _draw_qr_code(pdf, verification_url, qr_x, qr_y, size_mm=20)

    pdf.setFillColor(colors.HexColor("#111111"))
    pdf.setFont("Times-Roman", 11)
    pdf.drawString(38 * mm, bottom_y + 19 * mm, "Chief Editor:")

    # Signature line and name
    line_x1 = width - 110 * mm
    line_x2 = width - 42 * mm
    line_y = bottom_y + 14 * mm
    pdf.setStrokeColor(colors.black)
    pdf.setLineWidth(1.1)
    pdf.line(line_x1, line_y, line_x2, line_y)
    pdf.setFont("Times-Roman", 10)
    pdf.drawString(line_x1 + 10 * mm, bottom_y + 6 * mm, "Dr. Ibrohimbek Yusupov")

    # Faux signature stroke
    pdf.setStrokeColor(colors.HexColor("#222222"))
    pdf.setLineWidth(1.2)
    pdf.bezier(line_x1 + 16 * mm, line_y + 6 * mm, line_x1 + 25 * mm, line_y + 26 * mm, line_x1 + 32 * mm, line_y - 2 * mm, line_x1 + 40 * mm, line_y + 9 * mm)
    pdf.bezier(line_x1 + 40 * mm, line_y + 9 * mm, line_x1 + 48 * mm, line_y + 14 * mm, line_x1 + 56 * mm, line_y + 18 * mm, line_x1 + 64 * mm, line_y + 16 * mm)

    # Footer contact
    pdf.setFillColor(colors.HexColor("#1F2937"))
    pdf.setFont("Helvetica", 9)
    pdf.drawString(18 * mm, 14 * mm, "info@dcij.info    |    https://www.dcij.info    |    +998 90 123 45 67")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


def _draw_certificate_frame(pdf: canvas.Canvas, width: float, height: float):
    """Draw decorative multi-line frame for formal certificate look."""
    frame_color_dark = colors.HexColor("#4B5563")
    frame_color_light = colors.HexColor("#9CA3AF")

    outer_margin = 8 * mm
    mid_margin = 12 * mm
    inner_margin = 16 * mm

    pdf.setStrokeColor(frame_color_dark)
    pdf.setLineWidth(1.2)
    pdf.rect(
        outer_margin,
        outer_margin,
        width - 2 * outer_margin,
        height - 2 * outer_margin,
        stroke=1,
        fill=0,
    )

    pdf.setStrokeColor(frame_color_light)
    pdf.setLineWidth(0.8)
    pdf.rect(
        mid_margin,
        mid_margin,
        width - 2 * mid_margin,
        height - 2 * mid_margin,
        stroke=1,
        fill=0,
    )

    pdf.setStrokeColor(frame_color_dark)
    pdf.setLineWidth(0.6)
    pdf.rect(
        inner_margin,
        inner_margin,
        width - 2 * inner_margin,
        height - 2 * inner_margin,
        stroke=1,
        fill=0,
    )


def build_journal_publication_certificate_pdf(
    *,
    author_full_name: str,
    article_title: str,
    issue_title: str,
    volume: int,
    issue_number: int,
    publication_year: int,
    publication_date=None,
    author_affiliation: str = "",
    author_country: str = "",
    certificate_code: str = "",
) -> bytes:
    """Build journal publication certificate PDF bytes for issue publication email."""
    issued_at = timezone.now()
    issued_label = issued_at.strftime("%d %B %Y")
    publication_label = (
        publication_date.strftime("%d %B %Y")
        if publication_date
        else str(publication_year)
    )
    journal_name = getattr(settings, "JOURNAL_NAME", "Ditech Asia")
    journal_long_name = getattr(
        settings,
        "JOURNAL_FULL_NAME",
        "International Journal for Research in Applied Science and Engineering Technology",
    )
    journal_issn = getattr(settings, "JOURNAL_ISSN", "2321-9653")

    author_full_name = (author_full_name or "Author").strip()
    article_title = (article_title or "Untitled article").strip()
    issue_title = (issue_title or "").strip() or (
        f"Volume {volume}, Issue {issue_number} ({publication_year})"
    )

    affiliation_bits = [bit for bit in [author_affiliation.strip(), author_country.strip()] if bit]
    affiliation_line = ", ".join(affiliation_bits) if affiliation_bits else "Affiliation not provided"

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    center_x = width / 2

    pdf.setFillColor(colors.white)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    _draw_certificate_frame(pdf, width, height)

    pdf.setFillColor(colors.HexColor("#111827"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString(center_x, height - 21 * mm, "Scientific Journal Publication Certificate")

    pdf.setFont("Times-Bold", 21)
    pdf.drawCentredString(center_x, height - 34 * mm, "CERTIFICATE OF JOURNAL PUBLICATION")

    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(center_x, height - 45 * mm, "This certificate is awarded to")

    pdf.setFillColor(colors.HexColor("#0B1C4D"))
    pdf.setFont("Times-Bold", 22)
    pdf.drawCentredString(center_x, height - 58 * mm, author_full_name)

    pdf.setFillColor(colors.HexColor("#1F2937"))
    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(center_x, height - 66 * mm, affiliation_line)

    pdf.setFillColor(colors.HexColor("#111827"))
    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(center_x, height - 76 * mm, "for contribution to the published journal issue:")

    title_bottom = _draw_center_wrapped_text(
        pdf,
        issue_title,
        font_name="Times-Bold",
        font_size=15,
        center_x=center_x,
        top_y=height - 86 * mm,
        max_width=width - 80 * mm,
        line_height=7 * mm,
    )

    pdf.setFont("Helvetica", 10.5)
    pdf.drawCentredString(
        center_x,
        title_bottom - 2 * mm,
        f"{journal_long_name} (ISSN: {journal_issn})",
    )

    article_bottom = _draw_center_wrapped_text(
        pdf,
        f"Article: {article_title}",
        font_name="Times-Roman",
        font_size=13,
        center_x=center_x,
        top_y=title_bottom - 10 * mm,
        max_width=width - 90 * mm,
        line_height=6 * mm,
    )

    pdf.setFont("Helvetica", 10.5)
    pdf.drawCentredString(
        center_x,
        article_bottom - 4 * mm,
        f"Volume {volume} | Issue {issue_number} | Publication: {publication_label}",
    )

    pdf.drawCentredString(
        center_x,
        article_bottom - 11 * mm,
        f"Certificate issued on {issued_label}",
    )

    pdf.setStrokeColor(colors.HexColor("#374151"))
    pdf.setLineWidth(0.9)
    line_y = 24 * mm
    pdf.line(width - 102 * mm, line_y, width - 36 * mm, line_y)
    pdf.setFont("Times-Roman", 10)
    pdf.drawString(width - 90 * mm, line_y - 5 * mm, "Editorial Office")

    pdf.setFont("Helvetica", 9.5)
    footer_left = 24 * mm
    pdf.drawString(footer_left, 20 * mm, f"Journal: {journal_name}")
    pdf.drawString(footer_left, 15 * mm, "Publisher: Ditech Asia Editorial System")
    pdf.drawString(footer_left, 10 * mm, f"Certificate code: {certificate_code or 'N/A'}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()
