import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from citologia.domain.errors import InvalidDocumentError
from citologia.domain.models import IdentidadPDF

_PATRON = re.compile(
    r"^(?P<tipo>[A-Z]{2})(?P<numero>[A-Z0-9]+)_(?P<clase>[A-Z0-9]+)_(?P<ts>\d{14})$")


@dataclass(frozen=True)
class NombreArchivo:
    tipo_documento: str
    numero_documento: str
    clase: str            # el "CCU" del ejemplo
    fecha: datetime


def parsear_nombre(nombre: str) -> NombreArchivo:
    m = _PATRON.match(Path(nombre).stem.upper())
    if not m:
        raise InvalidDocumentError("Nombre de archivo con formato inesperado")
    try:
        fecha = datetime.strptime(m["ts"], "%Y%m%d%H%M%S")
    except ValueError:
        raise InvalidDocumentError("Fecha inválida en el nombre de archivo") from None
    return NombreArchivo(m["tipo"], m["numero"], m["clase"], fecha)


def identidad_desde_archivo(nombre: NombreArchivo, texto_primera_pagina: str) -> IdentidadPDF:
    # nombre_completo recibe el TEXTO donde debe aparecer el nombre del afiliado
    return IdentidadPDF(nombre.tipo_documento, nombre.numero_documento, texto_primera_pagina)