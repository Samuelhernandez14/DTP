from dataclasses import dataclass, field
from enum import Enum
from datetime import date


class Indicacion(str, Enum):
    """Hereda de str: se compara y serializa a JSON igual que el texto original."""
    TAMIZAJE = "tamizaje"
    CLINICA = "clinica"


@dataclass
class Caso:
    codigos_citologia: list                  # códigos 1..18 encontrados en la citología
    vph: int | None = None                   # 19 detectado, 20 no detectado, None desconocido
    antecedente_asc_us: bool | None = None   # None = histórico no verificado
    tiene_anexo1: bool = False               
    exclusiones: list = field(default_factory=list)


@dataclass
class Decision:
    activar: bool
    regla: int | None
    indicacion: Indicacion | None
    revision_humana: bool
    motivos: list = field(default_factory=list)

class EstadoVerificacion(str, Enum):
    VERIFICADA = "verificada"
    IDENTIDAD_INCOMPLETA = "identidad_incompleta"
    NO_ENCONTRADO = "no_encontrado"
    AMBIGUO = "ambiguo"
    NOMBRE_APROXIMADO = "nombre_aproximado"
    NOMBRE_NO_COINCIDE = "nombre_no_coincide"
    DOCUMENTO_NO_EN_PDF = "documento_no_en_pdf"


@dataclass(frozen=True)
class IdentidadPDF:
    """tipo y número vienen del NOMBRE del archivo; texto_pagina es el texto
    del PDF contra el que se verifican el número y el nombre."""
    tipo_documento: str | None
    numero_documento: str | None
    texto_pagina: str | None


@dataclass(frozen=True)
class Afiliado:
    """Solo las columnas mínimas necesarias de aseg_afiliados."""
    id: int
    id_afiliado: str
    tipo_documento: str
    numero_documento: str
    primer_nombre: str
    segundo_nombre: str | None
    primer_apellido: str
    segundo_apellido: str | None
    fecha_nacimiento: date
    genero: str
    telefono_fijo: str | None
    telefono_movil: str | None
    email: str | None
    direccion_residencia: str
    barrio: str | None
    estado_afiliacion: str | None
    regimen: str | None
    duplicado: bool


@dataclass(frozen=True)
class VerificacionIdentidad:
    estado: EstadoVerificacion
    afiliado: Afiliado | None = None