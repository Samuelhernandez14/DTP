from dataclasses import dataclass
from typing import Protocol

from citologia.domain.errors import EmailError
from citologia.domain.identidad import AfiliadoRepository, verificar_identidad
from citologia.domain.models import Decision, EstadoVerificacion, IdentidadPDF
from citologia.notifications.correo import construir_correo
from citologia.notifications.sender import EmailSender

TIPO_ACTIVACION = "ACTIVACION_COLPOSCOPIA"


class NotificacionRepository(Protocol):
    def reservar(self, sha256: str, tipo: str) -> bool: ...
    def marcar_enviado(self, sha256: str, tipo: str, message_id: str) -> None: ...
    def marcar_error(self, sha256: str, tipo: str, codigo: str) -> None: ...


@dataclass(frozen=True)
class ResultadoNotificacion:
    enviado: bool
    motivo: str   # enviado | no_aplica | ya_notificado | error_envio | <estado de verificación>
    revision_humana: bool = False
    message_id: str | None = None


def notificar_activacion(*, documento_sha256: str, identidad: IdentidadPDF,
                         codigos: list[int], vph: int | None, decision: Decision,
                         repo: AfiliadoRepository, notificaciones: NotificacionRepository,
                         sender: EmailSender, remitente: str, destinatarios: list[str],
                         prefijo_asunto: str = "") -> ResultadoNotificacion:
    if not decision.activar:
        return ResultadoNotificacion(False, "no_aplica")

    ver = verificar_identidad(identidad, repo)
    if ver.estado is not EstadoVerificacion.VERIFICADA:
        return ResultadoNotificacion(False, ver.estado.value, revision_humana=True)

    if not notificaciones.reservar(documento_sha256, TIPO_ACTIVACION):
        return ResultadoNotificacion(False, "ya_notificado")

    msg = construir_correo(caso_ref=documento_sha256[:12], afiliado=ver.afiliado,
                           codigos=codigos, vph=vph, decision=decision, remitente=remitente,
                           destinatarios=destinatarios, prefijo_asunto=prefijo_asunto)
    try:
        message_id = sender.enviar(msg)
    except EmailError as e:
        notificaciones.marcar_error(documento_sha256, TIPO_ACTIVACION, type(e).__name__)
        return ResultadoNotificacion(False, "error_envio")

    notificaciones.marcar_enviado(documento_sha256, TIPO_ACTIVACION, message_id)
    return ResultadoNotificacion(True, "enviado", message_id=message_id)