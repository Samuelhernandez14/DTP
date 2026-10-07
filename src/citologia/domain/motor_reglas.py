"""Motor de reglas (sin IA): decide si una usuaria se activa hacia colposcopia.
Determinista y auditable: cada decisión devuelve qué regla se cumplió y por qué."""

from citologia.domain.catalogo import (
    ANORMALES_REGLA_1, CITOLOGIA, VPH_DETECTADO,
)
from citologia.domain.models import Caso, Decision, Indicacion


def coinciden(codigos_pdf, codigos_excel) -> bool:
    """Validación PDF vs Excel: mismos códigos, sin importar el orden."""
    return set(codigos_pdf) == set(codigos_excel)


def decidir(caso: Caso) -> Decision:
    codigos = set(caso.codigos_citologia)
    motivos = []

    invalidos = codigos - set(CITOLOGIA)
    if invalidos:
        return Decision(False, None, None, True,
                        [f"Códigos fuera del catálogo: {sorted(invalidos)}"])

    if caso.exclusiones:
        return Decision(False, None, None, False,
                        [f"Excluida: {', '.join(caso.exclusiones)}"])

    anormales = codigos & ANORMALES_REGLA_1
    if 17 in codigos and (anormales or 1 in codigos):
        motivos.append("El informe trae 'negativa' y un hallazgo a la vez; "
                       "prevalece el hallazgo")

    # Regla 1: cualquier categoría 2..16
    if anormales:
        return Decision(True, 1, Indicacion.TAMIZAJE, False,
                        motivos + [f"Regla 1: códigos {sorted(anormales)}"])

    # Reglas 2 y 3: ASC-US
    if 1 in codigos:
        if caso.vph == VPH_DETECTADO:
            return Decision(True, 2, Indicacion.TAMIZAJE, False,
                            motivos + ["Regla 2: ASC-US con VPH detectado"])
        if caso.antecedente_asc_us is True:
            return Decision(True, 3, Indicacion.TAMIZAJE, False,
                            motivos + ["Regla 3: ASC-US con ASC-US previo"])
        if not caso.tiene_anexo1:
            # Faltan datos para descartar las reglas 2 y 3: no se cierra sola
            if caso.vph is None or caso.antecedente_asc_us is None:
                return Decision(False, None, None, True,
                                motivos + ["ASC-US sin VPH o sin histórico "
                                           "verificado: no se puede descartar"])
            return Decision(False, None, None, False,
                            motivos + ["ASC-US sin VPH detectado ni antecedente"])

    # Regla 4: orden médica (Anexo 1), aplica si no cumplió 1-3
    if caso.tiene_anexo1:
        return Decision(True, 4, Indicacion.CLINICA, False,
                        motivos + ["Regla 4: Anexo 1 con orden de colposcopia"])

    if 18 in codigos:
        return Decision(False, None, None, True,
                        motivos + ["Muestra inadecuada para lectura: sin regla definida"])

    if not codigos:
        return Decision(False, None, None, True,
                        ["No se identificó resultado de citología"])

    # Solo queda 17 (negativa) sin Anexo 1
    return Decision(False, None, None, False,
                    motivos + ["Citología negativa sin criterio de activación"])