from dataclasses import dataclass, field
from enum import Enum


class Indicacion(str, Enum):
    """Hereda de str: se compara y serializa a JSON igual que el texto original."""
    TAMIZAJE = "tamizaje"
    CLINICA = "clinica"


@dataclass
class Caso:
    codigos_citologia: list                  # códigos 1..18 encontrados en la citología
    vph: int | None = None                   # 19 detectado, 20 no detectado, None desconocido
    antecedente_asc_us: bool | None = None   # None = histórico no verificado
    tiene_anexo1: bool = False               # orden médica de colposcopia
    exclusiones: list = field(default_factory=list)


@dataclass
class Decision:
    activar: bool
    regla: int | None
    indicacion: Indicacion | None
    revision_humana: bool
    motivos: list = field(default_factory=list)