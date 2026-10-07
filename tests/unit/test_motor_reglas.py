import pytest

from citologia.domain.models import Caso, Indicacion
from citologia.domain.motor_reglas import coinciden, decidir

CASOS = [
    ("negativa", Caso([17]), dict(activar=False, revision_humana=False)),
    ("asc-us sin vph ni historico", Caso([17, 1]), dict(activar=False, revision_humana=True)),
    ("asc-us + vph detectado", Caso([1], vph=19, antecedente_asc_us=False), dict(activar=True, regla=2)),
    ("asc-us + antecedente", Caso([1], vph=20, antecedente_asc_us=True), dict(activar=True, regla=3)),
    ("asc-us vph no detectado sin antecedente", Caso([1], vph=20, antecedente_asc_us=False),
     dict(activar=False, revision_humana=False)),
    ("lei alto grado", Caso([4]), dict(activar=True, regla=1)),
    ("inadecuada", Caso([18]), dict(activar=False, revision_humana=True)),
    ("sin citologia + anexo1", Caso([], tiene_anexo1=True), dict(activar=True, regla=4)),
    ("negativa + anexo1", Caso([17], tiene_anexo1=True), dict(activar=True, regla=4)),
    ("codigo invalido", Caso([99]), dict(activar=False, revision_humana=True)),
    ("excluida", Caso([4], exclusiones=["disentimiento"]), dict(activar=False)),
]


@pytest.mark.parametrize("caso,esperado", [c[1:] for c in CASOS], ids=[c[0] for c in CASOS])
def test_decidir(caso, esperado):
    d = decidir(caso)
    for campo, valor in esperado.items():
        assert getattr(d, campo) == valor, d.motivos


def test_coinciden_ignora_orden():
    assert coinciden([1, 17], [17, 1])
    assert not coinciden([17], [1])


def test_indicacion_se_compara_como_texto():
    assert decidir(Caso([4])).indicacion == "tamizaje"
    assert decidir(Caso([], tiene_anexo1=True)).indicacion == Indicacion.CLINICA


def test_negativa_con_hallazgo_prevalece_hallazgo_y_lo_registra():
    d = decidir(Caso([17, 4]))
    assert d.activar and d.regla == 1
    assert any("negativa" in m for m in d.motivos)