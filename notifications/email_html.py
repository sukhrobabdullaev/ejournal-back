"""Build HTML email layout with journal branding."""
import html
import re

from django.conf import settings


URL_PATTERN = re.compile(r"(https?://[^\s<>\"']+)")


def _linkify_text(text: str) -> str:
  """Escape text and convert absolute URLs into clickable anchors."""
  escaped = html.escape(text)
  return URL_PATTERN.sub(
    lambda match: (
      f'<a href="{html.escape(match.group(1))}" '
      'style="color:#2563eb; text-decoration:underline; word-break:break-word;">'
      f"{html.escape(match.group(1))}</a>"
    ),
    escaped,
  )


def wrap_email_html(subject: str, body_plain: str) -> str:
    """
    Wrap plain body in a simple, readable HTML layout with journal name.
    Escapes body for safe HTML; newlines become <br> for readability.
    """
    journal = getattr(settings, "JOURNAL_NAME", "Ditech Asia")
    body_html = "<br>".join(_linkify_text(line) for line in body_plain.splitlines())
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(subject)}</title>
</head>
<body style="margin:0; padding:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif; font-size:16px; line-height:1.65; color:#0f172a; background:linear-gradient(180deg,#eef4ff 0%,#f8fbff 100%);">
  <div style="max-width:660px; margin:0 auto; padding:28px 18px 36px;">
    <div style="background:linear-gradient(135deg,#0b1c4d 0%,#1d4ed8 55%,#60a5fa 100%); color:#fff; padding:28px 30px; border-radius:20px 20px 0 0; box-shadow:0 16px 36px rgba(15,23,42,0.18);">
      <p style="margin:0 0 6px; font-size:12px; letter-spacing:.18em; text-transform:uppercase; opacity:.85;">{html.escape(journal)}</p>
      <h1 style="margin:0; font-size:24px; font-weight:700;">{html.escape(subject)}</h1>
      <p style="margin:8px 0 0; font-size:14px; opacity:.92;">Editorial workflow update</p>
    </div>
    <div style="background:#ffffff; padding:30px; border:1px solid #dbe8fb; border-top:none; border-radius:0 0 20px 20px; box-shadow:0 16px 36px rgba(15,23,42,0.08);">
      <div style="background:#f8fbff; border:1px solid #d8e4f6; border-radius:16px; padding:20px 22px; color:#1f2937;">
        {body_html}
      </div>
      <div style="margin-top:24px; padding-top:18px; border-top:1px solid #e2e8f0; font-size:13px; color:#64748b;">
        This is an automated message from {html.escape(journal)}. Please do not reply to this email.
      </div>
    </div>
  </div>
</body>
</html>"""


def render_account_notification_html(
    *,
    subject: str,
    intro: str,
    recipient_roles: list[str] | None = None,
    changed_fields: list[str] | None = None,
    cta_label: str | None = None,
    cta_url: str | None = None,
) -> str:
    """Professional responsive template for verification/profile notification emails."""
    journal = getattr(settings, "JOURNAL_NAME", "Ditech Asia")
    roles = recipient_roles or []
    role_badges = "".join(
        (
            '<span style="display:inline-block;margin:4px 6px 0 0;padding:6px 10px;'
            'border-radius:999px;background:#e8f1ff;color:#1d4ed8;font-size:12px;font-weight:700;">'
            f"{html.escape(role.title())}</span>"
        )
        for role in roles
    )
    fields_html = "".join(
        f'<li style="margin:0 0 8px;">{html.escape(field.replace("_", " ").title())}</li>'
        for field in (changed_fields or [])
    )
    cta_html = ""
    if cta_label and cta_url:
        cta_html = (
            '<div style="margin-top:20px;">'
            f'<a href="{html.escape(cta_url)}" '
            'style="display:inline-block;padding:12px 18px;border-radius:10px;background:#4285f4;'
            'color:#ffffff;text-decoration:none;font-size:14px;font-weight:700;">'
            f"{html.escape(cta_label)}"
            "</a></div>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(subject)}</title>
</head>
<body style="margin:0;padding:0;background:#f1f6ff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;color:#0f172a;">
  <div style="max-width:680px;margin:0 auto;padding:24px 14px 30px;">
    <div style="border-radius:18px;overflow:hidden;box-shadow:0 14px 34px rgba(15,23,42,0.14);">
      <div style="padding:26px 26px 20px;background:linear-gradient(135deg,#0b1c4d 0%,#1d4ed8 55%,#4285f4 100%);color:#fff;">
        <p style="margin:0 0 8px;font-size:12px;letter-spacing:.16em;text-transform:uppercase;opacity:.9;">{html.escape(journal)}</p>
        <h1 style="margin:0;font-size:24px;line-height:1.25;">{html.escape(subject)}</h1>
      </div>
      <div style="background:#fff;padding:24px 26px 26px;border:1px solid #dbe6fb;border-top:none;">
        <p style="margin:0 0 14px;font-size:15px;line-height:1.65;">{html.escape(intro)}</p>
        {('<div style="margin:0 0 14px;">' + role_badges + '</div>') if role_badges else ''}
        {('<div style="margin-top:12px;padding:14px 16px;border:1px dashed #b8d0fb;border-radius:12px;background:#f8fbff;">'
          '<p style="margin:0 0 10px;font-size:13px;font-weight:700;color:#1e3a8a;">Updated Profile Fields</p>'
          '<ul style="margin:0;padding-left:18px;font-size:14px;color:#334155;">' + fields_html + '</ul>'
          '</div>') if fields_html else ''}
        {cta_html}
        <p style="margin:18px 0 0;font-size:13px;color:#64748b;">This message was sent automatically. If this activity was not yours, please secure your account immediately.</p>
      </div>
    </div>
  </div>
</body>
</html>"""


