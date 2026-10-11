import sys
from django.core.mail.backends.base import BaseEmailBackend

class SafeConsoleEmailBackend(BaseEmailBackend):
    """
    Console email backend that safely handles UTF-8 / non-ASCII characters
    (such as Bengali text) across Windows cmd/PowerShell without charmap encoding crashes.
    """
    def send_messages(self, email_messages):
        count = 0
        for msg in email_messages:
            try:
                msg_bytes = msg.message().as_bytes()
                separator = b"\n" + (b"=" * 70) + b"\n"
                if hasattr(sys.stdout, "buffer"):
                    sys.stdout.buffer.write(separator)
                    sys.stdout.buffer.write(msg_bytes)
                    sys.stdout.buffer.write(separator)
                    sys.stdout.buffer.flush()
                else:
                    text = msg_bytes.decode("utf-8", errors="replace")
                    print(f"\n{'=' * 70}\n{text}\n{'=' * 70}\n")
                count += 1
            except Exception:
                try:
                    to_list = ", ".join(msg.to)
                    print(f"\n[EMAIL DISPATCHED] To: {to_list} | Subject: {msg.subject}\n")
                    count += 1
                except Exception:
                    pass
        return count
