from datetime import date

import pytest

from citologia.domain.models import Afiliado


@pytest.fixture
def crear_afiliado():
    def _crear(**kw) -> Afiliado:
        base = dict(
            id=1, id_afiliado="A1", tipo_documento="CC", numero_documento="1000000001",
            primer_nombre="MARIA", segundo_nombre="JOSE", primer_apellido="PEREZ",
            segundo_apellido="GOMEZ", fecha_nacimiento=date(1990, 1, 1), genero="F",
            telefono_fijo=None, telefono_movil="3000000000", email=None,
            direccion_residencia="CALLE 1 2-3", barrio="CENTRO",
            estado_afiliacion="ACTIVO", regimen="CONTRIBUTIVO", duplicado=False)
        base.update(kw)
        return Afiliado(**base)
    return _crear


class RepoFalso:
    def __init__(self, filas):
        self.filas, self.consultas = filas, []

    def buscar(self, tipo, numero):
        self.consultas.append((tipo, numero))
        return self.filas


@pytest.fixture
def repo_falso():
    return RepoFalso


class NotificacionesFalsa:
    def __init__(self):
        self.estado = {}

    def reservar(self, sha, tipo):
        if self.estado.get((sha, tipo)) in (None, "ERROR"):
            self.estado[(sha, tipo)] = "ENVIANDO"
            return True
        return False

    def marcar_enviado(self, sha, tipo, message_id):
        self.estado[(sha, tipo)] = "ENVIADO"

    def marcar_error(self, sha, tipo, codigo):
        self.estado[(sha, tipo)] = "ERROR"


@pytest.fixture
def notif_falsa():
    return NotificacionesFalsa()