"""Email sender - sends the digest via QQ SMTP."""

import os
import time
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

log = logging.getLogger("tech-pulse")

MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds
SMTP_TIMEOUT = 30  # seconds


def _md_to_html(md_text: str) -> str:
    """Minimal markdown to HTML conversion for email."""
    import re

    lines = md_text.split("\n")
    html_lines = []
    in_list = False

    for line in lines:
        # Headers
        if line.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(
                f'<h2 style="color:#1a1a2e;font-size:20px;border-bottom:2px solid #e94560;'
                f'padding-bottom:6px;margin-top:28px">{line[3:]}</h2>'
            )
            continue
        elif line.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(
                f'<h3 style="color:#16213e;font-size:17px;margin-top:20px">{line[4:]}</h3>'
            )
            continue
        elif line.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(
                f'<h1 style="color:#e94560;font-size:22px;margin-top:20px">{line[2:]}</h1>'
            )
            continue

        # Horizontal rule
        if line.strip() == "---":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append('<hr style="border:none;border-top:1px solid #eee;margin:24px 0">')
            continue

        # Process inline formatting
        # 1. Bold
        line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
        # 2. Inline code
        line = re.sub(r"`([^`]+)`", r'<code style="background:#f0f0f0;padding:2px 5px;border-radius:3px;font-size:13px">\1</code>', line)
        # 3. Markdown links (BEFORE plain URLs)
        line = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r'<a href="\2" style="color:#0f3460;text-decoration:none;border-bottom:1px solid #0f3460">\1</a>',
            line,
        )
        # 4. Plain URLs (only if not already in an href)
        line = re.sub(
            r"(?<!href=\")(?<!\">)(https?://[^\s<>\)\"]+)",
            r'<a href="\1" style="color:#0f3460;text-decoration:none;border-bottom:1px solid #0f3460">\1</a>',
            line,
        )

        # List items
        if line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_lines.append('<ul style="padding-left:20px;margin:8px 0">')
                in_list = True
            html_lines.append(
                f'<li style="margin-bottom:6px">{line[2:]}</li>'
            )
        elif re.match(r"^\d+\.\s", line):
            # Numbered list
            content = re.sub(r"^\d+\.\s", "", line)
            html_lines.append(
                f'<p style="margin:6px 0;padding-left:10px">{line}</p>'
            )
        elif line.strip() == "":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("")
        elif line.strip().startswith("（") or line.strip().startswith("("):
            # Parenthetical / source attribution line
            html_lines.append(
                f'<p style="color:#888;font-size:13px;margin:2px 0 12px 0;font-style:italic">{line}</p>'
            )
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f'<p style="margin:8px 0;line-height:1.7">{line}</p>')

    if in_list:
        html_lines.append("</ul>")

    body = "\n".join(html_lines)
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#333;line-height:1.7;background:#fff">
<div style="text-align:center;margin-bottom:24px">
  <h1 style="color:#e94560;font-size:26px;margin:0 0 8px 0;letter-spacing:1px">📡 Tech Pulse 周报</h1>
  <p style="color:#999;font-size:14px;margin:0">{datetime.now().strftime('%Y-%m-%d')} | AI 自动摘要</p>
</div>
<div style="background:#f8f9fa;border-radius:8px;padding:20px;margin-bottom:20px;border-left:4px solid #e94560">
{body}
</div>
<hr style="border:none;border-top:1px solid #eee;margin-top:24px">
<p style="color:#aaa;font-size:12px;text-align:center;margin-top:16px">由 Tech Pulse 自动生成 | Powered by AI</p>
</body>
</html>"""


def _build_message(markdown_text: str):
    """Build the email message (plain text + HTML)."""
    sender = os.environ["SMTP_SENDER"]
    receiver = os.environ["SMTP_RECEIVER"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Tech Pulse 周报 - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = sender
    msg["To"] = receiver

    msg.attach(MIMEText(markdown_text, "plain", "utf-8"))
    msg.attach(MIMEText(_md_to_html(markdown_text), "html", "utf-8"))
    return msg


def send(markdown_text: str) -> bool:
    """Send digest email via QQ SMTP with retry on timeout. Returns True on success."""
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.qq.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    sender = os.environ["SMTP_SENDER"]
    auth_code = os.environ["SMTP_AUTH_CODE"]
    receiver = os.environ["SMTP_RECEIVER"]

    msg = _build_message(markdown_text)
    payload = msg.as_string()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info(f"Sending email (attempt {attempt}/{MAX_RETRIES})...")
            with smtplib.SMTP(smtp_server, smtp_port, timeout=SMTP_TIMEOUT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(sender, auth_code)
                server.sendmail(sender, [receiver], payload)
            log.info("Email sent successfully")
            return True
        except (smtplib.SMTPServerDisconnected, TimeoutError, OSError) as e:
            log.warning(f"Attempt {attempt}/{MAX_RETRIES} failed: {type(e).__name__}: {e}")
            if attempt < MAX_RETRIES:
                log.info(f"Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)

    log.error(f"Email sending failed after {MAX_RETRIES} attempts")
    return False
