"""Email for sign-in codes and alerts.

With TREELINE_SMTP_HOST set, mail goes out over SMTP. Without it (dev),
each message is written to the outbox folder and the log instead.
"""

import logging
import os
import smtplib
import time
from email.message import EmailMessage

log = logging.getLogger("treeline")


def send(to, subject, body):
    host = os.environ.get("TREELINE_SMTP_HOST")
    sender = os.environ.get("TREELINE_MAIL_FROM", "Treeline <no-reply@treeline.invalid>")
    if not host:
        outbox = os.environ.get("TREELINE_OUTBOX", "/data/outbox")
        os.makedirs(outbox, exist_ok=True)
        safe = "".join(c if c.isalnum() or c in "@.-_" else "_" for c in to)
        path = os.path.join(outbox, f"{int(time.time() * 1000)}-{safe}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"To: {to}\nSubject: {subject}\n\n{body}\n")
        log.info("mail to %s: %s (saved to %s)", to, subject, path)
        return True
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = sender, to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(host, int(os.environ.get("TREELINE_SMTP_PORT", "587")), timeout=15) as s:
            if os.environ.get("TREELINE_SMTP_TLS", "1") == "1":
                s.starttls()
            user = os.environ.get("TREELINE_SMTP_USER")
            if user:
                s.login(user, os.environ.get("TREELINE_SMTP_PASS", ""))
            s.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError):
        log.exception("could not send mail to %s", to)
        return False
