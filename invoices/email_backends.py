import base64
import json
import re
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
BREVO_TIMEOUT = 20


class BrevoEmailBackend(BaseEmailBackend):
    """Email backend that sends via Brevo's HTTPS API instead of SMTP.

    Render's free tier blocks outbound SMTP ports (25, 465, 587), so plain
    SMTP connections hang there and gunicorn kills the worker. Brevo's API
    runs over HTTPS (port 443), which is never blocked. Activate it in
    production settings by setting BREVO_API_KEY; set DEFAULT_FROM_EMAIL to
    a sender address you verified in your Brevo account. Uses only the
    standard library, so requirements.txt stays unchanged.
    """

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            try:
                self._send(message)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent

    def _send(self, message):
        payload = {
            "sender": self._address_parts(message.from_email),
            "to": [{"email": r} for r in message.to],
            "subject": message.subject,
        }
        if message.cc:
            payload["cc"] = [{"email": r} for r in message.cc]
        if message.bcc:
            payload["bcc"] = [{"email": r} for r in message.bcc]
        if message.reply_to:
            payload["replyTo"] = self._address_parts(message.reply_to[0])
        if message.content_subtype == "html":
            payload["htmlContent"] = message.body
        else:
            payload["textContent"] = message.body
        if message.attachments:
            payload["attachment"] = []
            for item in message.attachments:
                filename, content = item[0], item[1]
                mimetype = item[2] if len(item) > 2 else None
                if isinstance(content, str):
                    content = content.encode("utf-8")
                entry = {
                    "name": filename,
                    "content": base64.b64encode(content).decode("ascii"),
                }
                if mimetype:
                    entry["contentType"] = mimetype
                payload["attachment"].append(entry)

        request = urllib.request.Request(
            BREVO_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "api-key": getattr(settings, "BREVO_API_KEY", ""),
                "content-type": "application/json",
                "accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=BREVO_TIMEOUT) as response:
            if response.status >= 400:
                raise RuntimeError(f"Brevo API returned HTTP {response.status}")

    @staticmethod
    def _address_parts(from_email):
        """Split 'SwiftInvoice <noreply@example.com>' into name + email."""
        match = re.match(r"^(.*)<(.+)>$", from_email.strip())
        if match:
            return {"name": match.group(1).strip(), "email": match.group(2).strip()}
        return {"email": from_email.strip()}