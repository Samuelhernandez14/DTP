import pytest

from citologia.domain.identidad import (
    ComparacionNombre as C, comparar_nombres, normalizar_numero, normalizar_tipo,
    numero_en_texto, verificar_identidad,
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


def test_nombre_partido_en_lineas_distintas_no_coincide(crear_afiliado):
    # primer nombre en una línea y apellido en otra (p. ej. un firmante): no es el paciente
    texto = "Citotecnóloga MARIA BURBANO\nResponsable: JUAN PEREZ"
    assert comparar_nombres(texto, crear_afiliado()) is C.NO_COINCIDE


@pytest.mark.parametrize("texto,esperado", [
    ("CC 1000000001", True),
    ("Doc. Id.: 1.000.000.001", True),
    ("Solicitud 21000000012", False),           # token distinto que contiene el número
    ("Orden 99887766", False),
    (None, False),
])
def test_numero_en_texto(texto, esperado):
    assert numero_en_texto("1000000001", texto) is esperado


def _id(**kw):
    base = dict(tipo_documento="CC", numero_documento="1000000001",
                texto_pagina="Paciente:\nMARIA PEREZ\nCC 1000000001")
    base.update(kw)
    return IdentidadPDF(**base)


def test_identidad_incompleta_no_consulta_bd(repo_falso):
    repo = repo_falso([])
    assert verificar_identidad(_id(tipo_documento=None), repo).estado is E.IDENTIDAD_INCOMPLETA
    assert repo.consultas == []


def test_numero_del_archivo_no_esta_en_el_pdf(repo_falso, crear_afiliado):
    repo = repo_falso([crear_afiliado()])
    r = verificar_identidad(_id(texto_pagina="MARIA PEREZ\nCC 7777777"), repo)
    assert r.estado is E.DOCUMENTO_NO_EN_PDF and repo.consultas == []


def test_no_encontrado(repo_falso):
    assert verificar_identidad(_id(), repo_falso([])).estado is E.NO_ENCONTRADO


def test_verificada_consulta_con_valores_normalizados(crear_afiliado, repo_falso):
    repo = repo_falso([crear_afiliado()])
    r = verificar_identidad(_id(tipo_documento="C.C.", numero_documento="1.000.000.001"), repo)
    assert r.estado is E.VERIFICADA and repo.consultas == [("CC", "1000000001")]


def test_nombre_distinto_no_verifica(crear_afiliado, repo_falso):
    r = verificar_identidad(_id(texto_pagina="ANA RODRIGUEZ\nCC 1000000001"),
                            repo_falso([crear_afiliado()]))
    assert r.estado is E.NOMBRE_NO_COINCIDE and r.afiliado is None


def test_duplicado_se_descarta(crear_afiliado, repo_falso):
    filas = [crear_afiliado(id=1, duplicado=True), crear_afiliado(id=2)]
    r = verificar_identidad(_id(), repo_falso(filas))
    assert r.estado is E.VERIFICADA and r.afiliado.id == 2


def test_dos_coincidencias_es_ambiguo(crear_afiliado, repo_falso):
    filas = [crear_afiliado(id=1), crear_afiliado(id=2)]
    assert verificar_identidad(_id(), repo_falso(filas)).estado is E.AMBIGUO


# Disposición real de campos en los PDFs (PyMuPDF entrega etiquetas y valores desordenados;
# en ADILAB el número de solicitud y el de documento son ambos de 8 dígitos).
PAGINAS = {
    "adilab": "Solicitud\nIdentificación\nPaciente\nLAURA MARCELA TORRES RIOS 48\n"
              "SAVIA SALUD EPS\n99887766\n10203040\n",
    "echavarria": "Paciente:\nCC 10203040\nLAURA MARCELA TORRES RIOS\nIdentificación:\n",
    "citofemme": "Paciente:\nDoc. Id.:\nLAURA MARCELA TORRES  RIOS \n51 Años\n10203040\nFEMENINO\n",
    "poctlab": "REPORTE DE RESULTADOS\nLAURA MARCELA TORRES  RIOS\n10203040\nDocumento:\n",
}


@pytest.mark.parametrize("lab", PAGINAS)
def test_verifica_en_la_disposicion_de_cada_laboratorio(lab, crear_afiliado, repo_falso):
    afi = crear_afiliado(numero_documento="10203040", primer_nombre="LAURA",
                         segundo_nombre="MARCELA", primer_apellido="TORRES",
                         segundo_apellido="RIOS")
    r = verificar_identidad(IdentidadPDF("CC", "10203040", PAGINAS[lab]), repo_falso([afi]))
    assert r.estado is E.VERIFICADA
