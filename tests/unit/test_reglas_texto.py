import unicodedata

import pytest

from citologia.extraction.reglas import extraer_por_reglas

# Secciones de resultado con la redacción real de cada laboratorio (sin datos de pacientes).
INFORMES = {
    "citofemme_asc_us": ("""CALIDAD DE LA MUESTRA
Satisfactoria para evaluación con presencia de componente endocervical
CLASIFICACIÓN GENERAL
Anormalidades en células epiteliales escamosas.
ESTUDIO ONCOLÓGICO
Atipias en células epiteliales escamosas de significado indeterminado ASC-US.
MICROORGANISMOS
Presencia de flora no patógena
RECOMENDACIONES
Sugiere consultar al ginecólogo""", [1]),
    "echavarria_lei_bajo_grado": ("""CALIDAD DE LA MUESTRA:
Satisfactoria. Presencia de componente endocervical / zona de transformación. -
INTERPRETACIÓN / RESULTADO
ANORMALIDADES EN CÉLULAS ESCAMOSAS:
Lesión Intraepitelial Escamosa de Bajo Grado
MICROORGANISMOS:
Bacilos
SUGERENCIAS
Se sugiere evaluar por colposcopia y biopsia
OBSERVACIONES
Persiste Lie de bajo grado""", [3]),
    "echavarria_negativa": ("""CALIDAD DE LA MUESTRA:
Satisfactoria. Presencia de componente endocervical / zona de transformación. - Extendido hemorrágico
INTERPRETACIÓN / RESULTADO
Negativa para lesión intraepitelial o malignidad
Cambios celulares reactivos asociados con inflamación
MICROORGANISMOS:
Bacilos
SUGERENCIAS
Control según criterio médico""", [17]),
    "adilab_negativa": ("""CALIDAD DE LA MUESTRA :
Satisfactoria para la evaluación. Presencia de células endocervicales o de la zona de transformación.
INTERPRETACION/ RESULTADO :
Negativo para lesión Intraepitelial o Malignidad.
OTROS HALLAZGOS NO NEOPLASICOS :
No se observan.
MICROORGANISMOS :
No se observan.
RECOMENDACIONES :
Se sugiere evaluar y control a criterio medico.""", [17]),
    "poctlab_negativa": ("""CITOLOGÍA - SISTEMA BETHESDA 2014
CALIDAD DE LA MUESTRA Satisfactoria para evaluación con presencia de células endocervicales y/o de la zona de transformación
ESTUDIO ONCOLÓGICO Negativo para lesión intraepitelial o malignidad, Cambios reactivos asociados por atrofia
MICROORGANISMOS ausecia de flora patogena
OBSERVACIONES extendido atrofico, Citología procesada por el método de base liquida
RECOMENDACIONES Control según criterio medico""", [17]),
}


@pytest.mark.parametrize("nombre", INFORMES)
def test_cada_laboratorio_se_resuelve_por_reglas(nombre):
    texto, esperado = INFORMES[nombre]
    r = extraer_por_reglas(texto)
    assert r["codigos_citologia"] == esperado
    assert r["claro"] is True and r["alertas"] == []


@pytest.mark.parametrize("nombre", INFORMES)
def test_tildes_descompuestas_dan_el_mismo_resultado(nombre):
    texto, esperado = INFORMES[nombre]
    nfd = unicodedata.normalize("NFD", texto)
    assert nfd != texto
    assert extraer_por_reglas(nfd)["codigos_citologia"] == esperado


def test_hallazgo_negado_no_cuenta_y_pide_ia():
    r = extraer_por_reglas("INTERPRETACIÓN\nNo se observan lesion intraepitelial de alto grado\n"
                           "RECOMENDACIONES\nControl")
    assert 4 not in r["codigos_citologia"] and r["claro"] is False


def test_sin_seccion_de_resultado_no_es_claro():
    r = extraer_por_reglas("texto cualquiera sin estructura")
    assert r["claro"] is False and r["codigos_citologia"] == []


@pytest.mark.parametrize("frase,esperado", [
    ("VPH: Detectado", 19), ("VPH no detectado", 20), ("HPV negativo", 20), ("sin dato", None),
])
def test_vph(frase, esperado):
    assert extraer_por_reglas("INTERPRETACIÓN\nNegativa para lesión intraepitelial\n" + frase)["vph"] == esperado
