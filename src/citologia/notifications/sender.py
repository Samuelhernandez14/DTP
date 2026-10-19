import smtplib
from pathlib import Path
from typing import Protocol

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from citologia.domain.errors import EmailError

_TRANSITORIOS = (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError,
                 TimeoutError, ConnectionError)


class EmailSender(Protocol):
    def enviar(self, msg) -> str: ...


class DryRunSender:
    """Guarda el correo como .eml en vez de enviarlo (pruebas locales)."""
    def __init__(self, carpeta: Path):
        self._carpeta = carpeta

    def enviar(self, msg) -> str:
        self._carpeta.mkdir(parents=True, exist_ok=True)
        (self._carpeta / f"{msg['X-Caso-Ref']}.eml").write_bytes(bytes(msg))
        return msg["Message-ID"]


class SmtpSender:
    def __init__(self, host: str, port: int, user: str, password: str,
                 starttls: bool = True, timeout: int = 30):
        self._host, self._port, self._user = host, port, user
        self._password, self._starttls, self._timeout = password, starttls, timeout
        self._ssl = port == 465          # 465 = SSL implícito; 587 = STARTTLS

    @retry(retry=retry_if_exception_type(_TRANSITORIOS), stop=stop_after_attempt(4),
           wait=wait_exponential_jitter(multiplier=2, max=30), reraise=True)
    def _enviar(self, msg) -> None:
        clase = smtplib.SMTP_SSL if self._ssl else smtplib.SMTP
        with clase(self._host, self._port, timeout=self._timeout) as smtp:
            if self._starttls and not self._ssl:
                smtp.starttls()
            if self._user:
                smtp.login(self._user, self._password)
            smtp.send_message(msg)

    def enviar(self, msg) -> str:
        try:
            self._enviar(msg)
        except (smtplib.SMTPException, OSError) as e:
            # solo el tipo de error: el mensaje puede contener direcciones o datos
            raise EmailError(f"Fallo SMTP: {type(e).__name__}") from e
        return msg["Message-ID"]