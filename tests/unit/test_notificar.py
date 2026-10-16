from citologia.domain.errors import EmailError
from citologia.domain.models import Decision, IdentidadPDF, Indicacion
from citologia.notifications.correo import construir_correo
from citologia.notifications.sender import DryRunSender
from citologia.pipeline.notificar import TIPO_ACTIVACION, notificar_activacion

SHA = "a" * 64
ID_OK = IdentidadPDF("CC", "1000000001", "MARIA PEREZ")
ACTIVAR = Decision(True, 1, Indicacion.TAMIZAJE, False, ["Regla 1"])


class Espia:
    def __init__(self):
        self.enviados = []

    def enviar(self, msg):
        self.enviados.append(msg)
        return "<id@test>"


class FallaUnaVez(Espia):
    def __init__(self):
        super().__init__()
        self.fallos = 0

    def enviar(self, msg):
        if self.fallos == 0:
            self.fallos = 1
            raise EmailError("SMTPServerDisconnected")
        return super().enviar(msg)


def _llamar(repo, notif, sender, decision=ACTIVAR, identidad=ID_OK):
    return notificar_activacion(
        documento_sha256=SHA, identidad=identidad, codigos=[4], vph=19, decision=decision,
        repo=repo, notificaciones=notif, sender=sender,
        remitente="bot@test.local", destinatarios=["ips@test.local"])


def test_no_activa_no_consulta_ni_reserva(repo_falso, notif_falsa):
    repo, s = repo_falso([]), Espia()
    r = _llamar(repo, notif_falsa, s, decision=Decision(False, None, None, False))
    assert r.motivo == "no_aplica" and repo.consultas == [] and notif_falsa.estado == {}


def test_identidad_no_verificada_no_reserva_ni_envia(repo_falso, notif_falsa):
    s = Espia()
    r = _llamar(repo_falso([]), notif_falsa, s)
    assert r.revision_humana and not s.enviados and notif_falsa.estado == {}


def test_envio_ok_y_segundo_intento_no_duplica(repo_falso, notif_falsa, crear_afiliado):
    repo, s = repo_falso([crear_afiliado()]), Espia()
    assert _llamar(repo, notif_falsa, s).enviado
    r2 = _llamar(repo, notif_falsa, s)
    assert r2.motivo == "ya_notificado" and len(s.enviados) == 1
    assert notif_falsa.estado[(SHA, TIPO_ACTIVACION)] == "ENVIADO"


def test_fallo_smtp_permite_reintento(repo_falso, notif_falsa, crear_afiliado):
    repo, s = repo_falso([crear_afiliado()]), FallaUnaVez()
    assert _llamar(repo, notif_falsa, s).motivo == "error_envio"
    assert notif_falsa.estado[(SHA, TIPO_ACTIVACION)] == "ERROR"
    assert _llamar(repo, notif_falsa, s).enviado and len(s.enviados) == 1


def test_asunto_sin_datos_personales_y_cuerpo_con_datos(crear_afiliado):
    msg = construir_correo(caso_ref="abc123", afiliado=crear_afiliado(), codigos=[4], vph=19,
                           decision=ACTIVAR, remitente="a@b.c", destinatarios=["x@y.z"])
    asunto = msg["Subject"]
    assert "PEREZ" not in asunto and "1000000001" not in asunto and "abc123" in asunto
    cuerpo = msg.get_content()
    assert "1000000001" in cuerpo and "LEI de alto grado" in cuerpo and "Detectado" in cuerpo


def test_dry_run_escribe_eml(tmp_path, crear_afiliado):
    msg = construir_correo(caso_ref="abc123", afiliado=crear_afiliado(), codigos=[4], vph=None,
                           decision=ACTIVAR, remitente="a@b.c", destinatarios=["x@y.z"])
    DryRunSender(tmp_path).enviar(msg)
    assert (tmp_path / "abc123.eml").exists()