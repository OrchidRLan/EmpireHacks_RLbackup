import re
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.constants import (
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USERNAME,
)


def _sanitize_header(value: str) -> str:
    """Strip CR/LF characters from an email header value.

    A subject or From/To value containing newline sequences can be used to
    inject additional RFC-2822 headers into the outbound message
    (OWASP A03:2021 Injection — email header injection / CWE-93).
    The Python email.mime library does NOT strip these automatically.

    Args:
        value: Raw header string sourced from DB or Claude output.

    Returns:
        The value with all CR and LF characters removed.
    """
    return re.sub(r"[\r\n]", "", value)


def send_email(
    to: str,
    subject: str,
    body: str,
    attachments: list[tuple[str, bytes]] | None = None,
) -> None:
    """Send an email via SMTP. Reads SMTP_* env vars.

    For local Mailhog: SMTP_HOST=mailhog, SMTP_PORT=1025, SMTP_USE_TLS=false
    For Gmail: SMTP_HOST=smtp.gmail.com, SMTP_PORT=587, SMTP_USE_TLS=true

    The ``to`` address and ``subject`` are sanitized before being placed into
    MIME headers to prevent email header injection attacks.

    Args:
        to: Recipient email address (sourced from DB, not user input).
        subject: Email subject line (may include Claude-generated text).
        body: Plain-text email body.
        attachments: Optional list of (filename, bytes) tuples to attach.
    """
    host = SMTP_HOST
    port = SMTP_PORT
    use_tls = SMTP_USE_TLS
    username = SMTP_USERNAME
    password = SMTP_PASSWORD
    from_addr = SMTP_FROM

    # Sanitize headers that may carry external or Claude-generated content.
    # The `to` address comes from the DB (apt.host_email), but we sanitize
    # defensively; the body goes into the MIME payload, not a header, so
    # Python's MIME library handles folding safely there.
    safe_to = _sanitize_header(to)
    safe_subject = _sanitize_header(subject)

    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = safe_to
    msg["Subject"] = safe_subject
    msg.attach(MIMEText(body, "plain"))

    if attachments:
        for filename, content in attachments:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
            msg.attach(part)

    if use_tls:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port) as server:
            server.starttls(context=context)
            if username and password:
                server.login(username, password)
            # Use safe_to (sanitized) as the SMTP envelope recipient as well.
            server.sendmail(from_addr, safe_to, msg.as_string())
    else:
        with smtplib.SMTP(host, port) as server:
            server.sendmail(from_addr, safe_to, msg.as_string())
