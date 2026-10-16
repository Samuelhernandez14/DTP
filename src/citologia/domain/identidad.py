"""Normalización y verificación de identidad (PDF vs aseg_afiliados).
Lógica pura: la base de datos entra solo a través del Protocol AfiliadoRepository."""

import re
import unicodedata
from difflib import SequenceMatcher
from enum import Enum
from typing import Protocol

from citologia.domain.models import (
    Afiliado, EstadoVerificacion, IdentidadPDF, VerificacionIdentidad,
)

UMBRAL_APROXIMADO = 0.85
_PARTICULAS = {"DE", "DEL", "LA", "LAS", "LOS", "Y"}

# Alias frecuentes -> código. Validar contra:
#   SELECT DISTINCT mae_tipo_documento_codigo, mae_tipo_documento_valor FROM aseg_afiliados;
_ALIAS_TIPO = {
    "CC": "CC", "CEDULA": "CC", "CEDULADECIUDADANIA": "CC",
    "TI": "TI", "TARJETADEIDENTIDAD": "TI",
    "RC": "RC", "REGISTROCIVIL": "RC",
    "CE": "CE", "CEDULADEEXTRANJERIA": "CE",
    "PA": "PA", "PASAPORTE": "PA",
    "PT": "PT", "PE": "PE", "CN": "CN", "MS": "MS", "AS": "AS",
}


class ComparacionNombre(str, Enum):
    COINCIDE = "coincide"
    APROXIMADO = "aproximado"
    NO_COINCIDE = "no_coincide"


class AfiliadoRepository(Protocol):
    def buscar(self, tipo_documento: str, numero_documento: str) -> list[Afiliado]: ...


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def normalizar_tipo(valor: str | None) -> str | None:
    if not valor:
        return None
    clave = re.sub(r"[^A-Z]", "", _sin_acentos(valor).upper())
    return _ALIAS_TIPO.get(clave)


def normalizar_numero(valor: str | None) -> str | None:
    if not valor:
        return None
    return re.sub(r"[\s.,\-]", "", valor).upper() or None


def tokens_nombre(texto: str | None) -> list[str]:
    if not texto:
        return []
    limpio = re.sub(r"[^A-Z ]", " ", _sin_acentos(texto).upper())
    return [t for t in limpio.split() if t not in _PARTICULAS]


def _similitud(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def numero_en_texto(numero: str | None, texto: str | None) -> bool:
    """¿Aparece el número como token completo? Tolera separadores de miles (1.000.000.001)."""
    if not numero or not texto:
        return False
    sin_miles = re.sub(r"(?<=\d)[.,](?=\d{3}\b)", "", texto.upper())
    return numero.upper() in set(re.findall(r"[A-Z0-9]+", sin_miles))


def comparar_nombres(texto: str | None, afiliado: Afiliado) -> ComparacionNombre:
    """Primer nombre y primer apellido de la BD deben estar en LA MISMA LÍNEA del texto
    (sin importar el orden). Así no coinciden por casualidad con otros nombres del
    informe (firmantes, etc.). Segundo nombre/apellido pueden faltar en el PDF."""
    requeridos = tokens_nombre(afiliado.primer_nombre) + tokens_nombre(afiliado.primer_apellido)
    if not requeridos:
        return ComparacionNombre.NO_COINCIDE
    mejor = ComparacionNombre.NO_COINCIDE
    for linea in (texto or "").splitlines():
        pdf = tokens_nombre(linea)
        if not pdf:
            continue
        if all(t in pdf for t in requeridos):
            return ComparacionNombre.COINCIDE
        if all(any(_similitud(t, p) >= UMBRAL_APROXIMADO for p in pdf) for t in requeridos):
            mejor = ComparacionNombre.APROXIMADO
    return mejor


def verificar_identidad(identidad: IdentidadPDF,
                        repo: AfiliadoRepository) -> VerificacionIdentidad:
    tipo = normalizar_tipo(identidad.tipo_documento)
    numero = normalizar_numero(identidad.numero_documento)
    if not tipo or not numero:
        return VerificacionIdentidad(EstadoVerificacion.IDENTIDAD_INCOMPLETA)

    # El nombre del archivo debe coincidir con el contenido del PDF
    if not numero_en_texto(numero, identidad.texto_pagina):
        return VerificacionIdentidad(EstadoVerificacion.DOCUMENTO_NO_EN_PDF)

    candidatos = repo.buscar(tipo, numero)
    if not candidatos:
        return VerificacionIdentidad(EstadoVerificacion.NO_ENCONTRADO)
    if len(candidatos) > 1:
        candidatos = [a for a in candidatos if not a.duplicado] or candidatos

    comparaciones = [(a, comparar_nombres(identidad.texto_pagina, a)) for a in candidatos]
    coinciden = [a for a, c in comparaciones if c is ComparacionNombre.COINCIDE]
    if len(coinciden) == 1:
        return VerificacionIdentidad(EstadoVerificacion.VERIFICADA, coinciden[0])
    if len(coinciden) > 1:
        return VerificacionIdentidad(EstadoVerificacion.AMBIGUO)
    if any(c is ComparacionNombre.APROXIMADO for _, c in comparaciones):
        return VerificacionIdentidad(EstadoVerificacion.NOMBRE_APROXIMADO)
    return VerificacionIdentidad(EstadoVerificacion.NOMBRE_NO_COINCIDE)