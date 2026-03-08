"""Build HTML email layout with journal branding."""
import html
from django.conf import settings


def wrap_email_html(subject: str, body_plain: str) -> str:
    """
    Wrap plain body in a simple, readable HTML layout with journal name.
    Escapes body for safe HTML; newlines become <br> for readability.
    """
    journal = getattr(settings, "JOURNAL_NAME", "Ditech Asia")
    escaped = html.escape(body_plain)
    body_html = escaped.replace("\n", "<br>\n")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(subject)}</title>
</head>
<body style="margin:0; padding:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-size: 16px; line-height: 1.6; color: #333; background-color: #f5f5f5;">
  <div style="max-width: 600px; margin: 0 auto; padding: 24px;">
    <div style="background: linear-gradient(135deg, #1a365d 0%, #2c5282 100%); color: #fff; padding: 24px 28px; border-radius: 8px 8px 0 0;">
      <h1 style="margin: 0; font-size: 22px; font-weight: 600;">{html.escape(journal)}</h1>
      <p style="margin: 6px 0 0; font-size: 14px; opacity: 0.9;">Editorial & submission system</p>
    </div>
    <div style="background: #fff; padding: 28px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 8px 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);">
      <div style="margin-bottom: 20px;">
        {body_html}
      </div>
      <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
      <p style="margin: 0; font-size: 13px; color: #64748b;">
        This is an automated message from {html.escape(journal)}. Please do not reply to this email.
      </p>
    </div>
  </div>
</body>
</html>"""