def build_journal_certificate_email_html(
    *,
    subject: str,
    author_name: str,
    journal_name: str,
    volume: int,
    issue_number: int,
    publication_date: str,
    article_title: str,
    certificate_url: str,
    google_scholar_url: str | None = None,
) -> str:
    """Professional HTML template for journal certificate emails with explicit links."""
    journal = journal_name or getattr(settings, "JOURNAL_NAME", "Ditech Asia")
    
    # Build Scholar section with explicit HTML link
    scholar_html = ""
    if google_scholar_url and google_scholar_url.strip():
        scholar_url = html.escape(google_scholar_url.strip())
        scholar_html = (
            f'<p style="margin:12px 0;font-size:14px;line-height:1.6;'
            'color:#0f172a;"><strong>Google Scholar:</strong><br>'
            f'<a href="{scholar_url}" '
            'style="color:#2563eb;text-decoration:underline;word-break:break-all;">'
            f'{scholar_url}</a></p>'
        )
    else:
        scholar_html = (
            '<p style="margin:12px 0;font-size:13px;line-height:1.6;'
            'color:#64748b;"><em>Enhance your academic profile by adding your '
            '<a href="https://scholar.google.com/citations" '
            'style="color:#2563eb;text-decoration:underline;">Google Scholar URL</a>'
            ' to your profile.</em></p>'
        )
    
    # Build Certificate page link
    cert_url = html.escape(certificate_url)
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(subject)}</title>
</head>
<body style="margin:0;padding:0;background:#f1f6ff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;color:#0f172a;">
  <div style="max-width:680px;margin:0 auto;padding:24px 14px 30px;">
    <div style="border-radius:18px;overflow:hidden;box-shadow:0 14px 34px rgba(15,23,42,0.14);">
      <div style="padding:26px 26px 20px;background:linear-gradient(135deg,#0b1c4d 0%,#1d4ed8 55%,#4285f4 100%);color:#fff;">
        <p style="margin:0 0 8px;font-size:12px;letter-spacing:.16em;text-transform:uppercase;opacity:.9;">{html.escape(journal)}</p>
        <h1 style="margin:0;font-size:24px;line-height:1.25;">Journal Certificate</h1>
      </div>
      <div style="background:#fff;padding:24px 26px 26px;border:1px solid #dbe6fb;border-top:none;">
        <p style="margin:0 0 16px;font-size:15px;line-height:1.65;color:#0f172a;">
          <strong>Dear {html.escape(author_name)},</strong><br><br>
          Congratulations! Your article has been published and included in our journal issue.
        </p>
        
        <div style="margin:16px 0;padding:16px;background:#f8fbff;border-left:4px solid #2563eb;border-radius:4px;">
          <p style="margin:0 0 8px;font-size:13px;font-weight:600;color:#1e40af;text-transform:uppercase;letter-spacing:.05em;">Publication Details</p>
          <p style="margin:0 0 6px;font-size:14px;color:#0f172a;"><strong>Journal:</strong> {html.escape(journal)}</p>
          <p style="margin:0 0 6px;font-size:14px;color:#0f172a;"><strong>Issue:</strong> Volume {volume}, Issue {issue_number}</p>
          <p style="margin:0 0 6px;font-size:14px;color:#0f172a;"><strong>Publication Date:</strong> {html.escape(publication_date)}</p>
          <p style="margin:0;font-size:14px;color:#0f172a;"><strong>Article:</strong> {html.escape(article_title)}</p>
        </div>
        
        <p style="margin:16px 0;font-size:14px;line-height:1.6;color:#0f172a;">
          <strong>Certificate:</strong><br>
          <a href="{cert_url}" 
             style="color:#2563eb;text-decoration:underline;word-break:break-all;">{cert_url}</a>
        </p>
        
        <div style="margin:16px 0;padding:14px;background:#fef3c7;border-radius:8px;border:1px solid #fcd34d;">
          <p style="margin:0;font-size:13px;color:#92400e;"><strong>Academic Profile:</strong></p>
          {scholar_html}
        </div>
        
        <p style="margin:16px 0 0;font-size:13px;color:#64748b;">
          Please find your Journal Certificate attached as PDF.
        </p>
        
        <p style="margin:16px 0 0;font-size:12px;color:#94a3b8;">
          Best regards,<br>
          {html.escape(journal)} Editorial Team
        </p>
        
        <div style="margin-top:20px;padding-top:14px;border-top:1px solid #e2e8f0;font-size:12px;color:#64748b;">
          This is an automated message. Please do not reply to this email.
        </div>
      </div>
    </div>
  </div>
</body>
</html>"""
