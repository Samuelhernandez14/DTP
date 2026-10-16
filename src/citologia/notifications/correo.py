from email.message import EmailMessage
from email.utils import make_msgid

from citologia.domain.catalogo import CITOLOGIA, VPH_DETECTADO, VPH_NO_DETECTADO
from citologia.domain.models import Afiliado, Decision


def _o(valor) -> str:
    return str(valor) if valor else "No registrado"


def construir_correo(*, caso_ref: str, afiliado: Afiliado, codigos: list[int],
                     vph: int | None, decision: Decision, remitente: str,
                     destinatarios: list[str], prefijo_asunto: str = "") -> EmailMessage:
    vph_txt = {VPH_DETECTADO: "Detectado", VPH_NO_DETECTADO: "No detectado"}.get(vph, "No informado")
    hallazgos = "\n".join(f"  - {c}: {CITOLOGIA.get(c, '?')}" for c in sorted(codigos)) or "  (ninguno)"
    nombre = " ".join(filter(None, [afiliado.primer_nombre, afiliado.segundo_nombre,
                                    afiliado.primer_apellido, afiliado.segundo_apellido]))
    cuerpo = f"""Se informa la activación de la usuaria hacia colposcopia.

Referencia interna: {caso_ref}
Indicación: {decision.indicacion.value if decision.indicacion else '-'}
Regla aplicada: {decision.regla}

RESULTADO DE CITOLOGÍA (extraído del informe)
{hallazgos}
  VPH: {vph_txt}

DATOS DE LA USUARIA (verificados contra la base de afiliados)
  Documento: {afiliado.tipo_documento} {afiliado.numero_documento}
  Nombre: {nombre}
  Fecha de nacimiento: {afiliado.fecha_nacimiento:%Y-%m-%d}   Género: {afiliado.genero}
  Teléfono móvil: {_o(afiliado.telefono_movil)}   Fijo: {_o(afiliado.telefono_fijo)}
  Correo: {_o(afiliado.email)}
  Dirección: {afiliado.direccion_residencia}   Barrio: {_o(afiliado.barrio)}
  Régimen: {_o(afiliado.regimen)}   Estado de afiliación: {_o(afiliado.estado_afiliacion)}

Mensaje generado automáticamente. Contiene datos sensibles de salud: uso exclusivo del destinatario.
"""
    msg = EmailMessage()
    msg["Subject"] = f"{prefijo_asunto} Activación colposcopia - Ref {caso_ref}".strip()
    msg["From"] = remitente
    msg["To"] = ", ".join(destinatarios)
    msg["Message-ID"] = make_msgid()
    msg["X-Caso-Ref"] = caso_ref
    msg.set_content(cuerpo)
    return msg