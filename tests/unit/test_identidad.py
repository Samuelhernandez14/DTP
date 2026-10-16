import pytest

from citologia.domain.identidad import (
    ComparacionNombre as C, comparar_nombres, normalizar_numero, normalizar_tipo,
    verificar_identidad,
)
from citologia.domain.models import EstadoVerificacion as E, IdentidadPDF


@pytest.mark.parametrize("entrada,esperado", [
    ("C.C.", "CC"), ("cc", "CC"), ("Cédula de Ciudadanía", "CC"),
    ("T.I.", "TI"), ("Registro Civil", "RC"), ("xyz", None), (None, None),
])
def test_normalizar_tipo(entrada, esperado):
    assert normalizar_tipo(entrada) == esperado


def test_normalizar_numero():
    assert normalizar_numero("1.000.000.001") == "1000000001"
    assert normalizar_numero(" ") is None


@pytest.mark.parametrize("pdf,esperado", [
    ("PEREZ GOMEZ MARIA JOSE", C.COINCIDE),     # orden invertido
    ("María Pérez", C.COINCIDE),                # tildes y sin segundos nombres
    ("ANA RODRIGUEZ", C.NO_COINCIDE),
    (None, C.NO_COINCIDE),
])
def test_comparar_nombres(crear_afiliado, pdf, esperado):
    assert comparar_nombres(pdf, crear_afiliado()) is esperado


def test_nombre_aproximado_no_se_acepta_solo(crear_afiliado):
    a = crear_afiliado(primer_nombre="JUAN", segundo_nombre=None)
    assert comparar_nombres("JUANA PEREZ", a) is C.APROXIMADO


def _id(**kw):
    base = dict(tipo_documento="CC", numero_documento="1000000001", nombre_completo="MARIA PEREZ")
    base.update(kw)
    return IdentidadPDF(**base)


def test_identidad_incompleta_no_consulta_bd(repo_falso):
    repo = repo_falso([])
    assert verificar_identidad(_id(tipo_documento=None), repo).estado is E.IDENTIDAD_INCOMPLETA
    assert repo.consultas == []


def test_no_encontrado(repo_falso):
    assert verificar_identidad(_id(), repo_falso([])).estado is E.NO_ENCONTRADO


def test_verificada_consulta_con_valores_normalizados(crear_afiliado, repo_falso):
    repo = repo_falso([crear_afiliado()])
    r = verificar_identidad(_id(tipo_documento="C.C.", numero_documento="1.000.000.001"), repo)
    assert r.estado is E.VERIFICADA and repo.consultas == [("CC", "1000000001")]


def test_nombre_distinto_no_verifica(crear_afiliado, repo_falso):
    r = verificar_identidad(_id(nombre_completo="ANA RODRIGUEZ"), repo_falso([crear_afiliado()]))
    assert r.estado is E.NOMBRE_NO_COINCIDE and r.afiliado is None


def test_duplicado_se_descarta(crear_afiliado, repo_falso):
    filas = [crear_afiliado(id=1, duplicado=True), crear_afiliado(id=2)]
    r = verificar_identidad(_id(), repo_falso(filas))
    assert r.estado is E.VERIFICADA and r.afiliado.id == 2


def test_dos_coincidencias_es_ambiguo(crear_afiliado, repo_falso):
    filas = [crear_afiliado(id=1), crear_afiliado(id=2)]
    assert verificar_identidad(_id(), repo_falso(filas)).estado is E.AMBIGUO