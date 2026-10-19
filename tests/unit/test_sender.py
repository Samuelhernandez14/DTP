import smtplib
from email.message import EmailMessage

import pytest

from citologia.domain.errors import EmailError
from citologia.notifications.sender import SmtpSender


def _fabrica(nombre, log):
    class Fake:
        def __init__(self, host, port, timeout=None):
            log.append((nombre, port))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            log.append((nombre, "starttls"))

        def login(self, u, p):
            log.append((nombre, "login"))

        def send_message(self, msg):
            log.append((nombre, "send"))
    return Fake


def _msg():
    m = EmailMessage()
    m["Message-ID"] = "<x@test>"
    return m


def test_puerto_465_usa_ssl_implicito_sin_starttls(monkeypatch):
    log = []
    monkeypatch.setattr(smtplib, "SMTP", _fabrica("SMTP", log))
    monkeypatch.setattr(smtplib, "SMTP_SSL", _fabrica("SSL", log))
    SmtpSender("h", 465, "u", "p").enviar(_msg())
    assert ("SSL", "send") in log and ("SSL", "starttls") not in log
    assert not any(n == "SMTP" for n, _ in log)


def test_puerto_587_usa_starttls(monkeypatch):
    log = []
    monkeypatch.setattr(smtplib, "SMTP", _fabrica("SMTP", log))
    monkeypatch.setattr(smtplib, "SMTP_SSL", _fabrica("SSL", log))
    SmtpSender("h", 587, "u", "p").enviar(_msg())
    assert [e for e in log if e[0] == "SMTP"] == [
        ("SMTP", 587), ("SMTP", "starttls"), ("SMTP", "login"), ("SMTP", "send")]


def test_error_de_autenticacion_no_se_reintenta(monkeypatch):
    llamadas = []

    class Mala:
        def __init__(self, *a, **k):
            llamadas.append(1)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            pass

        def login(self, u, p):
            raise smtplib.SMTPAuthenticationError(535, b"x")

    monkeypatch.setattr(smtplib, "SMTP", Mala)
    with pytest.raises(EmailError):
        SmtpSender("h", 587, "u", "p").enviar(_msg())
    assert len(llamadas) == 1
